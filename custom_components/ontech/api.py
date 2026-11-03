"""Client for the protocol used by the Ontech Control web application."""

import asyncio
import json
import re
from html import unescape
from html.parser import HTMLParser
from urllib.parse import urlsplit

import aiohttp

from .const import BASE_URL


class OntechError(Exception):
    """The service could not complete a request."""


class OntechAuthError(OntechError):
    """The account needs authentication."""


class LoginPage(HTMLParser):
    def __init__(self):
        super().__init__()
        self.token = None
        self.login_form = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "input" and attrs.get("name") == "_token":
            self.token = attrs.get("value")
        if tag == "form" and attrs.get("id") == "loginForm":
            self.login_form = True


def websocket_url(page):
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
    def __init__(self, session, email, password):
        self.session = session
        self.email = email
        self.password = password
        self.ws = None

    async def _page(self, method, path, **kwargs):
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
                return None
            return await response.text()

    async def connect(self):
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
        except (aiohttp.ClientError, TimeoutError):
            raise OntechError("Unable to connect to Ontech") from None

    async def receive(self):
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
        except (aiohttp.ClientError, ValueError) as err:
            raise OntechError("Invalid response from Ontech") from err

    async def send(self, data):
        if self.ws is None or self.ws.closed:
            raise OntechError("Not connected")
        try:
            await self.ws.send_json(data)
        except (aiohttp.ClientError, ConnectionError) as err:
            raise OntechError("Unable to send command") from err

    async def close(self):
        if self.ws is not None:
            await self.ws.close()
            self.ws = None
