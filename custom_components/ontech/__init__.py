"""Set up the Ontech Control integration."""

from collections.abc import Mapping
from typing import Any

import aiohttp
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .api import OntechClient
from .const import PLATFORMS
from .coordinator import OntechConfigEntry, OntechCoordinator


def create_client(hass: HomeAssistant, data: Mapping[str, Any]) -> OntechClient:
    """Create an account-isolated session with Home Assistant's SSL settings."""
    session = async_create_clientsession(
        hass,
        cookie_jar=aiohttp.CookieJar(),
        timeout=aiohttp.ClientTimeout(total=30),
    )
    return OntechClient(session, data[CONF_EMAIL], data[CONF_PASSWORD])


async def async_setup_entry(hass: HomeAssistant, entry: OntechConfigEntry) -> bool:
    """Set up an account and its entity platforms."""
    coordinator = OntechCoordinator(hass, entry, create_client(hass, entry.data))
    try:
        await coordinator.async_config_entry_first_refresh()
        entry.runtime_data = coordinator
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    except BaseException:
        await coordinator.async_shutdown()
        raise
    return True


async def async_unload_entry(hass: HomeAssistant, entry: OntechConfigEntry) -> bool:
    """Unload the platforms and close their connection."""
    if await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        await entry.runtime_data.async_shutdown()
        return True
    return False
