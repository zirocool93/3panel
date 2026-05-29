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


class OrderStatus(StrEnum):
    DRAFT = "draft"
    PENDING_PAYMENT = "pending_payment"
    PAID = "paid"
    PROVISIONING = "provisioning"
    FULFILLED = "fulfilled"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    FAILED = "failed"


class PaymentStatus(StrEnum):
    CREATED = "created"
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    EXPIRED = "expired"


class PaymentEventType(StrEnum):
    INVOICE_CREATED = "invoice_created"
    PRE_CHECKOUT = "pre_checkout"
    PAYMENT_SUCCEEDED = "payment_succeeded"
    PAYMENT_FAILED = "payment_failed"
    WEBHOOK_RECEIVED = "webhook_received"
    MANUAL_CONFIRMED = "manual_confirmed"
    REFUND_CREATED = "refund_created"


class AuditActorType(StrEnum):
    SYSTEM = "system"
    ADMIN = "admin"
    USER = "user"
    BOT = "bot"


class AuditEntityType(StrEnum):
    USER = "user"
    ORDER = "order"
    PAYMENT = "payment"
    SUBSCRIPTION = "subscription"
    SUBSCRIPTION_NODE = "subscription_node"
    TARIFF = "tariff"
    SERVER = "server"
    BALANCE_TRANSACTION = "balance_transaction"
    SETTING = "setting"


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
