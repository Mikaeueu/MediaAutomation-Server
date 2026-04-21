"""Helpers to register/unregister autostart on Windows.

This module provides two pragmatic approaches:
- Register a scheduled task via schtasks.exe (recommended for services that
  need to run with specific privileges).
- Optionally, write a registry Run key (simpler but less flexible).

Both functions are implemented to be explicit and safe; they do not run
with elevated privileges automatically — the caller must ensure permissions.
"""

import subprocess
import shlex
import platform
from typing import Tuple, Optional


def _ensure_windows() -> None:
    """Raise RuntimeError if not running on Windows."""
    if platform.system().lower() != "windows":
        raise RuntimeError("Windows autostart helpers are only supported on Windows")


def register_autostart_task(task_name: str, exe_path: str, arguments: str = "", run_as_admin: bool = False) -> Tuple[bool, str]:
    """Register a scheduled task that runs at user logon.

    Args:
        task_name: Name for the scheduled task.
        exe_path: Full path to executable to run.
        arguments: Optional command-line arguments.
        run_as_admin: If True, attempt to register task to run with highest privileges.

    Returns:
        Tuple[success(bool), message(str)].
    """
    _ensure_windows()
    # Build schtasks command
    # /RL HIGHEST requires admin to create; default is LIMITED
    run_level = "/RL HIGHEST" if run_as_admin else ""
    cmd = (
        f'schtasks /Create /SC ONLOGON /TN "{task_name}" /TR "{exe_path} {arguments}" '
        f'/F {run_level}'
    )
    try:
        subprocess.check_output(shlex.split(cmd), stderr=subprocess.STDOUT, shell=False)
        return True, "Task created"
    except subprocess.CalledProcessError as exc:
        return False, exc.output.decode("utf-8", errors="ignore")


def unregister_autostart_task(task_name: str) -> Tuple[bool, str]:
    """Remove a scheduled task by name.

    Args:
        task_name: Name of the scheduled task.

    Returns:
        Tuple[success(bool), message(str)].
    """
    _ensure_windows()
    cmd = f'schtasks /Delete /TN "{task_name}" /F'
    try:
        subprocess.check_output(shlex.split(cmd), stderr=subprocess.STDOUT, shell=False)
        return True, "Task deleted"
    except subprocess.CalledProcessError as exc:
        return False, exc.output.decode("utf-8", errors="ignore")
