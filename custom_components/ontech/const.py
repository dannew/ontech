"""Constants for the Ontech Control integration."""

from homeassistant.const import Platform

DOMAIN = "ontech"
BASE_URL = "https://app.ontechcontrol.com"
PLATFORMS = [Platform.BINARY_SENSOR, Platform.SENSOR, Platform.SWITCH]
