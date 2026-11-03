from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import UnitOfTemperature

from .const import DOMAIN
from .entity import OntechEntity, discover
from .model import number, value


async def async_setup_entry(hass, entry, async_add_entities):
    def factory(coordinator, iccid, index, status):
        for key, label in (
            ("intTemp", "Internal temperature"),
            ("extTemp", "External temperature"),
        ):
            if number(value(status, key, index)) is not None:
                yield key, OntechTemperature(coordinator, iccid, index, key, label)

    discover(hass.data[DOMAIN][entry.entry_id], entry, async_add_entities, factory)


class OntechTemperature(OntechEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    def __init__(self, coordinator, iccid, index, key, name):
        super().__init__(coordinator, iccid, index, key, name)
        self.key = key

    @property
    def native_value(self):
        return number(value(self.status, self.key, self.index))
