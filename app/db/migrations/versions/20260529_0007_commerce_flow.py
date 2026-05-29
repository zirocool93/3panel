"""commerce order payment provisioning flow

Revision ID: 20260529_0007
Revises: 20260527_0006
Create Date: 2026-05-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260529_0007"
down_revision: str | None = "20260527_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("start_payload", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("source", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f("ix_users_source"), "users", ["source"], unique=False)

    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("tariff_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("currency", sa.String(length=16), nullable=False),
        sa.Column(
            "payment_method",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column("duration_days", sa.Integer(), nullable=False),
        sa.Column("traffic_limit_bytes", sa.BigInteger(), nullable=True),
        sa.Column("device_limit", sa.Integer(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fulfilled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["tariff_id"], ["tariffs.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_orders_expires_at"), "orders", ["expires_at"], unique=False)
    op.create_index(op.f("ix_orders_status"), "orders", ["status"], unique=False)
    op.create_index(op.f("ix_orders_tariff_id"), "orders", ["tariff_id"], unique=False)
    op.create_index(op.f("ix_orders_user_id"), "orders", ["user_id"], unique=False)
    op.add_column("vpn_subscriptions", sa.Column("order_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        op.f("fk_vpn_subscriptions_order_id_orders"),
        "vpn_subscriptions",
        "orders",
        ["order_id"],
        ["id"],
    )
    op.create_index(
        op.f("ix_vpn_subscriptions_order_id"),
        "vpn_subscriptions",
        ["order_id"],
        unique=False,
    )

    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("currency", sa.String(length=16), nullable=False),
        sa.Column("external_payment_id", sa.String(length=255), nullable=True),
        sa.Column("invoice_payload", sa.String(length=500), nullable=True),
        sa.Column("provider_payload", sa.JSON(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("refunded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_payments_external_payment_id"), "payments", ["external_payment_id"], unique=False
    )
    op.create_index(
        op.f("ix_payments_idempotency_key"), "payments", ["idempotency_key"], unique=True
    )
    op.create_index(
        op.f("ix_payments_invoice_payload"), "payments", ["invoice_payload"], unique=False
    )
    op.create_index(op.f("ix_payments_order_id"), "payments", ["order_id"], unique=False)
    op.create_index(op.f("ix_payments_provider"), "payments", ["provider"], unique=False)
    op.create_index(op.f("ix_payments_status"), "payments", ["status"], unique=False)
    op.create_index(op.f("ix_payments_user_id"), "payments", ["user_id"], unique=False)
    op.create_index(
        "uq_payments_provider_external_payment_id_not_empty",
        "payments",
        ["provider", "external_payment_id"],
        unique=True,
        postgresql_where=sa.text("external_payment_id IS NOT NULL AND external_payment_id != ''"),
        sqlite_where=sa.text("external_payment_id IS NOT NULL AND external_payment_id != ''"),
    )

    op.create_table(
        "payment_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("payment_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("external_event_id", sa.String(length=255), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["payment_id"], ["payments.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_payment_events_external_event_id"),
        "payment_events",
        ["external_event_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_payment_events_payment_id"), "payment_events", ["payment_id"], unique=False
    )
    op.create_index(
        op.f("ix_payment_events_provider"), "payment_events", ["provider"], unique=False
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("actor_type", sa.String(length=64), nullable=False),
        sa.Column("actor_id", sa.String(length=64), nullable=True),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.String(length=64), nullable=True),
        sa.Column("before", sa.JSON(), nullable=True),
        sa.Column("after", sa.JSON(), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_logs_action"), "audit_logs", ["action"], unique=False)
    op.create_index(op.f("ix_audit_logs_actor_id"), "audit_logs", ["actor_id"], unique=False)
    op.create_index(op.f("ix_audit_logs_actor_type"), "audit_logs", ["actor_type"], unique=False)
    op.create_index(op.f("ix_audit_logs_entity_id"), "audit_logs", ["entity_id"], unique=False)
    op.create_index(op.f("ix_audit_logs_entity_type"), "audit_logs", ["entity_type"], unique=False)


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("payment_events")
    op.drop_index("uq_payments_provider_external_payment_id_not_empty", table_name="payments")
    op.drop_table("payments")
    op.drop_index(op.f("ix_vpn_subscriptions_order_id"), table_name="vpn_subscriptions")
    op.drop_constraint(op.f("fk_vpn_subscriptions_order_id_orders"), "vpn_subscriptions")
    op.drop_column("vpn_subscriptions", "order_id")
    op.drop_table("orders")
    op.drop_index(op.f("ix_users_source"), table_name="users")
    op.drop_column("users", "last_seen_at")
    op.drop_column("users", "source")
    op.drop_column("users", "start_payload")
