"""Simple file-based lock to coordinate processes.

This is a lightweight helper for local deployments to avoid concurrent
access to shared resources (e.g., writing the encrypted store).
It is not a replacement for robust inter-process locking libraries but
is sufficient for simple use-cases.
"""

from pathlib import Path
import time
from typing import Optional


class FileLock:
    """Context manager implementing a simple lock file."""

    def __init__(self, lock_path: str, timeout: float = 5.0, poll_interval: float = 0.1) -> None:
        """Initialize FileLock.

        Args:
            lock_path: Path to the lock file.
            timeout: Maximum seconds to wait for acquiring the lock.
            poll_interval: Seconds between attempts.
        """
        self.lock_path = Path(lock_path)
        self.timeout = timeout
        self.poll_interval = poll_interval
        self._acquired = False

    def acquire(self) -> bool:
        """Attempt to acquire the lock within timeout.

        Returns:
            True if lock acquired, False otherwise.
        """
        start = time.time()
        while True:
            try:
                # Use exclusive creation; fails if file exists
                fd = self.lock_path.open("x")
                fd.write(str(time.time()))
                fd.close()
                self._acquired = True
                return True
            except FileExistsError:
                if (time.time() - start) >= self.timeout:
                    return False
                time.sleep(self.poll_interval)

    def release(self) -> None:
        """Release the lock if held."""
        if self._acquired and self.lock_path.exists():
            try:
                self.lock_path.unlink()
            except Exception:
                pass
        self._acquired = False

    def __enter__(self):
        """Enter context and acquire lock or raise TimeoutError."""
        ok = self.acquire()
        if not ok:
            raise TimeoutError(f"Could not acquire lock {self.lock_path} within {self.timeout}s")
        return self

    def __exit__(self, exc_type, exc, tb):
        """Release lock on exit."""
        self.release()
