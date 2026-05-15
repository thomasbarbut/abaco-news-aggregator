"""Authentication routes – Microsoft Entra ID (MSAL) OAuth2/OIDC flow."""

import urllib.parse
from datetime import datetime, timezone

import msal
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.logging import get_logger
from app.core.security import (
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
    create_token_pair,
    verify_refresh_token,
)
from app.models.user import User
from app.schemas.auth import RefreshRequest, TokenResponse

router = APIRouter()
logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# MSAL helpers
# ---------------------------------------------------------------------------

_SCOPES = ["openid", "profile", "email", "User.Read"]
_AUTHORITY = f"https://login.microsoftonline.com/{settings.MICROSOFT_TENANT_ID}"


def _get_msal_app() -> msal.ConfidentialClientApplication:
    return msal.ConfidentialClientApplication(
        client_id=settings.MICROSOFT_CLIENT_ID,
        client_credential=settings.MICROSOFT_CLIENT_SECRET,
        authority=_AUTHORITY,
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/login", summary="Redirect to Microsoft login page")
async def login(request: Request) -> RedirectResponse:
    """Initiate the OAuth2 authorisation-code flow."""
    msal_app = _get_msal_app()
    auth_url = msal_app.get_authorization_request_url(
        scopes=_SCOPES,
        redirect_uri=settings.MICROSOFT_REDIRECT_URI,
        response_type="code",
    )
    return RedirectResponse(url=auth_url)


@router.get("/callback", summary="Microsoft OAuth2 callback", response_model=TokenResponse)
async def auth_callback(
    code: str,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Exchange the authorisation code for tokens and upsert the user."""
    msal_app = _get_msal_app()
    result = msal_app.acquire_token_by_authorization_code(
        code=code,
        scopes=_SCOPES,
        redirect_uri=settings.MICROSOFT_REDIRECT_URI,
    )

    if "error" in result:
        logger.warning("MSAL token acquisition failed", extra={"msal_error": result})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=result.get("error_description", "Authentication failed"),
        )

    id_token_claims: dict = result.get("id_token_claims", {})
    microsoft_id: str = id_token_claims.get("oid") or id_token_claims.get("sub", "")
    email: str = id_token_claims.get("preferred_username") or id_token_claims.get("email", "")
    name: str = id_token_claims.get("name", "")

    if not microsoft_id or not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incomplete identity claims from Microsoft",
        )

    # Upsert user
    stmt = select(User).where(User.microsoft_id == microsoft_id)
    existing = (await db.execute(stmt)).scalar_one_or_none()

    if existing is None:
        user = User(
            microsoft_id=microsoft_id,
            email=email.lower(),
            name=name,
        )
        db.add(user)
        await db.flush()
        logger.info("New user created", extra={"user_email": email})
    else:
        user = existing
        user.last_login = datetime.now(timezone.utc)
        if email:
            user.email = email.lower()
        if name:
            user.name = name
        logger.info("User logged in", extra={"user_email": email})

    await db.commit()
    await db.refresh(user)

    access_token, refresh_token = create_token_pair(
        subject=user.id,
        extra_claims={"role": user.role.value, "email": user.email},
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/dev-login", summary="LOCAL DEV ONLY — auto-login as admin", response_model=TokenResponse)
async def dev_login(db: AsyncSession = Depends(get_db)) -> TokenResponse:
    """Bypass Entra ID for local dev. Returns a JWT for a user named 'admin'.

    Only works when DEBUG=true. In production this returns 404 so the endpoint
    effectively doesn't exist."""
    if not settings.DEBUG:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    from app.models.user import UserRole

    email = "admin@local.dev"
    stmt = select(User).where(User.email == email)
    user = (await db.execute(stmt)).scalar_one_or_none()
    if user is None:
        user = User(
            email=email,
            name="admin",
            role=UserRole.admin,
            microsoft_id="dev-local-admin",  # not real, just needed to satisfy NOT NULL/UNIQUE
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        logger.info(f"Dev-login created admin user id={user.id}")

    access_token, refresh_token = create_token_pair(
        subject=user.id,
        extra_claims={"role": user.role.value, "email": user.email},
    )
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", summary="Refresh access token", response_model=TokenResponse)
async def refresh_token(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Issue a new access/refresh token pair given a valid refresh token."""
    payload = verify_refresh_token(body.refresh_token)
    from uuid import UUID

    user_id = UUID(payload["sub"])
    stmt = select(User).where(User.id == user_id)
    user = (await db.execute(stmt)).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    access_token, new_refresh_token = create_token_pair(
        subject=user.id,
        extra_claims={"role": user.role.value, "email": user.email},
    )
    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
