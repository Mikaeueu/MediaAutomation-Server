"""User management helpers: hashing, verification and simple store.

This module provides a minimal user store suitable for local deployments.
Replace or extend with a persistent store (database) for production.
"""

from typing import Optional, Dict
from passlib.context import CryptContext
from app.config import get_config
from .schemas import UserInDB, User

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# In-memory user store: username -> UserInDB
_user_store: Dict[str, UserInDB] = {}


def _hash_password(password: str) -> str:
    """Hash a plaintext password using passlib bcrypt.

    Args:
        password: Plaintext password.

    Returns:
        Hashed password string.
    """
    return _pwd_context.hash(password)


def _verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a hashed password.

    Args:
        plain_password: Plaintext password to verify.
        hashed_password: Stored hashed password.

    Returns:
        True if match, False otherwise.
    """
    return _pwd_context.verify(plain_password, hashed_password)


def _ensure_default_user() -> None:
    """Ensure default user from config exists in the in-memory store.

    This is convenient for initial local deployments. In production, remove
    or replace with proper user provisioning.
    """
    cfg = get_config()
    auth_cfg = cfg.get("auth", {})
    default_user = auth_cfg.get("default_user")
    default_password = auth_cfg.get("default_password")
    if default_user and default_password and default_user not in _user_store:
        hashed = _hash_password(default_password)
        _user_store[default_user] = UserInDB(
            username=default_user,
            full_name=None,
            disabled=False,
            hashed_password=hashed,
        )


def get_user(username: str) -> Optional[UserInDB]:
    """Retrieve a user from the in-memory store.

    Args:
        username: Username to lookup.

    Returns:
        UserInDB instance or None if not found.
    """
    _ensure_default_user()
    return _user_store.get(username)


def authenticate_user(username: str, password: str) -> Optional[User]:
    """Authenticate a user by username and password.

    Args:
        username: Username provided.
        password: Plaintext password provided.

    Returns:
        Public User model on success, otherwise None.
    """
    user = get_user(username)
    if not user:
        return None
    if not _verify_password(password, user.hashed_password):
        return None
    return User(username=user.username, full_name=user.full_name, disabled=user.disabled)


def create_user(username: str, password: str, full_name: Optional[str] = None) -> UserInDB:
    """Create a new user in the in-memory store.

    Args:
        username: Username for the new user.
        password: Plaintext password (will be hashed).
        full_name: Optional full name.

    Returns:
        The created UserInDB object.

    Raises:
        ValueError: If user already exists.
    """
    if get_user(username):
        raise ValueError("User already exists")
    hashed = _hash_password(password)
    user = UserInDB(username=username, full_name=full_name, disabled=False, hashed_password=hashed)
    _user_store[username] = user
    return user
