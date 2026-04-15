#app/core/security.py
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.models.student import Student

# Swagger detecta esto y crea el botón Authorize si hay endpoints que lo dependan
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# -----------------------
# Password hashing (bcrypt)
# -----------------------
def hash_password(password: str) -> str:
    # bcrypt solo procesa 72 bytes: para passwords normales estás ok.
    pw_bytes = password.encode("utf-8")
    if len(pw_bytes) > 72:
        raise ValueError("Password demasiado largo para bcrypt (max 72 bytes).")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pw_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False


# -----------------------
# JWT
# -----------------------
def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()

    expire_minutes = getattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 60)

    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=expire_minutes))
    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALG)
    return encoded_jwt


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALG])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )


# -----------------------
# Current user + Roles
# -----------------------
def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
) -> User:
    payload = decode_access_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token sin subject (sub)")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    if not getattr(user, "is_active", True):
        raise HTTPException(status_code=403, detail="Usuario inactivo")

    return user


def require_role(required_role: str):
    def _checker(user: User = Depends(get_current_user)) -> User:
        if user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Acceso denegado: requiere rol {required_role}",
            )
        return user
    return _checker


def get_current_student(
    request: Request,
    db: Session = Depends(get_db),
) -> Student:
    """
    Identifica al estudiante usando la cookie 'student_token' creada por el flujo de Google.
    """
    token = request.cookies.get("student_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesión de estudiante no encontrada. Inicia sesión con Google."
        )

    payload = decode_access_token(token)
    student_id = payload.get("sub")

    if not student_id or payload.get("type") != "student":
        raise HTTPException(status_code=401, detail="Token de estudiante inválido")

    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=401, detail="Estudiante no encontrado en la base de datos")

    return student


def get_user_flex(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    """
    Autentica usuarios de staff (Becario/Admin) desde cookie HttpOnly O header Authorization.
    Resuelve el problema donde el scanner del Becario falla si localStorage está vacío.
    """
    # 1. Intentar cookie HttpOnly (flujo normal de navegador)
    token = request.cookies.get("access_token", "")
    if token.startswith("Bearer "):
        token = token[7:]

    # 2. Fallback: Bearer header (Swagger, apps externas)
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Se requiere autenticación de staff.",
        )

    payload = decode_access_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token sin subject")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    if not getattr(user, "is_active", True):
        raise HTTPException(status_code=403, detail="Usuario inactivo")

    return user