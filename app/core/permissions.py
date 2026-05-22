from app.core.enums import AdminRole

ROLE_PERMISSIONS: dict[AdminRole, frozenset[str]] = {
    AdminRole.OWNER: frozenset({"*"}),
    AdminRole.ADMIN: frozenset(
        {
            "dashboard:read",
            "users:read",
            "users:write",
            "servers:read",
            "servers:write",
            "tariffs:read",
            "tariffs:write",
            "subscriptions:read",
            "subscriptions:write",
            "payments:read",
            "payments:write",
            "promo:read",
            "promo:write",
            "broadcasts:read",
            "broadcasts:write",
            "settings:read",
            "audit:read",
        }
    ),
    AdminRole.SUPPORT: frozenset(
        {"dashboard:read", "users:read", "subscriptions:read", "subscriptions:write"}
    ),
    AdminRole.ACCOUNTANT: frozenset({"dashboard:read", "payments:read", "payments:write"}),
    AdminRole.MARKETER: frozenset(
        {"dashboard:read", "promo:read", "promo:write", "broadcasts:read"}
    ),
}


def role_has_permission(role: AdminRole, permission: str) -> bool:
    permissions = ROLE_PERMISSIONS[role]
    return "*" in permissions or permission in permissions
