import base64
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from hmac import compare_digest

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.config import settings

TOKEN_SUBJECT = "app-user"
TOKEN_EXPIRES_SECONDS = 60 * 60 * 12

bearer_scheme = HTTPBearer(auto_error=False)


def _auth_configured() -> bool:
    return bool(settings.app_login_username and settings.app_login_password)


def authenticate_app_user(username: str, password: str) -> bool:
    if not _auth_configured():
        return False
    return compare_digest(username, settings.app_login_username) and compare_digest(
        password,
        settings.app_login_password,
    )


def create_access_token() -> str:
    expires = datetime.now(timezone.utc) + timedelta(seconds=TOKEN_EXPIRES_SECONDS)
    payload = {
        "sub": TOKEN_SUBJECT,
        "exp": int(expires.timestamp()),
    }
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    payload_part = base64.urlsafe_b64encode(payload_bytes).decode("ascii").rstrip("=")
    signature = hmac.new(
        settings.api_secret_key.encode("utf-8"),
        payload_part.encode("ascii"),
        hashlib.sha256,
    ).digest()
    signature_part = base64.urlsafe_b64encode(signature).decode("ascii").rstrip("=")
    return f"{payload_part}.{signature_part}"


def _decode_access_token(token: str) -> dict:
    try:
        payload_part, signature_part = token.split(".", 1)
    except ValueError:
        raise ValueError("Malformed token")

    expected_signature = hmac.new(
        settings.api_secret_key.encode("utf-8"),
        payload_part.encode("ascii"),
        hashlib.sha256,
    ).digest()
    expected_part = base64.urlsafe_b64encode(expected_signature).decode("ascii").rstrip("=")
    if not compare_digest(signature_part, expected_part):
        raise ValueError("Bad token signature")

    padding = "=" * (-len(payload_part) % 4)
    payload_bytes = base64.urlsafe_b64decode(f"{payload_part}{padding}")
    payload = json.loads(payload_bytes.decode("utf-8"))
    if int(payload.get("exp", 0)) < int(datetime.now(timezone.utc).timestamp()):
        raise ValueError("Expired token")
    return payload


def require_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> None:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    try:
        payload = _decode_access_token(credentials.credentials)
    except (ValueError, json.JSONDecodeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        )

    if payload.get("sub") != TOKEN_SUBJECT:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        )
