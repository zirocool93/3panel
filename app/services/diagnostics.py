from dataclasses import dataclass

import httpx
import redis.asyncio as redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.config import Settings


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    message: str
    fix: str | None = None


async def check_database(session_factory: async_sessionmaker) -> CheckResult:
    try:
        async with session_factory() as session:
            await session.execute(text("select 1"))
        return CheckResult("PostgreSQL", True, "Подключение к базе данных работает.")
    except Exception as exc:
        return CheckResult(
            "PostgreSQL",
            False,
            f"База данных недоступна: {exc}",
            "Проверьте DATABASE_URL и состояние контейнера postgres: docker compose ps postgres",
        )


async def check_redis(settings: Settings) -> CheckResult:
    client = redis.from_url(settings.redis_url, socket_connect_timeout=3, socket_timeout=3)
    try:
        await client.ping()
        return CheckResult("Redis", True, "Redis отвечает на PING.")
    except Exception as exc:
        return CheckResult(
            "Redis",
            False,
            f"Redis недоступен: {exc}",
            "Проверьте REDIS_URL и состояние контейнера redis: docker compose ps redis",
        )
    finally:
        await client.aclose()


async def check_backend_health(settings: Settings) -> CheckResult:
    url = f"http://127.0.0.1:{settings.api_port}/health"
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(url)
        if response.status_code == 200:
            return CheckResult("Backend API", True, f"Health endpoint отвечает: {url}")
        return CheckResult(
            "Backend API",
            False,
            f"Health endpoint вернул HTTP {response.status_code}: {url}",
            "Проверьте логи backend_api: docker compose logs --tail=100 backend_api",
        )
    except Exception as exc:
        return CheckResult(
            "Backend API",
            False,
            f"Health endpoint недоступен: {exc}",
            "Если команда запущена внутри backend_api, проверьте API_PORT. "
            "На хосте используйте docker compose ps и docker compose logs backend_api.",
        )
