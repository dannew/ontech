import aiohttp
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .api import OntechClient
from .const import DOMAIN, PLATFORMS
from .coordinator import OntechCoordinator


def create_client(hass, data):
    session = async_create_clientsession(
        hass,
        cookie_jar=aiohttp.CookieJar(),
        timeout=aiohttp.ClientTimeout(total=30),
    )
    return OntechClient(session, data["email"], data["password"])


async def async_setup_entry(hass, entry):
    coordinator = OntechCoordinator(hass, entry, create_client(hass, entry.data))
    try:
        await coordinator.async_config_entry_first_refresh()
        hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    except BaseException:
        await coordinator.async_close()
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
        raise
    return True


async def async_unload_entry(hass, entry):
    if await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        coordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.async_close()
        return True
    return False
