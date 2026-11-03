from homeassistant.components.switch import SwitchEntity

from .const import DOMAIN
from .entity import OntechEntity, discover
from .model import boolean, has_relay, value


async def async_setup_entry(hass, entry, async_add_entities):
    def factory(coordinator, iccid, index, status):
        if has_relay(status, index):
            yield "relay", OntechRelay(coordinator, iccid, index, "relay", "Relay")

    discover(hass.data[DOMAIN][entry.entry_id], entry, async_add_entities, factory)


class OntechRelay(OntechEntity, SwitchEntity):
    @property
    def available(self):
        return super().available and has_relay(self.status, self.index)

    @property
    def is_on(self):
        return boolean(value(self.status, "status", self.index))

    async def async_turn_on(self, **kwargs):
        await self.coordinator.set_relay(self.iccid, self.index, True)

    async def async_turn_off(self, **kwargs):
        await self.coordinator.set_relay(self.iccid, self.index, False)
