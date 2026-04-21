"""JWT utilities and FastAPI dependency to protect routes."""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.config import get_config
from .schemas import TokenData, User
from .users import get_user

# OAuth2 scheme expects tokenUrl to match the login route
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# Load secret and algorithm from config
_cfg = get_config()
SECRET_KEY = _cfg.get("auth", {}).get("jwt_secret", "troque_esta_chave_segura")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours by default


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token.

    Args:
        data: Payload data to include in token (e.g., {"sub": username}).
        expires_delta: Optional timedelta for token expiry.

    Returns:
        Encoded JWT string.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return token


def decode_access_token(token: str) -> TokenData:
    """Decode and validate a JWT token.

    Args:
        token: Encoded JWT string.

    Returns:
        TokenData with payload fields.

    Raises:
        HTTPException: If token is invalid or expired.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: Optional[str] = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing subject",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return TokenData(sub=username, exp=payload.get("exp"))
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """FastAPI dependency that returns the current authenticated user.

    Args:
        token: JWT token provided by OAuth2PasswordBearer.

    Returns:
        User model for the authenticated user.

    Raises:
        HTTPException: If token is invalid or user not found.
    """
    token_data = decode_access_token(token)
    user = get_user(token_data.sub) if token_data.sub else None
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return User(username=user.username, full_name=user.full_name, disabled=user.disabled)


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Dependency that ensures the current user is active (not disabled).

    Args:
        current_user: User resolved by get_current_user.

    Returns:
        The same User if active.

    Raises:
        HTTPException: If user is disabled.
    """
    if current_user.disabled:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is disabled")
    return current_user
