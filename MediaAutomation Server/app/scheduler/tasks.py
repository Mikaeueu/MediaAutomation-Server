"""Scheduler helpers and safe job management.

This version avoids starting the scheduler at import time. Use start_scheduler()
explicitly (e.g., in app startup) to initialize the singleton.
"""

from datetime import datetime
from typing import Callable, Any, Dict, List, Optional
import uuid
import threading
import platform
import shlex
import subprocess

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.job import Job

_scheduler_lock = threading.RLock()
_scheduler_instance: Optional[BackgroundScheduler] = None

_JOB_PREFIX_POLL = "poll-"
_JOB_PREFIX_ONESHOT = "oneshot-"
_JOB_PREFIX_SHUTDOWN = "shutdown-"


def start_scheduler() -> BackgroundScheduler:
    """Start and return the singleton BackgroundScheduler.

    Safe to call multiple times; returns existing instance if already started.
    """
    global _scheduler_instance
    with _scheduler_lock:
        if _scheduler_instance is None:
            _scheduler_instance = BackgroundScheduler()
            _scheduler_instance.start()
        return _scheduler_instance


def get_scheduler() -> BackgroundScheduler:
    """Return the running scheduler instance or raise if not started."""
    global _scheduler_instance
    with _scheduler_lock:
        if _scheduler_instance is None:
            raise RuntimeError("Scheduler not started. Call start_scheduler() first.")
        return _scheduler_instance


def _generate_job_id(prefix: str) -> str:
    """Generate a unique job id with a stable prefix."""
    return f"{prefix}{uuid.uuid4().hex}"


def schedule_polling(
    func: Callable[..., Any],
    seconds: int = 5,
    max_instances: int = 1,
    job_id: Optional[str] = None,
    args: Optional[List[Any]] = None,
    kwargs: Optional[Dict[str, Any]] = None,
) -> str:
    """Schedule a recurring polling job (idempotent if job_id provided)."""
    scheduler = start_scheduler()
    args = args or []
    kwargs = kwargs or {}
    job_id = job_id or _generate_job_id(_JOB_PREFIX_POLL)
    trigger = IntervalTrigger(seconds=seconds)
    scheduler.add_job(func, trigger=trigger, id=job_id, replace_existing=True, max_instances=max_instances, args=args, kwargs=kwargs)
    return job_id


def schedule_oneshot(
    run_time: datetime,
    func: Callable[..., Any],
    job_id: Optional[str] = None,
    args: Optional[List[Any]] = None,
    kwargs: Optional[Dict[str, Any]] = None,
) -> str:
    """Schedule a one-off job at a specific datetime."""
    scheduler = start_scheduler()
    args = args or []
    kwargs = kwargs or {}
    job_id = job_id or _generate_job_id(_JOB_PREFIX_ONESHOT)
    trigger = DateTrigger(run_date=run_time)
    scheduler.add_job(func, trigger=trigger, id=job_id, replace_existing=False, args=args, kwargs=kwargs)
    return job_id


def schedule_shutdown_job(scheduler: Optional[BackgroundScheduler], run_time: datetime, dry_run: bool = True) -> str:
    """Schedule a one-off shutdown job.

    Accepts an explicit scheduler for testability; if None, uses singleton.
    """
    sched = scheduler or start_scheduler()
    job_id = _generate_job_id(_JOB_PREFIX_SHUTDOWN)
    trigger = DateTrigger(run_date=run_time)
    sched.add_job(_execute_shutdown_job, trigger=trigger, id=job_id, replace_existing=False, args=[dry_run])
    return job_id


def _execute_shutdown_job(dry_run: bool = True) -> None:
    """Job function that executes the shutdown command for the host OS."""
    system = platform.system().lower()
    if dry_run:
        # Replace with proper logging in real app
        print(f"[scheduler] DRY RUN: would execute shutdown on {system}")
        return

    if system == "windows":
        cmd = "shutdown /s /t 0"
    elif system in ("linux", "darwin"):
        cmd = "shutdown -h now"
    else:
        print(f"[scheduler] Unsupported platform for shutdown: {system}")
        return

    args = shlex.split(cmd)
    try:
        subprocess.Popen(args, shell=False)
    except Exception as exc:
        print(f"[scheduler] Failed to execute shutdown command: {exc}")


def cancel_job(job_id: str) -> bool:
    """Cancel a scheduled job by id."""
    scheduler = start_scheduler()
    try:
        scheduler.remove_job(job_id)
        return True
    except Exception:
        return False


def list_jobs() -> List[Dict[str, Optional[str]]]:
    """Return a list of scheduled jobs with minimal metadata."""
    scheduler = start_scheduler()
    jobs: List[Job] = scheduler.get_jobs()
    result: List[Dict[str, Optional[str]]] = []
    for job in jobs:
        next_run = job.next_run_time.isoformat() if job.next_run_time else None
        result.append({"id": job.id, "next_run_time": next_run})
    return result
