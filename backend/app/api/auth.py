import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import create_access_token, create_refresh_token, verify_refresh_token
from app.core.logging import get_logger
from app.auth.microsoft import get_auth_url, exchange_code_for_token, get_user_info
from app.auth.dependencies import get_current_user
from app.models.user import User, UserRole
from app.schemas.auth import TokenResponse, RefreshRequest
from app.schemas.user import UserResponse

logger = get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/login")
async def login() -> dict:
    """Return the Microsoft OAuth2 authorization URL and a CSRF state token.

    The client should redirect the user to ``auth_url`` and store ``state``
    locally for verification when the callback is received.
    """
    state = secrets.token_urlsafe(32)
    auth_url = get_auth_url(state)
    return {"auth_url": auth_url, "state": state}


@router.get("/callback", response_model=TokenResponse)
async def auth_callback(
    code: str = Query(..., description="OAuth2 authorization code from Microsoft"),
    state: str = Query(None, description="CSRF state token"),
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Handle the Microsoft OAuth2 callback.

    Exchanges the authorization code for tokens, fetches user info from
    Microsoft Graph, creates or updates the local user record, and returns
    a JWT token pair.
    """
    try:
        token_result = await exchange_code_for_token(code)
        ms_access_token = token_result.get("access_token")
        if not ms_access_token:
            raise ValueError("No access_token in Microsoft token response")
        user_info = await get_user_info(ms_access_token)
    except Exception as exc:
        logger.error("OAuth callback error", extra={"error": str(exc)})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authentication failed",
        )

    microsoft_id: str = user_info.get("id", "")
    email: str = user_info.get("mail") or user_info.get("userPrincipalName", "")
    name: str = user_info.get("displayName", "")

    if not microsoft_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not retrieve Microsoft user ID",
        )

    # Find or create the local user record
    result = await db.execute(select(User).where(User.microsoft_id == microsoft_id))
    user: User | None = result.scalar_one_or_none()

    now = datetime.now(timezone.utc)
    if user is None:
        user = User(
            microsoft_id=microsoft_id,
            email=email,
            name=name,
            role=UserRole.user,
            last_login=now,
        )
        db.add(user)
    else:
        user.last_login = now
        user.email = email
        user.name = name

    await db.flush()
    await db.refresh(user)

    access_token = create_access_token(
        subject=str(user.id),
        extra_claims={"role": user.role.value},
    )
    refresh_token = create_refresh_token(subject=str(user.id))

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=3600,
    )


@router.post("/refresh")
async def refresh_token(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Issue a new access token using a valid refresh token."""
    try:
        payload = verify_refresh_token(body.refresh_token)
        user_id: str = payload.get("sub")
        if not user_id:
            raise ValueError("Missing subject in refresh token")
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    from uuid import UUID
    user = await db.get(User, UUID(user_id))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    access_token = create_access_token(
        subject=str(user.id),
        extra_claims={"role": user.role.value},
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": 3600,
    }


@router.post("/logout")
async def logout() -> dict:
    """Invalidate the current session (client-side token deletion)."""
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)) -> User:
    """Return the authenticated user's profile."""
    return current_user
