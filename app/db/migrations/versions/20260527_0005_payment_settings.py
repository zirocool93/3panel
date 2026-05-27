"""payment provider settings

Revision ID: 20260527_0005
Revises: 20260527_0004
Create Date: 2026-05-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260527_0005"
down_revision: str | None = "20260527_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "app_settings",
        sa.Column(
            "manual_payments_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )
    op.add_column(
        "app_settings",
        sa.Column("manual_payment_instructions", sa.Text(), nullable=True),
    )
    op.add_column(
        "app_settings",
        sa.Column(
            "telegram_stars_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column("app_settings", sa.Column("telegram_stars_rate_rub", sa.Integer(), nullable=True))
    op.add_column(
        "app_settings",
        sa.Column("telegram_stars_invoice_title", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "app_settings",
        sa.Column("telegram_stars_invoice_description", sa.Text(), nullable=True),
    )
    op.add_column(
        "app_settings",
        sa.Column("cardlink_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "app_settings",
        sa.Column(
            "cardlink_api_base_url",
            sa.String(length=255),
            nullable=True,
            server_default="https://cardlink.link",
        ),
    )
    op.add_column(
        "app_settings",
        sa.Column("cardlink_shop_id", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "app_settings",
        sa.Column("cardlink_api_token_encrypted", sa.Text(), nullable=True),
    )
    op.add_column(
        "app_settings",
        sa.Column("cardlink_currency", sa.String(length=3), nullable=True, server_default="RUB"),
    )
    op.add_column(
        "app_settings",
        sa.Column("cardlink_locale", sa.String(length=8), nullable=True, server_default="ru"),
    )
    op.add_column(
        "app_settings",
        sa.Column(
            "cardlink_payer_pays_commission",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )
    op.add_column("app_settings", sa.Column("cardlink_success_url", sa.Text(), nullable=True))
    op.add_column("app_settings", sa.Column("cardlink_fail_url", sa.Text(), nullable=True))
    op.add_column(
        "app_settings",
        sa.Column("yookassa_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "app_settings",
        sa.Column("yookassa_shop_id", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "app_settings",
        sa.Column("yookassa_secret_key_encrypted", sa.Text(), nullable=True),
    )
    op.add_column("app_settings", sa.Column("yookassa_return_url", sa.Text(), nullable=True))
    op.add_column(
        "app_settings",
        sa.Column("yookassa_currency", sa.String(length=3), nullable=True, server_default="RUB"),
    )

    for column_name in (
        "manual_payments_enabled",
        "telegram_stars_enabled",
        "cardlink_enabled",
        "cardlink_api_base_url",
        "cardlink_currency",
        "cardlink_locale",
        "cardlink_payer_pays_commission",
        "yookassa_enabled",
        "yookassa_currency",
    ):
        op.alter_column("app_settings", column_name, server_default=None)


def downgrade() -> None:
    op.drop_column("app_settings", "yookassa_currency")
    op.drop_column("app_settings", "yookassa_return_url")
    op.drop_column("app_settings", "yookassa_secret_key_encrypted")
    op.drop_column("app_settings", "yookassa_shop_id")
    op.drop_column("app_settings", "yookassa_enabled")
    op.drop_column("app_settings", "cardlink_fail_url")
    op.drop_column("app_settings", "cardlink_success_url")
    op.drop_column("app_settings", "cardlink_payer_pays_commission")
    op.drop_column("app_settings", "cardlink_locale")
    op.drop_column("app_settings", "cardlink_currency")
    op.drop_column("app_settings", "cardlink_api_token_encrypted")
    op.drop_column("app_settings", "cardlink_shop_id")
    op.drop_column("app_settings", "cardlink_api_base_url")
    op.drop_column("app_settings", "cardlink_enabled")
    op.drop_column("app_settings", "telegram_stars_invoice_description")
    op.drop_column("app_settings", "telegram_stars_invoice_title")
    op.drop_column("app_settings", "telegram_stars_rate_rub")
    op.drop_column("app_settings", "telegram_stars_enabled")
    op.drop_column("app_settings", "manual_payment_instructions")
    op.drop_column("app_settings", "manual_payments_enabled")
