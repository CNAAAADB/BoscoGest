"""In-process daily scheduler for fee maintenance (REQ-FEE-03).

Runs inside the FastAPI process (single uvicorn worker per start.sh) so the
maintenance executes with full access to the ORM and the WebSocket
notification manager. APScheduler's AsyncIOExecutor runs this sync job in a
threadpool, so it never blocks the event loop; `notification_manager.enqueue`
is thread-safe (uses loop.call_soon_threadsafe).
"""
import logging
import os
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.database import SyncSessionLocal

logger = logging.getLogger(__name__)

_scheduler: Optional[AsyncIOScheduler] = None


def run_fee_maintenance_job() -> None:
    from app.services.fee_service import FeeService  # local import avoids cycles

    db = SyncSessionLocal()
    try:
        run = FeeService(db).run_maintenance(trigger="scheduled")
        logger.info(
            "Fee maintenance run #%s: overdue=%s reminded=%s renewed=%s status=%s",
            run.id, run.overdue_count, run.reminded_count, run.renewed_count, run.status,
        )
    except Exception:  # noqa: BLE001
        logger.exception("Fee maintenance job failed")
    finally:
        db.close()


def start_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        return
    hour = int(os.getenv("FEE_MAINTENANCE_HOUR", "3"))
    minute = int(os.getenv("FEE_MAINTENANCE_MINUTE", "0"))
    tz = os.getenv("SCHEDULER_TZ", "Europe/Madrid")
    _scheduler = AsyncIOScheduler(timezone=tz)
    _scheduler.add_job(
        run_fee_maintenance_job,
        CronTrigger(hour=hour, minute=minute),
        id="fee_maintenance",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    _scheduler.start()
    logger.info("Fee maintenance scheduler started (daily at %02d:%02d %s)", hour, minute, tz)


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
