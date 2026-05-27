"""telegram bot settings

Revision ID: 20260527_0003
Revises: 20260527_0002
Create Date: 2026-05-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260527_0003"
down_revision: str | None = "20260527_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "app_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("telegram_bot_username", sa.String(length=64), nullable=True),
        sa.Column("telegram_bot_token_encrypted", sa.Text(), nullable=True),
        sa.Column("telegram_admin_id", sa.String(length=32), nullable=True),
        sa.Column("socks5_enabled", sa.Boolean(), nullable=False),
        sa.Column("socks5_host", sa.String(length=255), nullable=True),
        sa.Column("socks5_port", sa.Integer(), nullable=True),
        sa.Column("socks5_username_encrypted", sa.Text(), nullable=True),
        sa.Column("socks5_password_encrypted", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("app_settings")
