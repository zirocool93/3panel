"""tariff prices and balance ledger

Revision ID: 20260527_0006
Revises: 20260527_0005
Create Date: 2026-05-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260527_0006"
down_revision: str | None = "20260527_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tariff_prices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tariff_id", sa.Integer(), nullable=False),
        sa.Column("payment_method", sa.String(length=64), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("currency", sa.String(length=16), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tariff_id"], ["tariffs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tariff_id", "payment_method"),
    )
    op.create_table(
        "balance_transactions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("admin_id", sa.Integer(), nullable=True),
        sa.Column("subscription_id", sa.Integer(), nullable=True),
        sa.Column("type", sa.String(length=64), nullable=False),
        sa.Column("payment_method", sa.String(length=64), nullable=True),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("currency", sa.String(length=16), nullable=False),
        sa.Column("balance_before", sa.Numeric(14, 2), nullable=False),
        sa.Column("balance_after", sa.Numeric(14, 2), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("external_id", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["admin_id"], ["admin_users.id"]),
        sa.ForeignKeyConstraint(["subscription_id"], ["vpn_subscriptions.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_balance_transactions_user_id"),
        "balance_transactions",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_balance_transactions_external_id"),
        "balance_transactions",
        ["external_id"],
        unique=False,
    )
    op.execute(
        """
        INSERT INTO tariff_prices (
            tariff_id,
            payment_method,
            amount,
            currency,
            enabled,
            created_at,
            updated_at
        )
        SELECT id, 'manual', price, currency, true, created_at, updated_at
        FROM tariffs
        """
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_balance_transactions_external_id"), table_name="balance_transactions")
    op.drop_index(op.f("ix_balance_transactions_user_id"), table_name="balance_transactions")
    op.drop_table("balance_transactions")
    op.drop_table("tariff_prices")
