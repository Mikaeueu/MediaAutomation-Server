"""Simple encrypted key/value store using Fernet.

This is a convenience helper for local development. For production, use OS
secret stores or a dedicated secrets manager.
"""

import json
from typing import Optional
from pathlib import Path
from cryptography.fernet import Fernet, InvalidToken


class SecureStore:
    """Encrypted JSON key/value store."""

    def __init__(self, path: str, key_path: Optional[str] = None) -> None:
        """Initialize SecureStore.

        Args:
            path: Path to encrypted file.
            key_path: Optional path to store the encryption key (if not provided,
                      a key is derived from environment or generated).
        """
        self.path = Path(path)
        self.key_path = Path(key_path) if key_path else self.path.with_suffix(".key")
        self._ensure_key()
        self._fernet = Fernet(self._read_key())

    def _ensure_key(self) -> None:
        """Create key file if missing."""
        if not self.key_path.exists():
            key = Fernet.generate_key()
            self.key_path.write_bytes(key)

    def _read_key(self) -> bytes:
        """Read encryption key from key file."""
        return self.key_path.read_bytes()

    def _read_store(self) -> dict:
        """Read and decrypt store; return empty dict if missing or invalid."""
        if not self.path.exists():
            return {}
        try:
            token = self.path.read_bytes()
            data = self._fernet.decrypt(token)
            return json.loads(data.decode("utf-8"))
        except (InvalidToken, Exception):
            return {}

    def _write_store(self, data: dict) -> None:
        """Encrypt and write store to disk."""
        raw = json.dumps(data).encode("utf-8")
        token = self._fernet.encrypt(raw)
        self.path.write_bytes(token)

    def get(self, key: str) -> Optional[str]:
        """Get value for key or None."""
        data = self._read_store()
        return data.get(key)

    def set(self, key: str, value: str) -> None:
        """Set value for key and persist."""
        data = self._read_store()
        data[key] = value
        self._write_store(data)
