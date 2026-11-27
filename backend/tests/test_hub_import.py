import asyncio
import socket

import httpx
import pytest

from app.services.hub_import import HubImportError, _fetch_html


def test_import_pins_dns_and_rechecks_redirects(monkeypatch):
    async def resolve(self, host, port, *, type):
        address = "93.184.216.34" if host == "example.com" else "127.0.0.1"
        return [(socket.AF_INET, type, 6, "", (address, port))]

    def respond(request):
        assert request.url.host == "93.184.216.34"
        assert request.headers["Host"] == "example.com"
        assert request.extensions["sni_hostname"] == "example.com"
        return httpx.Response(302, headers={"Location": "http://internal.example/"})

    monkeypatch.setattr(asyncio.BaseEventLoop, "getaddrinfo", resolve)

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            with pytest.raises(HubImportError, match="public addresses"):
                await _fetch_html(client, "https://example.com")

    asyncio.run(run())
