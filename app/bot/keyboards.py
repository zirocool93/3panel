from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🌐 Мой VPN", callback_data="vpn:show")],
            [InlineKeyboardButton(text="💳 Купить / продлить", callback_data="catalog:list")],
            [InlineKeyboardButton(text="🎁 Пробный период", callback_data="trial:activate")],
            [InlineKeyboardButton(text="📲 Инструкции", callback_data="guides:list")],
            [InlineKeyboardButton(text="👥 Пригласить друга", callback_data="ref:show")],
            [InlineKeyboardButton(text="🎟 Промокод", callback_data="promo:show")],
            [InlineKeyboardButton(text="🆘 Поддержка", callback_data="support:start")],
        ]
    )


def back_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:main")]]
    )


def catalog_actions(tariff_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Купить за Telegram Stars",
                    callback_data=f"pay:stars:{tariff_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="Ручная оплата",
                    callback_data=f"pay:manual:{tariff_id}",
                )
            ],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:main")],
        ]
    )


def after_payment_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🌐 Мой VPN", callback_data="vpn:show")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:main")],
        ]
    )


def empty_vpn_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Купить VPN", callback_data="catalog:list")],
            [InlineKeyboardButton(text="Пробный период", callback_data="trial:activate")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:main")],
        ]
    )


def subscription_menu(subscription_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Показать ссылку",
                    callback_data=f"sub:link:{subscription_id}",
                )
            ],
            [InlineKeyboardButton(text="QR-код", callback_data=f"sub:qr:{subscription_id}")],
            [InlineKeyboardButton(text="Инструкция", callback_data="guides:list")],
            [InlineKeyboardButton(text="Продлить", callback_data="catalog:list")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:main")],
        ]
    )


def guides_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="iPhone / iPad", callback_data="guide:ios")],
            [InlineKeyboardButton(text="Android", callback_data="guide:android")],
            [InlineKeyboardButton(text="Windows", callback_data="guide:windows")],
            [InlineKeyboardButton(text="macOS", callback_data="guide:macos")],
            [InlineKeyboardButton(text="Android TV", callback_data="guide:tv")],
            [InlineKeyboardButton(text="Роутер", callback_data="guide:router")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:main")],
        ]
    )


def support_categories() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Не подключается", callback_data="support:cat:connect")],
            [InlineKeyboardButton(text="Низкая скорость", callback_data="support:cat:speed")],
            [
                InlineKeyboardButton(
                    text="Оплатил, но доступ не пришёл",
                    callback_data="support:cat:pay",
                )
            ],
            [InlineKeyboardButton(text="Нужна инструкция", callback_data="support:cat:guide")],
            [InlineKeyboardButton(text="Другое", callback_data="support:cat:other")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:main")],
        ]
    )
