"""Shared Ontech entity behavior and discovery."""

from collections.abc import Callable, Iterable
from typing import Any

from homeassistant.core import callback
from homeassistant.helpers.entity import DeviceInfo, EntityDescription
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import BASE_URL, DOMAIN
from .coordinator import OntechConfigEntry, OntechCoordinator
from .model import fresh, number, unit_indices, value


class OntechEntity(CoordinatorEntity[OntechCoordinator]):
    """An entity belonging to an Ontech master or expansion unit."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: OntechCoordinator,
        iccid: str,
        index: int,
        description: EntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.iccid = iccid
        self.index = index
        self.entity_description = description
        self._attr_unique_id = f"{iccid}_{index}_{description.key}"

    @property
    def status(self) -> dict[str, Any]:
        return self.coordinator.data.get(self.iccid, {})

    @property
    def available(self) -> bool:
        return (
            super().available
            and fresh(self.status)
            and bool(number(value(self.status, "connected", self.index)))
        )

    @property
    def device_info(self) -> DeviceInfo:
        names = self.coordinator.names.get(self.iccid, {})
        labels = names.get("units", [])
        label = (
            labels[self.index] if isinstance(labels, list) and self.index < len(labels) else None
        )
        system = names.get("systemName") or "Ontech"
        info = DeviceInfo(
            identifiers={(DOMAIN, f"{self.iccid}_{self.index}")},
            manufacturer="Ontech",
            model=str(value(self.status, "connected", self.index) or "Unknown"),
            configuration_url=BASE_URL,
        )
        if label:
            info["name"] = f"{system} {label}"
        else:
            info["translation_key"] = "unit"
            info["translation_placeholders"] = {"system": system, "number": str(self.index + 1)}
        return info


type EntityFactory = Callable[[OntechCoordinator, str, int, dict[str, Any]], Iterable[OntechEntity]]


@callback
def async_discover(
    entry: OntechConfigEntry,
    async_add_entities: AddEntitiesCallback,
    factory: EntityFactory,
) -> None:
    """Discover new entities from initial data and subsequent push updates."""
    coordinator = entry.runtime_data
    known: set[str] = set()

    @callback
    def update() -> None:
        entities = []
        for iccid, status in (coordinator.data or {}).items():
            for index in unit_indices(status):
                for entity in factory(coordinator, iccid, index, status):
                    if entity.unique_id not in known:
                        known.add(entity.unique_id)
                        entities.append(entity)
        if entities:
            async_add_entities(entities)

    entry.async_on_unload(coordinator.async_add_listener(update))
    update()
