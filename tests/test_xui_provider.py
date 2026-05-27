import json
from urllib.parse import parse_qs

import httpx
import pytest

from app.services.panels.xui import XuiCredentials, XuiProvider


@pytest.mark.asyncio
async def test_xui_provider_healthcheck_and_inbounds() -> None:
    requests: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(f"{request.method} {request.url.path}")
        if request.url.path == "/csrf-token":
            return httpx.Response(200, json={"success": True, "obj": "csrf-token"})
        if request.url.path == "/login":
            assert request.headers["X-CSRF-Token"] == "csrf-token"
            return httpx.Response(200, json={"success": True})
        if request.url.path == "/panel/api/inbounds/list":
            return httpx.Response(
                200,
                json={
                    "success": True,
                    "obj": [{"id": 1, "remark": "DE", "protocol": "vless", "enable": True}],
                },
            )
        return httpx.Response(404)

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://xui.example",
    ) as client:
        provider = XuiProvider(
            XuiCredentials(
                panel_url="https://xui.example",
                username="admin",
                password="password",
            ),
            client=client,
        )
        assert await provider.healthcheck() is True
        inbounds = await provider.get_inbounds()

    assert inbounds[0].id == 1
    assert inbounds[0].protocol == "vless"
    assert requests[:3] == [
        "GET /csrf-token",
        "POST /login",
        "GET /panel/api/inbounds/list",
    ]


@pytest.mark.asyncio
async def test_xui_provider_uses_bearer_token_without_login() -> None:
    requests: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(f"{request.method} {request.url.path}")
        assert request.headers["Authorization"] == "Bearer secret-token"
        if request.url.path == "/panel/api/inbounds/list":
            return httpx.Response(200, json={"success": True, "obj": []})
        return httpx.Response(404)

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://xui.example",
    ) as client:
        provider = XuiProvider(
            XuiCredentials(panel_url="https://xui.example", api_token="secret-token"),
            client=client,
        )
        assert await provider.healthcheck() is True

    assert requests == ["GET /panel/api/inbounds/list"]


@pytest.mark.asyncio
async def test_xui_provider_preserves_web_base_path() -> None:
    requests: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(f"{request.method} {request.url.path}")
        if request.url.path == "/randompath/panel/api/inbounds/addClient":
            return httpx.Response(200, json={"success": True})
        return httpx.Response(404)

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://xui.example/randompath/",
    ) as client:
        provider = XuiProvider(
            XuiCredentials(
                panel_url="https://xui.example/randompath",
                api_token="secret-token",
            ),
            client=client,
        )
        ref = await provider.create_client(
            inbound_id="7",
            payload={"id": "uuid-1", "email": "user-1", "enable": True},
        )

    assert requests == ["POST /randompath/panel/api/inbounds/addClient"]
    assert ref.subscription_url == "https://xui.example/randompath/sub/user-1"


@pytest.mark.asyncio
async def test_xui_provider_create_client_returns_external_ref() -> None:
    bodies: list[dict[str, list[str]]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/csrf-token":
            return httpx.Response(404)
        if request.url.path == "/login":
            return httpx.Response(200, json={"success": True})
        if request.url.path == "/panel/api/inbounds/addClient":
            bodies.append(parse_qs(request.content.decode()))
            return httpx.Response(200, json={"success": True})
        return httpx.Response(404)

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://xui.example",
    ) as client:
        provider = XuiProvider(
            XuiCredentials(
                panel_url="https://xui.example",
                username="admin",
                password="password",
            ),
            client=client,
        )
        ref = await provider.create_client(
            inbound_id="7",
            payload={"id": "uuid-1", "email": "user-1", "enable": True},
        )

    assert ref.external_id == "7:uuid-1:user-1"
    assert ref.subscription_url == "https://xui.example/sub/user-1"
    assert bodies[0]["id"] == ["7"]
    assert json.loads(bodies[0]["settings"][0])["clients"][0]["email"] == "user-1"


@pytest.mark.asyncio
async def test_xui_provider_lists_existing_clients_from_inbounds() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/panel/api/inbounds/list":
            return httpx.Response(
                200,
                json={
                    "success": True,
                    "obj": [
                        {
                            "id": 11,
                            "remark": "VLESS-443",
                            "protocol": "vless",
                            "settings": {
                                "clients": [
                                    {
                                        "id": "uuid-1",
                                        "email": "alice",
                                        "enable": True,
                                        "subId": "sub-1",
                                        "totalGB": 1073741824,
                                    }
                                ]
                            },
                            "clientStats": [
                                {
                                    "email": "alice",
                                    "up": 100,
                                    "down": 200,
                                    "total": 300,
                                    "enable": True,
                                }
                            ],
                        }
                    ],
                },
            )
        return httpx.Response(404)

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://xui.example",
    ) as client:
        provider = XuiProvider(
            XuiCredentials(panel_url="https://xui.example", api_token="secret-token"),
            client=client,
        )
        clients = await provider.get_clients()

    assert len(clients) == 1
    assert clients[0].email == "alice"
    assert clients[0].client_uuid == "uuid-1"
    assert clients[0].sub_id == "sub-1"
    assert clients[0].inbound_id == 11
    assert clients[0].up == 100
    assert clients[0].down == 200
    assert clients[0].traffic_limit == 1073741824
