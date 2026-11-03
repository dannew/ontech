from homeassistant.core import callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .model import fresh, number, unit_indices, value


class OntechEntity(CoordinatorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, iccid, index, key, name):
        super().__init__(coordinator)
        self.iccid = iccid
        self.index = index
        self._attr_unique_id = f"{iccid}_{index}_{key}"
        self._attr_name = name

    @property
    def status(self):
        return self.coordinator.data.get(self.iccid, {})

    @property
    def available(self):
        return (
            super().available
            and fresh(self.status)
            and bool(number(value(self.status, "connected", self.index)))
        )

    @property
    def device_info(self):
        names = self.coordinator.names.get(self.iccid, {})
        labels = names.get("units", [])
        label = (
            labels[self.index] if isinstance(labels, list) and self.index < len(labels) else None
        )
        system = names.get("systemName") or "Ontech"
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self.iccid}_{self.index}")},
            name=f"{system} {label or f'Unit {self.index + 1}'}",
            manufacturer="Ontech",
            model=str(value(self.status, "connected", self.index) or "Unknown"),
            configuration_url="https://app.ontechcontrol.com",
        )


def discover(coordinator, entry, async_add_entities, factory):
    known = set()

    @callback
    def update():
        entities = []
        for iccid, status in (coordinator.data or {}).items():
            for index in unit_indices(status):
                for key, entity in factory(coordinator, iccid, index, status):
                    identity = (iccid, index, key)
                    if identity not in known:
                        known.add(identity)
                        entities.append(entity)
        if entities:
            async_add_entities(entities)

    entry.async_on_unload(coordinator.async_add_listener(update))
    update()
