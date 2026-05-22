import structlog

from app.workers.celery_app import celery_app

logger = structlog.get_logger(__name__)


@celery_app.task(name="app.workers.tasks.system.heartbeat")
def heartbeat() -> str:
    logger.info("worker_heartbeat")
    return "ok"
