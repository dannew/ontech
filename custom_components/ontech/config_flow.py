"""Configure Ontech Control through the Home Assistant UI."""

import asyncio
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig, TextSelectorType

from . import create_client
from .api import OntechAuthError, OntechError
from .const import DOMAIN

PASSWORD_SELECTOR = TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))


class OntechConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Set up an account and renew its credentials."""

    VERSION = 1

    async def _validate_credentials(self, data: dict[str, Any]) -> str | None:
        client = create_client(self.hass, data)
        try:
            await client.connect()
            async with asyncio.timeout(30):
                while True:
                    message = await client.receive()
                    if message.get("command") == "get_account_info":
                        if not isinstance(message.get("iccids"), list):
                            raise OntechError("Invalid account device list")
                        return None
        except OntechAuthError:
            return "invalid_auth"
        except OntechError, TimeoutError:
            return "cannot_connect"
        finally:
            await client.close()
            await client.session.close()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Create a config entry after verifying the account."""
        errors = {}
        if user_input is not None:
            data = {
                CONF_EMAIL: user_input[CONF_EMAIL].strip().lower(),
                CONF_PASSWORD: user_input[CONF_PASSWORD],
            }
            await self.async_set_unique_id(data[CONF_EMAIL])
            self._abort_if_unique_id_configured()
            if error := await self._validate_credentials(data):
                errors["base"] = error
            else:
                return self.async_create_entry(title=data[CONF_EMAIL], data=data)
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_EMAIL): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.EMAIL)
                    ),
                    vol.Required(CONF_PASSWORD): PASSWORD_SELECTOR,
                }
            ),
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        """Prompt for a new password for the existing account."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Renew credentials without changing the account identity."""
        entry = self._get_reauth_entry()
        errors = {}
        if user_input is not None:
            data = {CONF_EMAIL: entry.data[CONF_EMAIL], CONF_PASSWORD: user_input[CONF_PASSWORD]}
            if error := await self._validate_credentials(data):
                errors["base"] = error
            else:
                return self.async_update_reload_and_abort(entry, data_updates=data)
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): PASSWORD_SELECTOR}),
            description_placeholders={"email": entry.data[CONF_EMAIL]},
            errors=errors,
        )
