"""Temperature sensors for Ontech Control."""

from collections.abc import Iterable
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import OntechConfigEntry, OntechCoordinator
from .entity import OntechEntity, async_discover
from .model import number, value

PARALLEL_UPDATES = 0
SENSORS = tuple(
    SensorEntityDescription(
        key=key,
        translation_key=translation_key,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    )
    for key, translation_key in (
        ("intTemp", "internal_temperature"),
        ("extTemp", "external_temperature"),
    )
)


async def async_setup_entry(
    hass: HomeAssistant, entry: OntechConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up reported temperature sensors."""

    def factory(
        coordinator: OntechCoordinator, iccid: str, index: int, status: dict[str, Any]
    ) -> Iterable[OntechTemperature]:
        for description in SENSORS:
            if number(value(status, description.key, index)) is not None:
                yield OntechTemperature(coordinator, iccid, index, description)

    async_discover(entry, async_add_entities, factory)


class OntechTemperature(OntechEntity, SensorEntity):
    """A temperature reported by an Ontech unit."""

    entity_description: SensorEntityDescription

    @property
    def native_value(self) -> float | None:
        return number(value(self.status, self.entity_description.key, self.index))
