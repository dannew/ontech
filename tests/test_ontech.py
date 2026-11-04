import asyncio
import copy
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest
from aiohttp import web
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.ontech import api
from custom_components.ontech.api import OntechAuthError, OntechClient, OntechError, websocket_url
from custom_components.ontech.config_flow import OntechConfigFlow
from custom_components.ontech.coordinator import OntechCoordinator
from custom_components.ontech.model import boolean, fresh, has_relay, number, relay_command, value
from custom_components.ontech.sensor import SENSORS, OntechTemperature
from custom_components.ontech.switch import RELAY, OntechRelay


def status():
    return {
        "command": "status",
        "iccid": "test-device",
        "statusUTC": datetime.now(UTC).isoformat(),
        "settings": [0] * 20,
        "units": {
            "connected": [9060, 9012, 0],
            "status": [0, 0, 0],
            "intTemp": ["21.5", "nc", ""],
            "extTemp": ["na", "0", ""],
            "inputA": [1, 0, 0],
            "inputB": [0, 0, 0],
        },
    }


@pytest.mark.parametrize("raw", [None, "", "nc", "na", "NaN", "inf", "bad"])
def test_invalid_temperatures(raw):
    assert number(raw) is None


def test_zero_and_missing_values():
    assert number("0") == 0
    assert number("-12.3") == -12.3
    assert boolean("0") is False
    assert boolean("1") is True
    assert boolean("nc") is None
    assert value(status(), "intTemp", 7) is None


def test_age_and_model_guards():
    data = status()
    assert fresh(data)
    assert has_relay(data, 0)
    assert not has_relay(data, 1)
    data["settings"][10] = 1
    assert not has_relay(data, 0)
    data["statusUTC"] = (datetime.now(UTC) - timedelta(minutes=31)).isoformat()
    assert not fresh(data)
    assert not fresh({"statusUTC": "invalid"})


def test_commands():
    assert relay_command("abc", 0, True) == {"command": "sms", "iccid": "abc", "data": "1*1#"}
    assert relay_command("abc", 7, False)["data"] == "0*8#"
    with pytest.raises(ValueError):
        relay_command("abc", 8, True)


@pytest.mark.parametrize(
    "url",
    [
        "ws://app.ontechcontrol.com/ws",
        "wss://evil.example/ws",
        "wss://ontechcontrol.com.evil.example/ws",
    ],
)
def test_endpoint_validation(url):
    with pytest.raises(OntechError):
        websocket_url(f'var WEBSOCKET_URL = "{url}";')


def test_endpoint_extract():
    assert (
        websocket_url('const WEBSOCKET_URL = "wss:\\/\\/app.ontechcontrol.com/ws?a=1&amp;b=2";')
        == "wss://app.ontechcontrol.com/ws?a=1&b=2"
    )


@pytest.fixture
async def server():
    app = web.Application()
    received = []
    sockets = []

    async def login(request):
        if request.method == "GET":
            response = web.Response(
                text='<form id="loginForm"><input name="_token" value="csrf"></form>'
            )
            response.set_cookie("csrf-session", "yes")
            return response
        data = await request.post()
        assert request.cookies.get("csrf-session") == "yes"
        assert data["_token"] == "csrf"
        assert data["fromLocation"] == "local"
        if data["password"] != "correct":
            raise web.HTTPFound("/login")
        response = web.HTTPFound("/")
        response.set_cookie("account", "yes")
        raise response

    async def account(request):
        assert request.cookies.get("account") == "yes"
        return web.Response(text='var WEBSOCKET_URL = "wss://app.ontechcontrol.com/socket";')

    async def socket(request):
        assert request.cookies.get("account") == "yes"
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        sockets.append(ws)
        await ws.send_json({"command": "get_account_info", "iccids": ["test-device"]})
        await ws.send_json(
            {
                "command": "get_names",
                "iccid": "test-device",
                "systemName": "Cabin",
                "units": ["Heater"],
            }
        )
        await ws.send_json(status())
        async for message in ws:
            data = message.json()
            received.append(data)
            if data["command"] == "ping":
                await ws.send_json(data)
        return ws

    app.router.add_route("*", "/login", login)
    app.router.add_get("/", account)
    app.router.add_get("/socket", socket)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]
    base = f"http://127.0.0.1:{port}"
    try:
        with (
            patch.object(api, "BASE_URL", base),
            patch.object(api, "websocket_url", return_value=f"ws://127.0.0.1:{port}/socket"),
        ):
            yield received, sockets
    finally:
        for ws in sockets:
            await ws.close()
        await runner.cleanup()


@pytest.fixture
async def client(server):
    session = aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar(unsafe=True))
    client = OntechClient(session, "test@example.com", "correct")
    yield client
    await client.close()
    await session.close()


async def test_real_http_and_websocket(client, server):
    await client.connect()
    assert (await client.receive())["command"] == "get_account_info"
    assert (await client.receive())["systemName"] == "Cabin"
    assert (await client.receive())["units"]["status"][0] == 0
    await client.send(relay_command("test-device", 0, True))
    await client.send({"command": "ping"})
    assert (await client.receive())["command"] == "ping"
    assert server[0][0]["data"] == "1*1#"


async def test_wrong_password(client):
    client.password = "wrong"
    with pytest.raises(OntechAuthError):
        await client.connect()


async def test_server_auth_expired(client, server):
    await client.connect()
    for _ in range(3):
        await client.receive()
    await server[1][0].send_json({"error": "-1"})
    with pytest.raises(OntechAuthError):
        await client.receive()


async def test_malformed_message(client, server):
    await client.connect()
    for _ in range(3):
        await client.receive()
    await server[1][0].send_str("not json")
    with pytest.raises(OntechError):
        await client.receive()


def entry_mock():
    entry = MagicMock()
    entry.pref_disable_polling = False
    entry.async_create_background_task.side_effect = lambda hass, coro, name: asyncio.create_task(
        coro
    )
    return entry


async def test_coordinator_entities_reconnect_and_cleanup(client, server, tmp_path):
    hass = HomeAssistant(str(tmp_path))
    coordinator = OntechCoordinator(hass, entry_mock(), client)
    try:
        coordinator.data = await coordinator._async_update_data()
        coordinator.last_update_success = True
        relay = OntechRelay(coordinator, "test-device", 0, RELAY)
        temperature = OntechTemperature(coordinator, "test-device", 0, SENSORS[0])
        assert relay.available
        assert relay.is_on is False
        assert temperature.native_value == 21.5
        assert relay.device_info["name"] == "Cabin Heater"
        await relay.async_turn_on()
        assert relay.is_on is False
        updated = copy.deepcopy(status())
        updated["units"]["status"][0] = 1
        await server[1][0].send_json(updated)
        async with asyncio.timeout(2):
            while relay.is_on is not True:
                await asyncio.sleep(0.01)
        await server[1][0].close()
        async with asyncio.timeout(2):
            while not coordinator.reader.done():
                await asyncio.sleep(0.01)
        assert not relay.available
        with pytest.raises(HomeAssistantError):
            await relay.async_turn_off()
        coordinator.data = await coordinator._async_update_data()
        assert len(server[1]) == 2
    finally:
        await coordinator.async_shutdown()
    assert client.session.closed
    assert coordinator.reader is None


async def test_coordinator_error_mapping(tmp_path):
    client = MagicMock()
    client.close = AsyncMock()
    client.connect = AsyncMock(side_effect=OntechAuthError())
    coordinator = OntechCoordinator(HomeAssistant(str(tmp_path)), entry_mock(), client)
    with pytest.raises(ConfigEntryAuthFailed):
        await coordinator._async_update_data()
    client.connect.side_effect = OntechError()
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


@pytest.mark.parametrize(
    "error,expected", [(OntechAuthError(), "invalid_auth"), (OntechError(), "cannot_connect")]
)
async def test_config_flow_errors(error, expected, tmp_path):
    client = MagicMock()
    client.connect = AsyncMock(side_effect=error)
    client.close = AsyncMock()
    client.session.close = AsyncMock()
    flow = OntechConfigFlow()
    flow.hass = HomeAssistant(str(tmp_path))
    with (
        patch("custom_components.ontech.config_flow.create_client", return_value=client),
        patch.object(flow, "async_set_unique_id", new_callable=AsyncMock),
        patch.object(flow, "_abort_if_unique_id_configured"),
    ):
        result = await flow.async_step_user({"email": "test@example.com", "password": "wrong"})
    assert result["errors"]["base"] == expected
    client.session.close.assert_awaited_once()


async def test_late_discovery_and_no_duplicates(tmp_path):
    from custom_components.ontech.sensor import async_setup_entry

    hass = HomeAssistant(str(tmp_path))
    entry = entry_mock()
    coordinator = OntechCoordinator(hass, entry, MagicMock())
    coordinator.data = {}
    coordinator.async_add_listener = MagicMock(return_value=lambda: None)
    entry.runtime_data = coordinator
    add = MagicMock()
    await async_setup_entry(hass, entry, add)
    add.assert_not_called()
    listener = coordinator.async_add_listener.call_args.args[0]
    coordinator.data = {"test-device": status()}
    listener()
    assert len(add.call_args.args[0]) == 2
    listener()
    assert add.call_count == 1
    coordinator.data["test-device"]["units"]["extTemp"][0] = "10"
    listener()
    assert add.call_count == 2
    assert len(add.call_args.args[0]) == 1


async def test_config_flow_success(client, tmp_path):
    flow = OntechConfigFlow()
    flow.hass = HomeAssistant(str(tmp_path))
    with (
        patch("custom_components.ontech.config_flow.create_client", return_value=client),
        patch.object(flow, "async_set_unique_id", new_callable=AsyncMock) as unique,
        patch.object(flow, "_abort_if_unique_id_configured"),
    ):
        result = await flow.async_step_user({"email": " TEST@example.com ", "password": "correct"})
    unique.assert_awaited_once_with("test@example.com")
    assert result["type"] == "create_entry"
    assert result["data"]["email"] == "test@example.com"
    assert client.session.closed


async def test_reauth_keeps_existing_account(tmp_path):
    flow = OntechConfigFlow()
    flow.hass = HomeAssistant(str(tmp_path))
    original = MagicMock(data={"email": "first@example.com"})
    with (
        patch.object(flow, "_get_reauth_entry", return_value=original),
        patch.object(
            flow, "_validate_credentials", new_callable=AsyncMock, return_value=None
        ) as validate,
        patch.object(
            flow, "async_update_reload_and_abort", return_value={"type": "abort"}
        ) as reload_entry,
    ):
        form = await flow.async_step_reauth({})
        assert form["description_placeholders"] == {"email": "first@example.com"}
        assert list(form["data_schema"].schema) == ["password"]
        await flow.async_step_reauth_confirm({"email": "second@example.com", "password": "new"})
    expected = {"email": "first@example.com", "password": "new"}
    validate.assert_awaited_once_with(expected)
    reload_entry.assert_called_once_with(original, data_updates=expected)


async def test_unload_closes_connection(tmp_path):
    from custom_components.ontech import async_unload_entry

    hass = HomeAssistant(str(tmp_path))
    hass.config_entries = MagicMock()
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
    entry = entry_mock()
    coordinator = MagicMock()
    coordinator.async_shutdown = AsyncMock()
    entry.runtime_data = coordinator
    assert await async_unload_entry(hass, entry)
    coordinator.async_shutdown.assert_awaited_once()


async def test_duplicate_account_does_not_contact_service(tmp_path):
    from homeassistant.data_entry_flow import AbortFlow

    flow = OntechConfigFlow()
    flow.hass = HomeAssistant(str(tmp_path))
    with (
        patch.object(flow, "async_set_unique_id", new_callable=AsyncMock),
        patch.object(
            flow, "_abort_if_unique_id_configured", side_effect=AbortFlow("already_configured")
        ),
        patch.object(flow, "_validate_credentials", new_callable=AsyncMock) as validate,
        pytest.raises(AbortFlow),
    ):
        await flow.async_step_user({"email": "same@example.com", "password": "secret"})
    validate.assert_not_awaited()


async def test_push_auth_failure_does_not_start_reauth(tmp_path):
    client = MagicMock()
    client.receive = AsyncMock(side_effect=OntechAuthError())
    client.close = AsyncMock()
    entry = entry_mock()
    hass = HomeAssistant(str(tmp_path))
    coordinator = OntechCoordinator(hass, entry, client)
    await coordinator._listen()
    assert not coordinator.last_update_success
    entry.async_start_reauth.assert_not_called()
    client.close.assert_awaited_once()


async def test_failed_platform_setup_closes_resources(tmp_path):
    from custom_components.ontech import async_setup_entry

    hass = HomeAssistant(str(tmp_path))
    hass.config_entries = MagicMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock(side_effect=RuntimeError("failure"))
    coordinator = MagicMock()
    coordinator.async_config_entry_first_refresh = AsyncMock()
    coordinator.async_shutdown = AsyncMock()
    with (
        patch("custom_components.ontech.create_client"),
        patch("custom_components.ontech.OntechCoordinator", return_value=coordinator),
        pytest.raises(RuntimeError),
    ):
        await async_setup_entry(hass, entry_mock())
    coordinator.async_shutdown.assert_awaited_once()


async def test_failed_unload_keeps_resources(tmp_path):
    from custom_components.ontech import async_unload_entry

    hass = HomeAssistant(str(tmp_path))
    hass.config_entries = MagicMock()
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=False)
    entry = entry_mock()
    entry.runtime_data.async_shutdown = AsyncMock()
    assert not await async_unload_entry(hass, entry)
    entry.runtime_data.async_shutdown.assert_not_awaited()


async def test_diagnostics_do_not_export_account_or_device_identifiers(tmp_path):
    import json

    from custom_components.ontech.diagnostics import async_get_config_entry_diagnostics

    hass = HomeAssistant(str(tmp_path))
    entry = entry_mock()
    entry.data = {"email": "private@example.com", "password": "private-password"}
    coordinator = OntechCoordinator(hass, entry, MagicMock())
    entry.runtime_data = coordinator
    coordinator.data = {"private-iccid": {**status(), "email": "private@example.com"}}
    coordinator.names = {"private-iccid": {"systemName": "private-home"}}
    result = await async_get_config_entry_diagnostics(hass, entry)
    assert result["systems"][0]["models"] == [9060, 9012]
    encoded = json.dumps(result)
    for secret in (
        "private@example.com",
        "private-password",
        "private-iccid",
        "private-home",
        "test-device",
    ):
        assert secret not in encoded


def test_naive_utc_timestamps():
    now = datetime(2026, 11, 4, 10, 0, tzinfo=UTC)
    assert fresh({"statusUTC": "2026-11-04 09:59:00"}, now)
    assert not fresh({"statusUTC": "2026-11-04 09:00:00"}, now)


async def test_initial_sync_without_names(client, tmp_path):
    coordinator = OntechCoordinator(HomeAssistant(str(tmp_path)), entry_mock(), client)
    original = client.receive

    async def receive_without_names():
        message = await original()
        while message.get("command") == "get_names":
            message = await original()
        return message

    with patch.object(client, "receive", side_effect=receive_without_names):
        try:
            data = await coordinator._async_update_data()
            assert "test-device" in data
            assert not coordinator.names
        finally:
            await coordinator.async_shutdown()
