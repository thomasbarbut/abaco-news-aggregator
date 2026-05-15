import msal
import httpx

from app.core.config import settings


def get_msal_app() -> msal.ConfidentialClientApplication:
    """Return a configured MSAL ConfidentialClientApplication instance."""
    return msal.ConfidentialClientApplication(
        settings.MICROSOFT_CLIENT_ID,
        authority=f"https://login.microsoftonline.com/{settings.MICROSOFT_TENANT_ID}",
        client_credential=settings.MICROSOFT_CLIENT_SECRET,
    )


def get_auth_url(state: str) -> str:
    """Return the Microsoft OAuth2 authorization URL."""
    app = get_msal_app()
    return app.get_authorization_request_url(
        scopes=["User.Read", "openid", "profile", "email"],
        state=state,
        redirect_uri=settings.MICROSOFT_REDIRECT_URI,
    )


async def exchange_code_for_token(code: str) -> dict:
    """Exchange an authorization code for Microsoft tokens.

    Returns the full MSAL token result dict (contains access_token,
    id_token, and optional refresh_token).
    Raises ValueError if the token exchange fails.
    """
    app = get_msal_app()
    result = app.acquire_token_by_authorization_code(
        code,
        scopes=["User.Read"],
        redirect_uri=settings.MICROSOFT_REDIRECT_URI,
    )
    if "error" in result:
        raise ValueError(
            f"Token exchange failed: {result.get('error_description', result.get('error'))}"
        )
    return result


async def get_user_info(access_token: str) -> dict:
    """Fetch the authenticated user's profile from Microsoft Graph API."""
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(
            "https://graph.microsoft.com/v1.0/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        response.raise_for_status()
        return response.json()
