"""Relay switches for Ontech Control."""

from collections.abc import Iterable
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import OntechConfigEntry, OntechCoordinator
from .entity import OntechEntity, async_discover
from .model import boolean, has_relay, value

PARALLEL_UPDATES = 1
RELAY = SwitchEntityDescription(key="relay", translation_key="relay")


async def async_setup_entry(
    hass: HomeAssistant, entry: OntechConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up supported relay switches."""

    def factory(
        coordinator: OntechCoordinator, iccid: str, index: int, status: dict[str, Any]
    ) -> Iterable[OntechRelay]:
        if has_relay(status, index):
            yield OntechRelay(coordinator, iccid, index, RELAY)

    async_discover(entry, async_add_entities, factory)


class OntechRelay(OntechEntity, SwitchEntity):
    """An Ontech relay with server-reported state."""

    @property
    def available(self) -> bool:
        return super().available and has_relay(self.status, self.index)

    @property
    def is_on(self) -> bool | None:
        return boolean(value(self.status, "status", self.index))

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_relay(self.iccid, self.index, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_relay(self.iccid, self.index, False)
