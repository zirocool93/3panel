"""tariff visibility and inbound links

Revision ID: 20260527_0002
Revises: 20260523_0001
Create Date: 2026-05-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260527_0002"
down_revision: str | None = "20260523_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "tariffs",
        sa.Column("is_visible", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.alter_column("tariffs", "is_visible", server_default=None)
    op.create_table(
        "tariff_inbounds",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tariff_id", sa.Integer(), nullable=False),
        sa.Column("server_id", sa.Integer(), nullable=False),
        sa.Column("inbound_id", sa.String(length=128), nullable=False),
        sa.Column("inbound_remark", sa.String(length=255), nullable=True),
        sa.Column("protocol", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(["server_id"], ["servers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tariff_id"], ["tariffs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tariff_id", "server_id", "inbound_id"),
    )


def downgrade() -> None:
    op.drop_table("tariff_inbounds")
    op.drop_column("tariffs", "is_visible")
