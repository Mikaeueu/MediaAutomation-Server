"""Authentication routes using OAuth2 password flow.

Exposes /auth/login which returns a JWT access token for the default user
configured in config.json.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from app.auth.users import authenticate_user
from app.auth.jwt import create_access_token

router = APIRouter(tags=["auth"])


@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Authenticate user and return JWT access token.

    Uses the default in-memory user from config.json. Returns a bearer token
    that must be sent as Authorization: Bearer <token> to protected endpoints.

    Args:
        form_data: OAuth2PasswordRequestForm provided by FastAPI.

    Raises:
        HTTPException: 401 when credentials are invalid.

    Returns:
        dict: access_token and token_type.
    """
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token({"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}
