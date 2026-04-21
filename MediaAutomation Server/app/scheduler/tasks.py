"""Scheduler helpers and safe job management.

This module provides a singleton BackgroundScheduler instance and helper
functions to schedule polling jobs, one-off jobs (e.g., shutdown), list
and cancel jobs. It is designed to be safe for use across multiple modules
without creating duplicate schedulers or conflicting job ids.
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

# Internal singleton scheduler and lock to avoid race conditions
_scheduler_lock = threading.RLock()
_scheduler_instance: Optional[BackgroundScheduler] = None

# Prefixes for job ids to avoid collisions across the app
_JOB_PREFIX_POLL = "poll-"
_JOB_PREFIX_ONESHOT = "oneshot-"
_JOB_PREFIX_SHUTDOWN = "shutdown-"


def start_scheduler() -> BackgroundScheduler:
    """Start and return the singleton BackgroundScheduler.

    If the scheduler is already started, return the existing instance.

    Returns:
        BackgroundScheduler: started scheduler instance.
    """
    global _scheduler_instance
    with _scheduler_lock:
        if _scheduler_instance is None:
            _scheduler_instance = BackgroundScheduler()
            _scheduler_instance.start()
        return _scheduler_instance


def get_scheduler() -> BackgroundScheduler:
    """Return the running scheduler instance.

    Raises:
        RuntimeError: If the scheduler has not been started yet.

    Returns:
        BackgroundScheduler: the scheduler instance.
    """
    global _scheduler_instance
    with _scheduler_lock:
        if _scheduler_instance is None:
            raise RuntimeError("Scheduler not started. Call start_scheduler() first.")
        return _scheduler_instance


def _generate_job_id(prefix: str) -> str:
    """Generate a unique job id with a stable prefix.

    Args:
        prefix: Prefix string to categorize job ids.

    Returns:
        str: Unique job id.
    """
    return f"{prefix}{uuid.uuid4().hex}"


def schedule_polling(
    func: Callable[..., Any],
    seconds: int = 5,
    max_instances: int = 1,
    job_id: Optional[str] = None,
    args: Optional[List[Any]] = None,
    kwargs: Optional[Dict[str, Any]] = None,
) -> str:
    """Schedule a recurring polling job.

    If job_id is provided and a job with the same id exists, the job will be
    replaced to avoid duplicate polling jobs.

    Args:
        func: Callable to execute periodically.
        seconds: Interval in seconds between runs.
        max_instances: Maximum concurrent instances of the job.
        job_id: Optional explicit job id.
        args: Optional positional args for the callable.
        kwargs: Optional keyword args for the callable.

    Returns:
        str: The job id scheduled.
    """
    scheduler = start_scheduler()
    args = args or []
    kwargs = kwargs or {}
    job_id = job_id or _generate_job_id(_JOB_PREFIX_POLL)
    trigger = IntervalTrigger(seconds=seconds)
    # replace_existing ensures idempotency when re-scheduling same job_id
    scheduler.add_job(func, trigger=trigger, id=job_id, replace_existing=True, max_instances=max_instances, args=args, kwargs=kwargs)
    return job_id


def schedule_oneshot(
    run_time: datetime,
    func: Callable[..., Any],
    job_id: Optional[str] = None,
    args: Optional[List[Any]] = None,
    kwargs: Optional[Dict[str, Any]] = None,
) -> str:
    """Schedule a one-off job at a specific datetime.

    Args:
        run_time: Datetime (UTC) when the job should run.
        func: Callable to execute.
        job_id: Optional explicit job id.
        args: Optional positional args.
        kwargs: Optional keyword args.

    Returns:
        str: The job id scheduled.
    """
    scheduler = start_scheduler()
    args = args or []
    kwargs = kwargs or {}
    job_id = job_id or _generate_job_id(_JOB_PREFIX_ONESHOT)
    trigger = DateTrigger(run_date=run_time)
    scheduler.add_job(func, trigger=trigger, id=job_id, replace_existing=False, args=args, kwargs=kwargs)
    return job_id


def schedule_shutdown_job(scheduler: Optional[BackgroundScheduler], run_time: datetime, dry_run: bool = True) -> str:
    """Schedule a one-off shutdown job.

    This function is a convenience wrapper that schedules a job which will
    execute a platform-appropriate shutdown command. It accepts an explicit
