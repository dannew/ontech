"""Privacy-preserving diagnostics for Ontech Control."""

from typing import Any

from homeassistant.core import HomeAssistant

from .coordinator import OntechConfigEntry
from .model import fresh, unit_indices, value


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: OntechConfigEntry
) -> dict[str, Any]:
    """Export only connection health and model counts, never raw account data."""
    coordinator = entry.runtime_data
    return {
        "connected": bool(coordinator.client.ws and not coordinator.client.ws.closed),
        "last_update_success": coordinator.last_update_success,
        "systems": [
            {
                "fresh": fresh(status),
                "models": [value(status, "connected", index) for index in unit_indices(status)],
            }
            for status in (coordinator.data or {}).values()
        ],
    }
