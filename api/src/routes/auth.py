from fastapi import APIRouter, Depends, HTTPException, status

from src.models.user import AppLoginRequest, AppLoginResponse
from src.services.auth_service import (
    authenticate_app_user,
    create_access_token,
    require_auth,
)

router = APIRouter()


@router.post("/login", response_model=AppLoginResponse)
def login(credentials: AppLoginRequest) -> AppLoginResponse:
    """Login with the configured application credentials."""
    if not authenticate_app_user(credentials.username, credentials.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    return AppLoginResponse(
        access_token=create_access_token(),
        username=credentials.username,
    )


@router.get("/session")
def session(_: None = Depends(require_auth)) -> dict[str, bool]:
    """Validate the current bearer token."""
    return {"authenticated": True}
