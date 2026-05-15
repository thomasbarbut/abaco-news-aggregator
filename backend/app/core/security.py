from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.core.config import settings

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
ALGORITHM = settings.JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS

# FastAPI dependency that extracts the Bearer token from the Authorization header
_bearer_scheme = HTTPBearer(auto_error=True)

# ---------------------------------------------------------------------------
# Token creation
# ---------------------------------------------------------------------------


def _build_claims(
    subject: str | UUID,
    token_type: str,
    extra: dict[str, Any] | None,
    expires_delta: timedelta,
) -> dict[str, Any]:
    now = datetime.now(tz=timezone.utc)
    claims: dict[str, Any] = {
        "sub": str(subject),
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    if extra:
        claims.update(extra)
    return claims


def create_access_token(
    subject: str | UUID,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Return a signed JWT access token valid for ACCESS_TOKEN_EXPIRE_MINUTES."""
    claims = _build_claims(
        subject=subject,
        token_type="access",
        extra=extra_claims,
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return jwt.encode(claims, settings.JWT_SECRET, algorithm=ALGORITHM)


def create_refresh_token(
    subject: str | UUID,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Return a signed JWT refresh token valid for REFRESH_TOKEN_EXPIRE_DAYS."""
    claims = _build_claims(
        subject=subject,
        token_type="refresh",
        extra=extra_claims,
        expires_delta=timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    )
    return jwt.encode(claims, settings.JWT_SECRET, algorithm=ALGORITHM)


def create_token_pair(
    subject: str | UUID,
    extra_claims: dict[str, Any] | None = None,
) -> tuple[str, str]:
    """Return (access_token, refresh_token) for a given subject."""
    access = create_access_token(subject, extra_claims)
    refresh = create_refresh_token(subject, extra_claims)
    return access, refresh


# ---------------------------------------------------------------------------
# Token verification
# ---------------------------------------------------------------------------

_credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT.  Raises HTTP 401 on any failure."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise _credentials_exception from exc
    return payload


def verify_access_token(token: str) -> dict[str, Any]:
    """Decode a token and assert its type is 'access'."""
    payload = decode_token(token)
    if payload.get("type") != "access":
        raise _credentials_exception
    return payload


def verify_refresh_token(token: str) -> dict[str, Any]:
    """Decode a token and assert its type is 'refresh'."""
    payload = decode_token(token)
    if payload.get("type") != "refresh":
        raise _credentials_exception
    return payload


# ---------------------------------------------------------------------------
# FastAPI dependencies
# ---------------------------------------------------------------------------


async def get_token_payload(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> dict[str, Any]:
    """FastAPI dependency: extract and verify the Bearer access token."""
    return verify_access_token(credentials.credentials)


async def get_current_user_id(
    payload: dict[str, Any] = Depends(get_token_payload),
) -> UUID:
    """FastAPI dependency: return the current user's UUID from the token subject."""
    sub = payload.get("sub")
    if not sub:
        raise _credentials_exception
    try:
        return UUID(sub)
    except ValueError as exc:
        raise _credentials_exception from exc


# NOTE: The full get_current_user dependency (which loads the User ORM object
# from the database) lives in app.api.deps to avoid circular imports between
# the core security module and the ORM models/database layer.
