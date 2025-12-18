"""
Middleware d'authentification OAuth2
Valide les tokens auprès du serveur OAuth2
"""
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import httpx
import os

security = HTTPBearer()

# URL du serveur OAuth2
OAUTH2_URL = os.getenv("OAUTH2_URL", "http://localhost:3000")


async def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> dict:
    """
    Vérifie le token OAuth2 en appelant l'API OAuth2

    Args:
        credentials: Credentials Bearer token

    Returns:
        dict: Informations du token validé

    Raises:
        HTTPException: Si le token est invalide
    """
    token = credentials.credentials
    print(f"[DEBUG] Validating token: {token[:20]}...")
    print(f"[DEBUG] OAuth2 URL: {OAUTH2_URL}")

    try:
        # Appeler l'endpoint /secure de l'API OAuth2 pour valider le token
        # Note: express-oauth-server a des problèmes avec le header Bearer,
        # donc on utilise le query parameter access_token
        async with httpx.AsyncClient() as client:
            url = f"{OAUTH2_URL}/v1/secure?access_token={token}"
            print(f"[DEBUG] Calling: {url}")
            response = await client.get(url, timeout=5.0)
            print(f"[DEBUG] Response status: {response.status_code}")
            print(f"[DEBUG] Response body: {response.text[:200]}")

            if response.status_code == 200:
                # Token valide
                return response.json()
            elif response.status_code == 401:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid or expired token",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"OAuth2 server error: {response.status_code}"
                )

    except httpx.RequestError as e:
        print(f"[DEBUG] Request error: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail=f"OAuth2 server unavailable: {str(e)}"
        )


async def get_current_user(token_data: dict = Depends(verify_token)) -> dict:
    """
    Récupère les informations de l'utilisateur courant

    Args:
        token_data: Données du token validé

    Returns:
        dict: Informations utilisateur
    """
    return token_data.get("user", {})


# Dépendance optionnelle pour les endpoints publics
async def optional_verify_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security)
) -> Optional[dict]:
    """
    Vérifie le token OAuth2 de manière optionnelle
    Retourne None si pas de token
    """
    if credentials is None:
        return None

    return await verify_token(credentials)
