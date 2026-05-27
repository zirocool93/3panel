from enum import StrEnum


class AdminRole(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    SUPPORT = "support"
    ACCOUNTANT = "accountant"
    MARKETER = "marketer"


class PanelProviderType(StrEnum):
    XUI = "xui"


class PaymentProviderType(StrEnum):
    MANUAL = "manual"
    TELEGRAM_STARS = "telegram_stars"
    CARDLINK = "cardlink"
    YOOKASSA = "yookassa"


class ServerHealthStatus(StrEnum):
    UNKNOWN = "unknown"
    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"


class ServerGroupSelectionMode(StrEnum):
    ONE = "one"
    ALL = "all"


class SubscriptionStatus(StrEnum):
    PENDING = "pending"
    ACTIVE = "active"
    EXPIRED = "expired"
    DISABLED = "disabled"
    PROVISIONING_FAILED = "provisioning_failed"


class SubscriptionNodeStatus(StrEnum):
    PENDING = "pending"
    ACTIVE = "active"
    DISABLED = "disabled"
    FAILED = "failed"
    DELETED = "deleted"
