import asyncio
import logging
import time
from datetime import timedelta

from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import OntechAuthError, OntechError
from .model import fresh, has_relay, relay_command

_LOGGER = logging.getLogger(__name__)


class OntechCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry, client):
        super().__init__(
            hass,
            _LOGGER,
            name="Ontech Control",
            config_entry=entry,
            update_interval=timedelta(seconds=60),
        )
        self.client = client
        self.entry = entry
        self.statuses = {}
        self.names = {}
        self.iccids = None
        self.reader = None
        self.last_received = 0
        self.command_lock = asyncio.Lock()

    def accept(self, message):
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

    async def _async_update_data(self):
        try:
            if self.reader is not None and not self.reader.done():
                if time.monotonic() - self.last_received > 150:
                    await self._stop_reader()
                else:
                    await self.client.send({"command": "ping", "message": int(time.time())})
                    return dict(self.statuses)
            self.statuses = {}
            self.names = {}
            self.iccids = None
            await self.client.connect()
            async with asyncio.timeout(30):
                while (
                    self.iccids is None
                    or not self.iccids.issubset(self.statuses)
                    or not self.iccids.issubset(self.names)
                ):
                    message = await self.client.receive()
                    self.accept(message)
                    if message.get("command") == "get_account_info":
                        for iccid in self.iccids:
                            await self.client.send({"command": "get_status", "iccid": iccid})
            self.reader = self.entry.async_create_background_task(
                self.hass, self._listen(), "Ontech WebSocket"
            )
            return dict(self.statuses)
        except OntechAuthError as err:
            await self.client.close()
            raise ConfigEntryAuthFailed("Log in to Ontech again") from err
        except (OntechError, TimeoutError) as err:
            await self.client.close()
            raise UpdateFailed("Unable to fetch Ontech status") from err

    async def _listen(self):
        try:
            while True:
                message = await self.client.receive()
                self.accept(message)
                self.async_set_updated_data(dict(self.statuses))
        except OntechAuthError:
            self.async_set_update_error(ConfigEntryAuthFailed("Ontech session expired"))
        except OntechError:
            self.async_set_update_error(UpdateFailed("Ontech connection lost"))
        finally:
            await self.client.close()

    async def _stop_reader(self):
        if self.reader is not None:
            self.reader.cancel()
            try:
                await self.reader
            except asyncio.CancelledError:
                pass
            self.reader = None
        await self.client.close()

    async def async_close(self):
        await self._stop_reader()
        await self.client.session.close()

    async def set_relay(self, iccid, index, on):
        async with self.command_lock:
            status = self.statuses.get(iccid, {})
            if not self.last_update_success or not fresh(status) or not has_relay(status, index):
                raise HomeAssistantError("Ontech relay is unavailable")
            try:
                await self.client.send(relay_command(iccid, index, on))
            except OntechError as err:
                raise HomeAssistantError("Ontech relay command failed") from err
