import asyncio
from pathlib import Path

import typer
from alembic import command
from alembic.config import Config
from sqlalchemy import select

from app.core.enums import AdminRole
from app.core.security import hash_password
from app.db.models.admin import AdminUser
from app.db.session import async_session_factory

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


if __name__ == "__main__":
    app()
