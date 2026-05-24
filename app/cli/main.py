import asyncio
from pathlib import Path

import typer
from alembic import command
from alembic.config import Config
from sqlalchemy import select

from app.core.config import get_settings
from app.core.enums import AdminRole
from app.core.security import hash_password
from app.db.models.admin import AdminUser
from app.db.session import async_session_factory
from app.services.diagnostics import CheckResult, check_backend_health, check_database, check_redis

app = typer.Typer(no_args_is_help=True)


@app.command("migrate")
def migrate() -> None:
    """Apply all Alembic migrations."""
    command.upgrade(Config("alembic.ini"), "head")


@app.command("create-admin")
def create_admin(
    email: str = typer.Option(..., prompt=True),
    password: str = typer.Option(
        ...,
        envvar="VPNBOTX_ADMIN_PASSWORD",
        prompt=True,
        hide_input=True,
        confirmation_prompt=True,
    ),
    role: AdminRole = typer.Option(AdminRole.OWNER),
) -> None:
    """Create the first web-admin account."""
    asyncio.run(_create_admin(email=email.lower(), password=password, role=role))


@app.command("list-admins")
def list_admins() -> None:
    """List web-admin accounts."""
    asyncio.run(_list_admins())


@app.command("set-admin-password")
def set_admin_password(
    email: str = typer.Option(..., prompt=True),
    password: str = typer.Option(
        ...,
        envvar="VPNBOTX_ADMIN_PASSWORD",
        prompt=True,
        hide_input=True,
        confirmation_prompt=True,
    ),
) -> None:
    """Reset a web-admin password."""
    asyncio.run(_set_admin_password(email=email.lower(), password=password))


@app.command("check-db")
def check_db() -> None:
    """Check database connectivity."""
    result = asyncio.run(check_database(async_session_factory))
    _print_check(result)
    raise typer.Exit(code=0 if result.ok else 1)


@app.command("check-redis")
def check_redis_command() -> None:
    """Check Redis connectivity."""
    result = asyncio.run(check_redis(get_settings()))
    _print_check(result)
    raise typer.Exit(code=0 if result.ok else 1)


@app.command("doctor")
def doctor() -> None:
    """Run deployment diagnostics and print actionable fixes."""
    results = asyncio.run(_doctor())
    for result in results:
        _print_check(result)
    raise typer.Exit(code=0 if all(result.ok for result in results) else 1)


@app.command("seed-demo-data")
def seed_demo_data() -> None:
    """Reserved entrypoint for local demo data in later stages."""
    typer.echo("Demo seed data will be added with tariffs and payment flows.")


@app.command("check-xui-server")
def check_xui_server(panel_url: str) -> None:
    """Stage-1 connectivity placeholder for the future 3X-UI provider."""
    typer.echo(f"3X-UI connectivity checks arrive in Stage 2: {panel_url}")


@app.command("backup-db")
def backup_db() -> None:
    """Show the supported container backup command."""
    typer.echo("Run scripts/backup_db.sh on the deployment host.")


@app.command("restore-db")
def restore_db(path: Path) -> None:
    """Show the supported container restore command."""
    typer.echo(f"Run scripts/restore_db.sh {path} on the deployment host.")


async def _create_admin(*, email: str, password: str, role: AdminRole) -> None:
    if len(password) < 8:
        raise typer.BadParameter("Admin password must contain at least 8 characters.")
    async with async_session_factory() as session:
        result = await session.execute(select(AdminUser).where(AdminUser.email == email))
        if result.scalar_one_or_none():
            raise typer.BadParameter("An admin with this email already exists.")
        session.add(AdminUser(email=email, password_hash=hash_password(password), role=role))
        await session.commit()
    typer.echo(f"Created {role.value} admin {email}.")


async def _list_admins() -> None:
    async with async_session_factory() as session:
        result = await session.execute(select(AdminUser).order_by(AdminUser.id))
        admins = result.scalars().all()

    if not admins:
        typer.echo("No admin users found.")
        return

    for admin in admins:
        status = "active" if admin.is_active else "inactive"
        typer.echo(f"{admin.id}\t{admin.email}\t{admin.role.value}\t{status}")


async def _set_admin_password(*, email: str, password: str) -> None:
    if len(password) < 8:
        raise typer.BadParameter("Admin password must contain at least 8 characters.")
    async with async_session_factory() as session:
        result = await session.execute(select(AdminUser).where(AdminUser.email == email))
        admin = result.scalar_one_or_none()
        if not admin:
            raise typer.BadParameter("Admin with this email does not exist.")
        admin.password_hash = hash_password(password)
        await session.commit()
    typer.echo(f"Password updated for {email}.")


async def _doctor() -> list[CheckResult]:
    settings = get_settings()
    return [
        await check_database(async_session_factory),
        await check_redis(settings),
        await check_backend_health(settings),
    ]


def _print_check(result: CheckResult) -> None:
    marker = "OK" if result.ok else "FAIL"
    typer.echo(f"[{marker}] {result.name}: {result.message}")
    if result.fix:
        typer.echo(f"      Что сделать: {result.fix}")


if __name__ == "__main__":
    app()
