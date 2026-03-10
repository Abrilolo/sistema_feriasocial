from jose import JWTError, jwt
from fastapi import HTTPException, status

from app.core.config import settings


def decode_token(token: str) -> dict:
    """
    Decodifica y valida el JWT.
    - Verifica firma (SECRET_KEY)
    - Verifica expiración (exp)
    Devuelve el payload si es válido.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
