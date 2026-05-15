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
    """Return the Microsoft OAuth2 authorization URL.
    MSAL injects openid/profile/offline_access automatically and rejects them
    if passed explicitly — only resource scopes go here."""
    app = get_msal_app()
    return app.get_authorization_request_url(
        scopes=["User.Read"],
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


def _entra_configured() -> bool:
    """True iff real Entra credentials are configured (not placeholders)."""
    placeholders = {"placeholder", "your-azure-app-client-id", "your-azure-app-client-secret", "your-azure-tenant-id", ""}
    return (
        settings.MICROSOFT_CLIENT_ID not in placeholders
        and settings.MICROSOFT_CLIENT_SECRET not in placeholders
        and settings.MICROSOFT_TENANT_ID not in placeholders
    )


def _acquire_app_token() -> str:
    """Acquire an app-only (client-credentials) token for Microsoft Graph.
    Used to search/list users in the tenant directory."""
    app = get_msal_app()
    result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    if "error" in result:
        raise ValueError(f"App token acquisition failed: {result.get('error_description', result.get('error'))}")
    return result["access_token"]


async def search_entra_users(query: str, top: int = 20) -> list[dict]:
    """Search users in the Entra ID tenant by displayName or mail.

    Returns a list of dicts shaped like
        {id, displayName, mail, userPrincipalName, jobTitle}
    Raises RuntimeError if Entra credentials are placeholders or not configured.
    """
    if not _entra_configured():
        raise RuntimeError(
            "Entra ID not configured. Set real MICROSOFT_CLIENT_ID, "
            "MICROSOFT_CLIENT_SECRET, MICROSOFT_TENANT_ID in .env "
            "(app needs Microsoft Graph User.Read.All application permission, admin-consented)."
        )

    token = _acquire_app_token()
    q = (query or "").strip().replace("'", "''")
    # Use $search if a query is given (works for any substring); fall back
    # to a plain list otherwise.
    params: dict
    if q:
        # $search needs ConsistencyLevel: eventual + Authorization header
        params = {
            "$search": f'"displayName:{q}" OR "mail:{q}"',
            "$top": top,
            "$select": "id,displayName,mail,userPrincipalName,jobTitle",
        }
        headers = {
            "Authorization": f"Bearer {token}",
            "ConsistencyLevel": "eventual",
        }
    else:
        params = {"$top": top, "$select": "id,displayName,mail,userPrincipalName,jobTitle"}
        headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(
            "https://graph.microsoft.com/v1.0/users",
            headers=headers,
            params=params,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("value", [])
