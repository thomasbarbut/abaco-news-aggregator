"""Tests for the /api/auth endpoints."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.core.security import create_access_token, create_refresh_token
from app.models.user import User, UserRole
from tests.conftest import auth_headers_for

pytestmark = pytest.mark.asyncio


async def test_login_returns_auth_url(client: AsyncClient) -> None:
    """GET /api/auth/login should return a Microsoft auth URL and a state token."""
    fake_url = "https://login.microsoftonline.com/tenant/oauth2/v2.0/authorize?client_id=x&state=y"
    with patch("app.api.auth.get_auth_url", return_value=fake_url):
        response = await client.get("/api/auth/login")
    assert response.status_code == 200
    data = response.json()
    assert "auth_url" in data
    assert "state" in data
    assert "login.microsoftonline.com" in data["auth_url"]
    assert len(data["state"]) > 16  # should be a meaningful random value


async def test_me_requires_auth(client: AsyncClient) -> None:
    """GET /api/auth/me without a token should return 401."""
    response = await client.get("/api/auth/me")
    assert response.status_code == 401


async def test_me_returns_user(
    client: AsyncClient,
    test_user: User,
) -> None:
    """GET /api/auth/me with a valid token should return the user profile."""
    response = await client.get(
        "/api/auth/me",
        headers=auth_headers_for(test_user),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(test_user.id)
    assert data["email"] == test_user.email
    assert data["name"] == test_user.name
    assert data["role"] == test_user.role.value


async def test_refresh_token(
    client: AsyncClient,
    test_user: User,
) -> None:
    """POST /api/auth/refresh with a valid refresh token should return a new access token."""
    refresh_tok = create_refresh_token(subject=str(test_user.id))

    response = await client.post(
        "/api/auth/refresh",
        json={"refresh_token": refresh_tok},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 3600


async def test_refresh_token_invalid(client: AsyncClient) -> None:
    """POST /api/auth/refresh with a garbage token should return 401."""
    response = await client.post(
        "/api/auth/refresh",
        json={"refresh_token": "not.a.valid.token"},
    )
    assert response.status_code == 401


async def test_logout(client: AsyncClient, test_user: User) -> None:
    """POST /api/auth/logout should return a success message."""
    response = await client.post(
        "/api/auth/logout",
        headers=auth_headers_for(test_user),
    )
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "logged out" in data["message"].lower()


async def test_me_with_invalid_token(client: AsyncClient) -> None:
    """GET /api/auth/me with a tampered token should return 401."""
    response = await client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer invalid.jwt.token"},
    )
    assert response.status_code == 401


async def test_me_admin_role(
    client: AsyncClient,
    test_admin: User,
) -> None:
    """GET /api/auth/me should correctly reflect the admin role."""
    response = await client.get(
        "/api/auth/me",
        headers=auth_headers_for(test_admin),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == UserRole.admin.value
