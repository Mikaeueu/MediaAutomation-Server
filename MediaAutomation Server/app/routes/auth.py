"""Authentication routes."""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.auth.users import authenticate_user
from app.auth.jwt import create_access_token

router = APIRouter()


class LoginRequest(BaseModel):
    """Login payload."""
    username: str
    password: str


class LoginResponse(BaseModel):
    """Login response payload."""
    access_token: str
    token_type: str = "bearer"


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest):
    """Authenticate user and return JWT token.

    Args:
        payload: LoginRequest with username and password.

    Raises:
        HTTPException: If authentication fails.

    Returns:
        LoginResponse with access token.
    """
    user = authenticate_user(payload.username, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": user["username"]})
    return LoginResponse(access_token=token)
