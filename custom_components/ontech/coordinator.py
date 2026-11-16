"""Maintain the Ontech connection and coordinate entity updates."""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import OntechAuthError, OntechClient, OntechError
from .const import DOMAIN
from .model import fresh, has_relay, relay_command

_LOGGER = logging.getLogger(__name__)


type OntechConfigEntry = ConfigEntry[OntechCoordinator]
type StatusData = dict[str, dict[str, Any]]


class OntechCoordinator(DataUpdateCoordinator[StatusData]):
    """Receive push status and supervise the connection."""

    def __init__(self, hass: HomeAssistant, entry: OntechConfigEntry, client: OntechClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="Ontech Control",
            config_entry=entry,
        )
        self.client = client
        self.entry = entry
        self.statuses: StatusData = {}
        self.names: StatusData = {}
        self.iccids: set[str] | None = None
        self.reader: asyncio.Task[None] | None = None
        self.last_received = 0
        self.command_lock = asyncio.Lock()
        self._unsub_watchdog = None
        self._reauth_required = False
        self._was_connected = False
        self._check_task: asyncio.Task[None] | None = None

    def accept(self, message: dict[str, Any]) -> None:
        self.last_received = time.monotonic()
        command = message.get("command")
        if command == "get_account_info":
            ids = message.get("iccids")
            if not isinstance(ids, list) or not all(isinstance(i, str) for i in ids):
                raise OntechError("Invalid account device list")
            self.iccids = set(ids)
            self.statuses = {k: v for k, v in self.statuses.items() if k in self.iccids}
        iccid = message.get("iccid")
        if command == "status" and isinstance(iccid, str):
            if not isinstance(message.get("units"), dict):
                raise OntechError("Invalid device status")
            if self.iccids is None or iccid in self.iccids:
                self.statuses[iccid] = message
        elif command == "get_names" and isinstance(iccid, str):
            self.names[iccid] = message

    @callback
    def _watchdog(self, now: datetime) -> None:
        if (
            not self._shutdown_requested
            and not self._reauth_required
            and (self._check_task is None or self._check_task.done())
        ):
            self._check_task = self.entry.async_create_background_task(
                self.hass, self.async_refresh(), "Ontech connection check"
            )

    async def _async_update_data(self) -> StatusData:
        try:
            if self.reader is not None and not self.reader.done():
                if time.monotonic() - self.last_received > 150:
                    await self._stop_reader()
                else:
                    await self.client.send({"command": "ping", "message": int(time.time())})
                    return dict(self.statuses)
            await self._stop_reader()
            _LOGGER.debug("Connecting to Ontech Control")
            self.statuses = {}
            self.names = {}
            self.iccids = None
            await self.client.connect()
            async with asyncio.timeout(30):
                while self.iccids is None or not self.iccids.issubset(self.statuses):
                    message = await self.client.receive()
                    self.accept(message)
                    if message.get("command") == "get_account_info":
                        for iccid in self.iccids:
                            await self.client.send({"command": "get_status", "iccid": iccid})
            if self._unsub_watchdog is None:
                self._unsub_watchdog = async_track_time_interval(
                    self.hass, self._watchdog, timedelta(seconds=60)
                )
            if self._was_connected:
                _LOGGER.info("Ontech Control connection restored")
            self._was_connected = True
            self.reader = self.entry.async_create_background_task(
                self.hass, self._listen(), "Ontech WebSocket"
            )
            return dict(self.statuses)
        except OntechAuthError as err:
            await self._stop_reader()
            self._reauth_required = True
            raise ConfigEntryAuthFailed(
                translation_domain=DOMAIN, translation_key="invalid_auth"
            ) from err
        except (OntechError, TimeoutError) as err:
            await self._stop_reader()
            _LOGGER.debug(
                "Ontech connection attempt failed; retrying in 60 seconds (%s)", type(err).__name__
            )
            raise UpdateFailed(translation_domain=DOMAIN, translation_key="cannot_connect") from err

    async def _listen(self) -> None:
        try:
            while True:
                message = await self.client.receive()
                self.accept(message)
                self.async_set_updated_data(dict(self.statuses))
        except (OntechError, TimeoutError, ConnectionError) as err:
            _LOGGER.debug(
                "Ontech reader disconnected (%s); automatic retry scheduled", type(err).__name__
            )
            self.async_set_update_error(
                UpdateFailed(translation_domain=DOMAIN, translation_key="cannot_connect")
            )
        except Exception as err:
            _LOGGER.error(
                "Unexpected Ontech reader failure (%s); automatic retry scheduled",
                type(err).__name__,
            )
            self.async_set_update_error(
                UpdateFailed(translation_domain=DOMAIN, translation_key="cannot_connect")
            )
        finally:
            await self.client.close()

    async def _stop_reader(self) -> None:
        if self.reader is not None:
            self.reader.cancel()
            try:
                await self.reader
            except asyncio.CancelledError:
                if asyncio.current_task().cancelling():
                    raise
            except Exception as err:
                _LOGGER.debug("Previous Ontech reader failed (%s)", type(err).__name__)
            self.reader = None
        await self.client.close()

    async def async_shutdown(self) -> None:
        """Cancel refreshes and close account-owned network resources."""
        if self._unsub_watchdog is not None:
            self._unsub_watchdog()
            self._unsub_watchdog = None
        await super().async_shutdown()
        if self._check_task is not None:
            self._check_task.cancel()
            try:
                await self._check_task
            except asyncio.CancelledError:
                if asyncio.current_task().cancelling():
                    raise
            self._check_task = None
        await self._stop_reader()
        # Helper-created sessions must release their reference without closing HA's connector.
        self.client.session.detach()

    async def async_set_relay(self, iccid: str, index: int, on: bool) -> None:
        async with self.command_lock:
            status = self.statuses.get(iccid, {})
            if not self.last_update_success or not fresh(status) or not has_relay(status, index):
                raise HomeAssistantError(
                    translation_domain=DOMAIN, translation_key="relay_unavailable"
                )
            try:
                await self.client.send(relay_command(iccid, index, on))
            except OntechError as err:
                raise HomeAssistantError(
                    translation_domain=DOMAIN, translation_key="command_failed"
                ) from err
