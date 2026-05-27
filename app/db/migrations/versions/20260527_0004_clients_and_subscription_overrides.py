"""clients and subscription overrides

Revision ID: 20260527_0004
Revises: 20260527_0003
Create Date: 2026-05-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260527_0004"
down_revision: str | None = "20260527_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("display_name", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("comment", sa.Text(), nullable=True))
    op.alter_column("users", "telegram_id", existing_type=sa.BigInteger(), nullable=True)
    op.add_column(
        "vpn_subscriptions",
        sa.Column("payment_method", sa.String(length=64), nullable=True),
    )
    op.add_column("vpn_subscriptions", sa.Column("price_amount", sa.Numeric(14, 2), nullable=True))
    op.add_column("vpn_subscriptions", sa.Column("currency", sa.String(length=3), nullable=True))
    op.add_column("vpn_subscriptions", sa.Column("duration_days", sa.Integer(), nullable=True))
    op.add_column("vpn_subscriptions", sa.Column("device_limit", sa.Integer(), nullable=True))
    op.add_column(
        "vpn_subscriptions",
        sa.Column("admin_comment", sa.String(length=500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("vpn_subscriptions", "admin_comment")
    op.drop_column("vpn_subscriptions", "device_limit")
    op.drop_column("vpn_subscriptions", "duration_days")
    op.drop_column("vpn_subscriptions", "currency")
    op.drop_column("vpn_subscriptions", "price_amount")
    op.drop_column("vpn_subscriptions", "payment_method")
    op.alter_column("users", "telegram_id", existing_type=sa.BigInteger(), nullable=False)
    op.drop_column("users", "comment")
    op.drop_column("users", "display_name")
