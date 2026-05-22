from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class PanelClientRef:
    external_id: str
    subscription_url: str | None = None


class PanelProvider(Protocol):
    async def create_client(
        self, *, inbound_id: str, payload: dict[str, object]
    ) -> PanelClientRef: ...

    async def update_client(self, *, client_id: str, payload: dict[str, object]) -> None: ...

    async def delete_client(self, *, client_id: str) -> None: ...

    async def disable_client(self, *, client_id: str) -> None: ...

    async def enable_client(self, *, client_id: str) -> None: ...

    async def reset_traffic(self, *, client_id: str) -> None: ...

    async def get_client_stats(self, *, client_id: str) -> dict[str, object]: ...

    async def get_subscription_url(self, *, client_id: str) -> str | None: ...
