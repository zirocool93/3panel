from pydantic import BaseModel


class AdminUpdateStatus(BaseModel):
    enabled: bool
    running: bool
    ref: str
    log_tail: list[str]
