"""Authentication helpers for WebSocket connections."""
from datetime import datetime, timezone
from typing import Any, Dict

from jose import JWTError, jwt

import os

JWT_SECRET = os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-in-production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_ISSUER = os.getenv("JWT_ISSUER", "realtoragentai")
JWT_AUDIENCE = os.getenv("JWT_AUDIENCE", "realtoragentai")


def decode_jwt(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT token.

    Raises ``ValueError`` if the token is invalid.
    """
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            audience=JWT_AUDIENCE,
            issuer=JWT_ISSUER,
        )
        now = datetime.now(timezone.utc)
        if "nbf" in payload and datetime.fromtimestamp(payload["nbf"], timezone.utc) > now:
            raise JWTError("Token not yet valid")
        if "iat" in payload and datetime.fromtimestamp(payload["iat"], timezone.utc) > now:
            raise JWTError("Token issued in the future")
        return payload
    except JWTError as exc:
        raise ValueError("Invalid token") from exc

__all__ = ["decode_jwt"]
