# Bugs and feature requests

| ID | Type | Status | Description |
| --- | --- | --- | --- |
| BUG-001 | Verification | Partially verified | User confirmed physical relay on/off control and temperature readings with a real account on 2026-11-03, using Home Assistant Core 2026.10.4 with Ontech 9040 and 9015 hardware. Binary inputs, restart/reconnection, stale-data handling, and automations remain unverified. Advanced alarm entities are not implemented (see BUG-002). |
| BUG-002 | Feature | Open | Thermostat, heat pump, scheduling, alarm acknowledgement, and garage pulse entities are not implemented. |
| BUG-003 | Limitation | Open | Sending a relay command provides no separate delivery acknowledgement. Entity state changes only after a server status update. |
| BUG-004 | Publication | Open | Metadata targets dannew/ontech with @dannew as maintainer. Publication is on hold until real-account hardware testing, validation, and owner approval. Catalog inclusion also requires external review. |
| BUG-005 | Localization | Fixed in 0.2.0 | Entity names and action errors were hardcoded and project documentation was Swedish-only. English is now the source language, with complete Swedish runtime translations. |
| BUG-006 | Lifecycle | Fixed in 0.2.0 | Runtime data used hass.data and cleanup did not explicitly cancel coordinator refreshes. The integration now uses typed ConfigEntry.runtime_data and coordinator shutdown. Push authentication failures now explicitly start reauthentication. |
