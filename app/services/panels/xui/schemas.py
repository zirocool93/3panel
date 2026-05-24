from pydantic import BaseModel, Field


class XuiInbound(BaseModel):
    id: int
    remark: str | None = None
    protocol: str | None = None
    enable: bool | None = None
    port: int | None = None


class XuiClientStats(BaseModel):
    id: int | None = None
    inbound_id: int | None = Field(default=None, alias="inboundId")
    email: str | None = None
    up: int = 0
    down: int = 0
    total: int = 0
    enable: bool | None = None
