"""Check translations through Home Assistant's own translation loader."""

import json
from pathlib import Path
from string import Formatter

import pytest
from homeassistant import loader
from homeassistant.core import HomeAssistant
from homeassistant.helpers.translation import async_get_translations

from custom_components.ontech.binary_sensor import INPUTS
from custom_components.ontech.sensor import SENSORS
from custom_components.ontech.switch import RELAY

COMPONENT = Path(__file__).resolve().parents[1] / "custom_components/ontech"


@pytest.fixture
async def hass(tmp_path):
    hass = HomeAssistant(str(tmp_path))
    loader.async_setup(hass)
    integration = loader.Integration(
        hass,
        "custom_components.ontech",
        COMPONENT,
        json.loads((COMPONENT / "manifest.json").read_text()),
        top_level_files={path.name for path in COMPONENT.iterdir()},
    )
    hass.data[loader.DATA_INTEGRATIONS] = {"ontech": integration}
    hass.data[loader.DATA_CUSTOM_COMPONENTS] = {"ontech": integration}
    return hass


@pytest.mark.parametrize("language,relay", [("en", "Relay"), ("sv", "Relä")])
async def test_ha_loads_entity_names(hass, language, relay):
    translations = await async_get_translations(hass, language, "entity", {"ontech"})
    assert translations["component.ontech.entity.switch.relay.name"] == relay
    for platform, descriptions in (
        ("sensor", SENSORS),
        ("binary_sensor", INPUTS),
        ("switch", (RELAY,)),
    ):
        for description in descriptions:
            assert translations[
                f"component.ontech.entity.{platform}.{description.translation_key}.name"
            ]


async def test_missing_language_falls_back_to_english(hass):
    translations = await async_get_translations(hass, "fr", "entity", {"ontech"})
    assert translations["component.ontech.entity.switch.relay.name"] == "Relay"


@pytest.mark.parametrize("category", ["entity", "config", "device", "exceptions"])
async def test_translation_keys_and_placeholders_match(hass, category):
    english = await async_get_translations(hass, "en", category, {"ontech"})
    swedish = await async_get_translations(hass, "sv", category, {"ontech"})
    assert english
    assert english.keys() == swedish.keys()
    for key in english:
        assert "[%key:" not in english[key]
        assert "[%key:" not in swedish[key]
        expected = {name for _, name, _, _ in Formatter().parse(english[key]) if name}
        actual = {name for _, name, _, _ in Formatter().parse(swedish[key]) if name}
        assert expected == actual
