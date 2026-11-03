from homeassistant.components.binary_sensor import BinarySensorEntity

from .const import DOMAIN
from .entity import OntechEntity, discover
from .model import boolean, value


async def async_setup_entry(hass, entry, async_add_entities):
    def factory(coordinator, iccid, index, status):
        for key, label in (("inputA", "Input A"), ("inputB", "Input B")):
            if boolean(value(status, key, index)) is not None:
                yield key, OntechInput(coordinator, iccid, index, key, label)

    discover(hass.data[DOMAIN][entry.entry_id], entry, async_add_entities, factory)


class OntechInput(OntechEntity, BinarySensorEntity):
    def __init__(self, coordinator, iccid, index, key, name):
        super().__init__(coordinator, iccid, index, key, name)
        self.key = key

    @property
    def is_on(self):
        return boolean(value(self.status, self.key, self.index))
