"""Binary inputs for Ontech Control."""

from collections.abc import Iterable
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import OntechConfigEntry, OntechCoordinator
from .entity import OntechEntity, async_discover
from .model import boolean, value

PARALLEL_UPDATES = 0
INPUTS = (
    BinarySensorEntityDescription(key="inputA", translation_key="input_a"),
    BinarySensorEntityDescription(key="inputB", translation_key="input_b"),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: OntechConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up inputs without assuming what is wired to them."""

    def factory(
        coordinator: OntechCoordinator, iccid: str, index: int, status: dict[str, Any]
    ) -> Iterable[OntechInput]:
        for description in INPUTS:
            if boolean(value(status, description.key, index)) is not None:
                yield OntechInput(coordinator, iccid, index, description)

    async_discover(entry, async_add_entities, factory)


class OntechInput(OntechEntity, BinarySensorEntity):
    """A raw binary input reported by an Ontech unit."""

    entity_description: BinarySensorEntityDescription

    @property
    def is_on(self) -> bool | None:
        return boolean(value(self.status, self.entity_description.key, self.index))
