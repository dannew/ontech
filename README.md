# Ontech Control for Home Assistant

![Ontech Control community integration icon](custom_components/ontech/brand/icon.png)

A community integration for [Ontech Control](https://app.ontechcontrol.com). Control relays and monitor temperatures and binary inputs through your existing Ontech account.

**Experimental:** account login and physical device control still need verification with real hardware. Automated tests use a simulated Ontech server. This integration is not affiliated with or supported by Ontech. Known limitations and feature requests are tracked in [BUGS.md](BUGS.md).

## Requirements

- Home Assistant Core **2026.10.4 or newer**.
- An Ontech Control account with devices accessible in the web application.
- Internet access from Home Assistant to Ontech Control. This is a cloud integration; it does not communicate directly with the devices.
- No additional Python dependencies beyond Home Assistant itself.

## Installation

### Marketplace (Home Assistant 2026.11 and later)

This integration is **not yet released or included in the catalog**. After hardware testing and validation, add `https://github.com/dannew/ontech` as a custom repository with type **Integration** in **Settings → Marketplace**, then install **Ontech Control** and restart Home Assistant.

### HACS (Home Assistant 2026.10)

After hardware testing and validation, add `https://github.com/dannew/ontech` under **HACS → Custom repositories**, select **Integration**, download **Ontech Control**, and restart Home Assistant.

The Marketplace uses the same repository layout, catalog, and `hacs.json` as HACS. See the [Marketplace documentation](https://contributors.home-assistant.io/marketplace/).

### Manual installation

1. Copy `custom_components/ontech` into `<config>/custom_components/ontech`.
2. Restart Home Assistant.
3. Continue with configuration below.

### Configuration

Open **Settings → Devices & services → Add integration → Ontech Control**.

| Field | Description |
| --- | --- |
| Email | The email address used to sign in to Ontech Control. |
| Password | The password for that account. |

Credentials are stored in Home Assistant's standard config entry storage. Do not put them in this repository or in `configuration.yaml`. If authentication expires, Home Assistant prompts you to reauthenticate the existing account; only the password is requested.

English is the source and fallback language. Swedish translations are included for setup, entities, default device names, and errors. Home Assistant selects the appropriate translation; names you configured in Ontech are retained.

## Supported entities

| Entity | Function |
| --- | --- |
| Relay switch | Turn a supported relay on or off. |
| Internal temperature | Read the built-in temperature sensor, when reported. |
| External temperature | Read an attached temperature sensor, when reported. |
| Input A / Input B | Read the raw binary inputs, when reported. |

The relay model allowlist is **9010, 9015, 9025, 9035, 9040, 9060, and 9065**, based on the web protocol. It is not a list of hardware-tested models. Model 9012 and master units configured in garage mode do not get relay switches.

Thermostats, heat pumps, scheduling, alarm acknowledgement, and garage pulses are not implemented. Inputs are not assigned a door, motion, or alarm device class because their meaning depends on your wiring.

## Updates and availability

The integration keeps an authenticated WebSocket open and discovers units as their status arrives. A supervisor runs approximately once a minute when no push data is arriving, checks connection health, and reconnects after a failure. The server's cached status is requested on connection; there is no periodic SMS request to the hardware.

Relays keep their last reported state until Ontech sends an update. Sending a command is not a delivery acknowledgement. Devices become unavailable when the connection fails, the unit disconnects, or both the most recent status and temperature report are older than 30 minutes. Invalid temperatures, including `nc`, `na`, and empty values, become unknown rather than zero.

Use the standard `switch.turn_on` and `switch.turn_off` actions in automations. Temperature sensors support numeric-state triggers, for example a low-temperature notification. Choose entity IDs from your own installation in the automation editor.

## Troubleshooting and diagnostics

1. Confirm that login works in the Ontech web application and that the devices are current there.
2. Check internet connectivity if Home Assistant reports a connection error. Transient failures are retried automatically.
3. Complete the reauthentication flow if prompted. Reauthenticate the existing entry rather than adding a duplicate account.
4. After installation or an upgrade, restart Home Assistant. Refresh the browser if an old label is still displayed.
5. Download diagnostics from the integration's menu when reporting an issue. The export contains only connection health, freshness flags, and model numbers. It excludes credentials, cookies, WebSocket URLs, ICCIDs, names, and raw account payloads.

For hardware verification, compare device names and temperatures with Ontech, test an appropriate relay load, check the reported state after switching, and test reconnection after a restart. Include your model and Home Assistant version in bug reports. Never share passwords, cookies, ICCIDs, or session-bearing URLs.

## Removal

Delete the account entry under **Settings → Devices & services**. To uninstall the files as well, remove the integration in Marketplace/HACS, or delete `custom_components/ontech` after a manual installation, then restart Home Assistant.

## Development and publication

```sh
uv venv --python 3.14 .venv
uv pip install --python .venv/bin/python homeassistant==2026.10.4 -r requirements-test.txt
.venv/bin/python -m pytest
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/python scripts/check_release.py
```

Locally verified: 38 tests pass on both Home Assistant 2026.10.4 and 2026.11.0b3. CI runs the same version matrix, plus Ruff, hassfest, and HACS validation. Repository metadata targets `dannew/ontech`, maintained by `@dannew`. Publication requires hardware testing, validation, and explicit release approval. Passing local tests is not catalog approval. See [RELEASING.md](RELEASING.md) for the remaining publishing steps.

The private protocol was mapped from [Ontech's public web client](https://app.ontechcontrol.com/js/all.js). No Ontech JavaScript is distributed here. It uses `get_account_info`, `get_names`, `get_status`, `status`, `ping`, and `sms`; a relay command such as `1*1#` targets unit 1. The protocol may change without notice.

Licensed under the [MIT license](LICENSE). The bundled relay icon is an original community-integration graphic, not an Ontech or Home Assistant logo.
