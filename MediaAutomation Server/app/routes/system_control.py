"""System control routes: agendamento de desligamento e abrir programas (Windows)."""

from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.scheduler.tasks import start_scheduler, schedule_shutdown_job, cancel_shutdown_job
from app.config import get_config
from app.auth.jwt import get_current_active_user
from app.auth.schemas import User

router = APIRouter(tags=["system"])
_scheduler = start_scheduler()


class ShutdownSchedulePayload(BaseModel):
    """Payload to schedule shutdown.

    Provide either 'at' (ISO datetime string) or 'delay_seconds' (int).
    """
    at: Optional[datetime] = None
    delay_seconds: Optional[int] = None


class CancelPayload(BaseModel):
    """Payload to cancel a scheduled job."""
    job_id: str


class OpenProgramPayload(BaseModel):
    """Payload to request opening a whitelisted program."""
    program_id: str


@router.post("/shutdown/schedule")
def schedule_shutdown(payload: ShutdownSchedulePayload, current_user: User = Depends(get_current_active_user)):
    """Schedule a system shutdown on Windows 10.

    The endpoint requires authentication. For safety, when running in development
    set 'system.dry_run' in config to True to avoid actual shutdown.

    Args:
        payload: ShutdownSchedulePayload with 'at' or 'delay_seconds'.
        current_user: Authenticated user (injected).

    Returns:
        dict: status, job_id and run_time.
    """
    cfg = get_config()
    dry_run = cfg.get("system", {}).get("dry_run", True)

    if payload.at is None and payload.delay_seconds is None:
        raise HTTPException(status_code=400, detail="Provide 'at' or 'delay_seconds'")

    if payload.at:
        run_time = payload.at
    else:
        run_time = datetime.utcnow() + timedelta(seconds=payload.delay_seconds)

    job_id = schedule_shutdown_job(_scheduler, run_time, dry_run=dry_run)
    return {"status": "scheduled", "job_id": job_id, "run_time": run_time.isoformat()}


@router.post("/shutdown/cancel")
def cancel_shutdown(payload: CancelPayload, current_user: User = Depends(get_current_active_user)):
    """Cancel a scheduled shutdown job.

    Args:
        payload: CancelPayload with job_id.
        current_user: Authenticated user (injected).

    Returns:
        dict: cancellation status.
    """
    cancelled = cancel_shutdown_job(_scheduler, payload.job_id)
    if not cancelled:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"status": "cancelled", "job_id": payload.job_id}


@router.post("/open")
def open_program(payload: OpenProgramPayload, current_user: User = Depends(get_current_active_user)):
    """Open a whitelisted program by id (Windows only).

    The config.json must contain a 'system.program_whitelist' mapping of id -> path.

    Args:
        payload: OpenProgramPayload with program_id.
        current_user: Authenticated user (injected).

    Returns:
        dict: launch status.
    """
    cfg = get_config()
    whitelist = cfg.get("system", {}).get("program_whitelist", {})
    program_path = whitelist.get(payload.program_id)
    if not program_path:
        raise HTTPException(status_code=400, detail="Program not allowed")

    # Launch is delegated to scheduler/tasks or subprocess; here we simply return success
    # to keep route logic simple and testable. The actual launch should be performed
    # by a trusted component with proper validation.
    try:
        # Import locally to avoid top-level platform-specific imports in tests
        import subprocess
        subprocess.Popen([program_path], shell=False)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return {"status": "launched", "program_id": payload.program_id}


@router.get("/shutdown/jobs")
def list_jobs(current_user: User = Depends(get_current_active_user)):
    """Return a list of scheduled shutdown job ids.

    Args:
        current_user: Authenticated user (injected).

    Returns:
        dict: job ids list.
    """
    jobs = _scheduler.get_jobs()
    job_list = [{"id": j.id, "next_run_time": j.next_run_time.isoformat() if j.next_run_time else None} for j in jobs]
    return {"jobs": job_list}
