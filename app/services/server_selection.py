from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.enums import ServerGroupSelectionMode, ServerHealthStatus
from app.db.models.server import Server, ServerGroupServer
from app.db.models.tariff import Tariff


class NoAvailableServerError(ValueError):
    pass


@dataclass(frozen=True)
class SelectedInbound:
    server: Server
    inbound_id: str
    protocol: str
    inbound_remark: str | None = None


class ServerSelectionService:
    def __init__(self, session: AsyncSession, *, allow_degraded: bool = False) -> None:
        self.session = session
        self.allow_degraded = allow_degraded

    async def select_for_tariff(self, tariff: Tariff) -> list[SelectedInbound]:
        if tariff.inbound_links:
            selected = [
                SelectedInbound(
                    server=link.server,
                    inbound_id=link.inbound_id,
                    protocol=(link.protocol or "vless").lower(),
                    inbound_remark=link.inbound_remark,
                )
                for link in tariff.inbound_links
                if self._server_ok(link.server)
            ]
            if selected:
                return selected

        selected_from_groups: list[SelectedInbound] = []
        for link in tariff.server_group_links:
            servers = await self._group_servers(link.server_group_id)
            if link.selection_mode == ServerGroupSelectionMode.ONE:
                servers = servers[:1]
            selected_from_groups.extend(
                SelectedInbound(server=server, inbound_id="1", protocol="vless")
                for server in servers
            )
        if selected_from_groups:
            return selected_from_groups
        raise NoAvailableServerError("No available server/inbound for tariff.")

    async def _group_servers(self, group_id: int) -> list[Server]:
        result = await self.session.execute(
            select(Server)
            .join(ServerGroupServer, ServerGroupServer.server_id == Server.id)
            .where(ServerGroupServer.group_id == group_id, Server.enabled.is_(True))
            .options(selectinload(Server.subscription_nodes))
        )
        servers = [server for server in result.scalars().unique() if self._server_ok(server)]
        return sorted(servers, key=self._server_sort_key)

    def _server_ok(self, server: Server) -> bool:
        if not server.enabled or server.last_health_status == ServerHealthStatus.OFFLINE:
            return False
        if server.last_health_status == ServerHealthStatus.DEGRADED and not self.allow_degraded:
            return False
        return server.max_users is None or server.current_users < server.max_users

    @staticmethod
    def _server_sort_key(server: Server) -> tuple[int, int, float, int]:
        capacity = server.max_users or 1
        load = server.current_users / capacity
        online_rank = 0 if server.last_health_status == ServerHealthStatus.ONLINE else 1
        return (online_rank, server.priority, load, server.id)
