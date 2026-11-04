# Bugs and feature requests

| ID | Type | Status | Description |
| --- | --- | --- | --- |
| BUG-001 | Verification | Partially verified | User confirmed physical relay on/off control and temperature readings with a real account on 2026-11-03, using Home Assistant Core 2026.10.4 with Ontech 9040 and 9015 hardware. Binary inputs, restart/reconnection, stale-data handling, and automations remain unverified. Advanced alarm entities are not implemented (see BUG-002). |
| BUG-002 | Feature | Open | Thermostat, heat pump, scheduling, alarm acknowledgement, and garage pulse entities are not implemented. |
| BUG-003 | Limitation | Open | Sending a relay command provides no separate delivery acknowledgement. Entity state changes only after a server status update. |
| BUG-004 | Publication | Open | Metadata targets dannew/ontech with @dannew as maintainer. Publication is on hold until real-account hardware testing, validation, and owner approval. Catalog inclusion also requires external review. |
| BUG-005 | Localization | Fixed in 0.2.0 | Entity names and action errors were hardcoded and project documentation was Swedish-only. English is now the source language, with complete Swedish runtime translations. |
| BUG-006 | Lifecycle | Fixed in 0.2.0 | Runtime data used hass.data and cleanup did not explicitly cancel coordinator refreshes. The integration now uses typed ConfigEntry.runtime_data and coordinator shutdown. HTTP authentication failures start reauthentication; WebSocket session expiration is retried automatically (see BUG-008). |
| BUG-007 | Authentication | Fixed in 0.2.1 | Login redirects to /login now raise an authentication error, including after a rejected password. Regression server uses Laravel-style HTTP 302. |
| BUG-008 | Session | Fixed in 0.2.1 | WebSocket session expiration no longer prompts for credentials immediately; connection supervision retries login, and only a rejected HTTP login requests reauthentication. |
| BUG-009 | Availability | Fixed in 0.2.1 | Naive timestamps in statusUTC and temperaturesUTC are interpreted as UTC. |
| BUG-010 | Setup | Fixed in 0.2.1 | Initial sync no longer requires optional names before accepting valid device status. |
| BUG-011 | Verification | Open | Verify application ping responses during quiet periods, removal of devices, expansion-device hierarchy, and avoid redundant entity updates. Review CI action SHA pinning and broader async lint rules separately. |
