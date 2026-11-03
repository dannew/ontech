import asyncio

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig, TextSelectorType

from . import create_client
from .api import OntechAuthError, OntechError
from .const import DOMAIN


class OntechConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        return await self._credentials("user", user_input)

    async def async_step_reauth(self, entry_data):
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        return await self._credentials("reauth_confirm", user_input)

    async def _credentials(self, step, user_input):
        errors = {}
        if user_input is not None:
            data = {
                "email": user_input["email"].strip().lower(),
                "password": user_input["password"],
            }
            if step == "reauth_confirm" and data["email"] != self._get_reauth_entry().data["email"]:
                errors["base"] = "wrong_account"
            else:
                client = create_client(self.hass, data)
                try:
                    await client.connect()
                    async with asyncio.timeout(30):
                        while True:
                            message = await client.receive()
                            if message.get("command") == "get_account_info":
                                break
                except OntechAuthError:
                    errors["base"] = "invalid_auth"
                except (OntechError, TimeoutError):
                    errors["base"] = "cannot_connect"
                finally:
                    await client.close()
                    await client.session.close()
                if not errors:
                    if step == "reauth_confirm":
                        return self.async_update_reload_and_abort(
                            self._get_reauth_entry(), data_updates=data
                        )
                    await self.async_set_unique_id(data["email"])
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(title=data["email"], data=data)
        return self.async_show_form(
            step_id=step,
            data_schema=vol.Schema(
                {
                    vol.Required("email"): str,
                    vol.Required("password"): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.PASSWORD)
                    ),
                }
            ),
            errors=errors,
        )
