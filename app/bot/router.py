from aiogram import Router

from app.bot.handlers import admin, catalog, menu, payments, start, subscriptions, support, trial


def build_router() -> Router:
    router = Router(name="bot")
    router.include_router(start.router)
    router.include_router(menu.router)
    router.include_router(catalog.router)
    router.include_router(payments.router)
    router.include_router(subscriptions.router)
    router.include_router(trial.router)
    router.include_router(support.router)
    router.include_router(admin.router)
    return router
