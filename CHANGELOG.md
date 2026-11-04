# Changelog

## 0.2.1

First release candidate for installation as a custom repository in HACS or Marketplace. This release is not a listing in the shared catalog.

### Supported and tested

- Relay on/off control and temperature readings verified by the owner on Home Assistant Core 2026.10.4 with Ontech 9040 and 9015 hardware, including after the protocol fixes below.
- English and Swedish configuration, entity names, and errors.
- Minimum Home Assistant Core version: 2026.10.4.

### Fixes

- Treat redirects to the login page as authentication failures so rejected credentials are reported correctly.
- Reconnect expired WebSocket sessions before requesting new credentials.
- Interpret timestamps without a timezone in UTC status fields as UTC.
- Allow initial device synchronization to complete without optional names.

### Installation and migration

Add https://github.com/dannew/ontech as a custom repository of type Integration in HACS (2026.10) or Marketplace (2026.11 and later), then install Ontech Control and restart Home Assistant.

For an existing Git/symlink installation, back up Home Assistant first. Remove only the `custom_components/ontech` symlink before installing through HACS/Marketplace; retain the existing Ontech config entry under Devices & services. Do not delete the account entry or its entities. Keep the Git checkout for rollback until the managed installation has been verified.

### Known limitations

- Binary inputs, restart/reconnection, stale-data handling, and Home Assistant automations have not yet been verified with real hardware.
- Thermostat, heat pump, scheduling, alarm acknowledgement, and garage pulse entities are not implemented.
- Sending a relay command is not a delivery acknowledgement; state follows the server's reported status.
- Other device models have not been hardware-tested. See BUGS.md for outstanding verification work.

### Validation

40 automated tests pass on Home Assistant Core 2026.10.4 and 2026.11.0b3 using a simulated Ontech server. These tests complement the limited real-hardware verification above.
