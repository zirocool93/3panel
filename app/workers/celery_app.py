from celery import Celery

from app.core.config import get_settings

settings = get_settings()
celery_app = Celery(
    "vpnbotx",
    broker=str(settings.redis_url),
    backend=str(settings.redis_url),
    include=["app.workers.tasks.system", "app.workers.tasks.commerce"],
)
celery_app.conf.timezone = "UTC"
celery_app.conf.beat_schedule = {
    "heartbeat-every-minute": {
        "task": "app.workers.tasks.system.heartbeat",
        "schedule": 60.0,
    }
}
