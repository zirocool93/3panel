import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import httpx

from app.services.panels.base import PanelClientRef
from app.services.panels.xui.exceptions import XuiAuthenticationError, XuiRequestError
from app.services.panels.xui.schemas import XuiClientStats, XuiInbound


@dataclass(frozen=True)
class XuiCredentials:
    panel_url: str
    username: str
    password: str


class XuiProvider:
    """3X-UI HTTP adapter.

    The adapter keeps the public PanelProvider contract narrow, while exposing
    server-management helpers used by the admin API: healthcheck and inbound list.
    """

    def __init__(
        self,
        credentials: XuiCredentials,
        *,
        client: httpx.AsyncClient | None = None,
        timeout: float = 15,
    ) -> None:
        self._credentials = credentials
        self._owned_client = client is None
        self._client = client or httpx.AsyncClient(
            base_url=credentials.panel_url.rstrip("/"),
            timeout=timeout,
            follow_redirects=True,
        )
        self._authenticated = False

    async def __aenter__(self) -> "XuiProvider":
        return self

    async def __aexit__(self, *_args: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._owned_client:
            await self._client.aclose()

    async def login(self) -> None:
        response = await self._client.post(
            "/login",
            data={"username": self._credentials.username, "password": self._credentials.password},
        )
        if response.status_code not in {200, 204}:
            raise XuiAuthenticationError(f"3X-UI login failed with HTTP {response.status_code}.")
        payload = _json_or_empty(response)
        if payload and payload.get("success") is False:
            raise XuiAuthenticationError(str(payload.get("msg") or "3X-UI rejected credentials."))
        self._authenticated = True

    async def healthcheck(self) -> bool:
        await self.login()
        await self.get_inbounds()
        return True

    async def get_inbounds(self) -> list[XuiInbound]:
        payload = await self._request("GET", "/panel/api/inbounds/list")
        items = payload.get("obj") if isinstance(payload, Mapping) else None
        if not isinstance(items, list):
            return []
        return [XuiInbound.model_validate(item) for item in items]

    async def create_client(
        self, *, inbound_id: str, payload: dict[str, object]
    ) -> PanelClientRef:
        body = {"id": int(inbound_id), "settings": json.dumps({"clients": [payload]})}
        await self._request("POST", "/panel/api/inbounds/addClient", json=body)
        client_uuid = str(
            payload.get("id") or payload.get("client_uuid") or payload.get("uuid") or ""
        )
        email = str(payload.get("email") or "")
        external_id = _pack_client_id(inbound_id=inbound_id, client_uuid=client_uuid, email=email)
        return PanelClientRef(
            external_id=external_id,
            subscription_url=await self.get_subscription_url(client_id=external_id),
        )

    async def update_client(self, *, client_id: str, payload: dict[str, object]) -> None:
        ref = _unpack_client_id(client_id)
        await self._request(
            "POST",
            f"/panel/api/inbounds/updateClient/{ref.client_uuid}",
            json={"id": int(ref.inbound_id), "settings": json.dumps({"clients": [payload]})},
        )

    async def delete_client(self, *, client_id: str) -> None:
        ref = _unpack_client_id(client_id)
        await self._request(
            "POST",
            f"/panel/api/inbounds/{int(ref.inbound_id)}/delClient/{ref.client_uuid}",
        )

    async def disable_client(self, *, client_id: str) -> None:
        ref = _unpack_client_id(client_id)
        await self.update_client(
            client_id=client_id,
            payload={"id": ref.client_uuid, "email": ref.email, "enable": False},
        )

    async def enable_client(self, *, client_id: str) -> None:
        ref = _unpack_client_id(client_id)
        await self.update_client(
            client_id=client_id,
            payload={"id": ref.client_uuid, "email": ref.email, "enable": True},
        )

    async def reset_traffic(self, *, client_id: str) -> None:
        ref = _unpack_client_id(client_id)
        await self._request(
            "POST",
            f"/panel/api/inbounds/{int(ref.inbound_id)}/resetClientTraffic/{ref.email}",
        )

    async def get_client_stats(self, *, client_id: str) -> dict[str, object]:
        ref = _unpack_client_id(client_id)
        payload = await self._request("GET", f"/panel/api/inbounds/getClientTraffics/{ref.email}")
        obj = payload.get("obj") if isinstance(payload, Mapping) else None
        if not isinstance(obj, Mapping):
            return {}
        return XuiClientStats.model_validate(obj).model_dump()

    async def get_subscription_url(self, *, client_id: str) -> str | None:
        ref = _unpack_client_id(client_id)
        if not ref.email:
            return None
        base_url = str(self._client.base_url).rstrip("/")
        return f"{base_url}/sub/{ref.email}"

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        if not self._authenticated:
            await self.login()
        response = await self._client.request(method, path, **kwargs)
        if response.status_code >= 400:
            raise XuiRequestError(f"3X-UI request {path} failed with HTTP {response.status_code}.")
        payload = _json_or_empty(response)
        if payload.get("success") is False:
            raise XuiRequestError(str(payload.get("msg") or f"3X-UI request {path} failed."))
        return payload


@dataclass(frozen=True)
class _ClientId:
    inbound_id: str
    client_uuid: str
    email: str


def _pack_client_id(*, inbound_id: str, client_uuid: str, email: str) -> str:
    return f"{inbound_id}:{client_uuid}:{email}"


def _unpack_client_id(client_id: str) -> _ClientId:
    parts = client_id.split(":", 2)
    if len(parts) != 3:
        raise XuiRequestError("Некорректный идентификатор клиента 3X-UI.")
    return _ClientId(inbound_id=parts[0], client_uuid=parts[1], email=parts[2])


def _json_or_empty(response: httpx.Response) -> dict[str, Any]:
    if not response.content:
        return {}
    try:
        payload = response.json()
    except ValueError:
        return {}
    return payload if isinstance(payload, dict) else {}
