import os

from fastapi import Header, HTTPException, status

API_KEY = os.getenv("API_KEY", "")


def require_api_key(x_api_key: str = Header(default="", alias="X-API-Key")):
    """Authentification simple par clé API pour les requêtes du backend central."""
    if not API_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API_KEY non configurée côté serveur",
        )
    if x_api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Clé API invalide",
        )
    return x_api_key
