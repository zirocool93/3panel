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
    BALANCE = "balance"
    TELEGRAM_STARS = "telegram_stars"
    CRYPTO = "crypto"
    CARDLINK = "cardlink"
    YOOKASSA = "yookassa"


class BalanceTransactionType(StrEnum):
    MANUAL_ADJUSTMENT = "manual_adjustment"
    PAYMENT = "payment"
    SUBSCRIPTION_CHARGE = "subscription_charge"
    REFUND = "refund"
    BONUS = "bonus"


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
