"""Pydantic schemas for authentication."""

from typing import Optional
from pydantic import BaseModel


class TokenData(BaseModel):
    """Payload extracted from JWT token for authorization checks."""
    sub: Optional[str] = None
    exp: Optional[int] = None


class User(BaseModel):
    """Public user model returned by APIs (no sensitive fields)."""
    username: str
    full_name: Optional[str] = None
    disabled: Optional[bool] = False


class UserInDB(User):
    """Internal user model that includes hashed password."""
    hashed_password: str
