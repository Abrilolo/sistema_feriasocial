from jose import JWTError
from jose import jwt

from fastapi import HTTPException, status

from app.core.config import settings


def decode_token(token: str) -> dict:
    """
    Decodifica y valida el JWT.
    - Verifica firma (JWT_SECRET)
    - Verifica expiración (exp)
    Devuelve el payload si es válido.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALG],
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )