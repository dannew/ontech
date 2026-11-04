"""Client for the protocol used by the Ontech Control web application."""

import asyncio
import json
import re
from html import unescape
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urlsplit

import aiohttp

from .const import BASE_URL


class OntechError(Exception):
    """The service could not complete a request."""


class OntechAuthError(OntechError):
    """The account needs authentication."""


class LoginPage(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.token: str | None = None
        self.login_form = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "input" and attributes.get("name") == "_token":
            self.token = attributes.get("value")
        if tag == "form" and attributes.get("id") == "loginForm":
            self.login_form = True


def websocket_url(page: str) -> str:
    match = re.search(r"\bWEBSOCKET_URL\s*=\s*([\"'])(.*?)\1", page)
    if not match:
        raise OntechError("The account page contains no WebSocket URL")
    url = unescape(match[2].replace(r"\/", "/"))
    parsed = urlsplit(url)
    host = parsed.hostname or ""
    if (
        parsed.scheme != "wss"
        or not (host == "ontechcontrol.com" or host.endswith(".ontechcontrol.com"))
        or parsed.username
        or parsed.password
    ):
        raise OntechError("Unexpected WebSocket endpoint")
    return url


class OntechClient:
    def __init__(self, session: aiohttp.ClientSession, email: str, password: str) -> None:
        self.session = session
        self.email = email
        self.password = password
        self.ws: aiohttp.ClientWebSocketResponse | None = None

    async def _page(self, method: str, path: str, **kwargs: Any) -> str | None:
        async with self.session.request(
            method, BASE_URL + path, allow_redirects=False, **kwargs
        ) as response:
            if response.status in (401, 403):
                raise OntechAuthError("Authentication rejected")
            if response.status >= 400:
                raise OntechError(f"Ontech returned HTTP {response.status}")
            if 300 <= response.status < 400:
                location = response.headers.get("Location", "/")
                target = urlsplit(location)
                if target.netloc and target.netloc != urlsplit(BASE_URL).netloc:
                    raise OntechError("Unexpected login redirect")
                if target.path.rstrip("/") == "/login":
                    raise OntechAuthError("Login required")
                return None
            return await response.text()

    async def connect(self) -> None:
        await self.close()
        try:
            async with asyncio.timeout(30):
                page = await self._page("GET", "/login")
                if page is None:
                    page = await self._page("GET", "/")
                parser = LoginPage()
                parser.feed(page or "")
                if parser.login_form:
                    if not parser.token:
                        raise OntechError("The login page contains no CSRF token")
                    page = await self._page(
                        "POST",
                        "/login",
                        data={
                            "_token": parser.token,
                            "email": self.email,
                            "password": self.password,
                            "fromLocation": "local",
                        },
                    )
                    if page is None:
                        page = await self._page("GET", "/")
                    parser = LoginPage()
                    parser.feed(page or "")
                    if parser.login_form:
                        raise OntechAuthError("Login rejected")
                url = websocket_url(page or "")
                self.ws = await self.session.ws_connect(
                    url,
                    origin=BASE_URL,
                    heartbeat=30,
                )
        except aiohttp.ClientError, TimeoutError:
            raise OntechError("Unable to connect to Ontech") from None

    async def receive(self) -> dict[str, Any]:
        if self.ws is None:
            raise OntechError("Not connected")
        try:
            message = await self.ws.receive()
            if message.type != aiohttp.WSMsgType.TEXT:
                raise OntechError("Ontech disconnected")
            data = json.loads(message.data)
            if not isinstance(data, dict):
                raise OntechError("Invalid Ontech message")
            if str(data.get("error")) == "-1":
                raise OntechAuthError("Ontech session expired")
            if str(data.get("error", "0")) not in ("0", "None", ""):
                raise OntechError("Ontech rejected the request")
            return data
        except aiohttp.ClientError, ValueError:
            raise OntechError("Invalid response from Ontech") from None

    async def send(self, data: dict[str, Any]) -> None:
        if self.ws is None or self.ws.closed:
            raise OntechError("Not connected")
        try:
            await self.ws.send_json(data)
        except aiohttp.ClientError, ConnectionError:
            raise OntechError("Unable to send command") from None

    async def close(self) -> None:
        ws, self.ws = self.ws, None
        if ws is not None:
            await ws.close()
