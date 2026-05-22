from app.services.panels.base import PanelClientRef


class XuiProvider:
    """3X-UI adapter shell. HTTP operations are implemented in Stage 2."""

    async def create_client(self, *, inbound_id: str, payload: dict[str, object]) -> PanelClientRef:
        raise NotImplementedError("3X-UI client provisioning is implemented in Stage 2.")

    async def update_client(self, *, client_id: str, payload: dict[str, object]) -> None:
        raise NotImplementedError

    async def delete_client(self, *, client_id: str) -> None:
        raise NotImplementedError

    async def disable_client(self, *, client_id: str) -> None:
        raise NotImplementedError

    async def enable_client(self, *, client_id: str) -> None:
        raise NotImplementedError

    async def reset_traffic(self, *, client_id: str) -> None:
        raise NotImplementedError

    async def get_client_stats(self, *, client_id: str) -> dict[str, object]:
        raise NotImplementedError

    async def get_subscription_url(self, *, client_id: str) -> str | None:
        raise NotImplementedError
