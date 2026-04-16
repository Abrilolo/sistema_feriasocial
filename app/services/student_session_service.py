# app/services/student_session_service.py
"""
Servicio para manejo de sesiones de estudiantes (JWT + cookies).
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Request, Response
from jose import JWTError, jwt

from app.core.config import settings
from app.models.student import Student

logger = logging.getLogger(__name__)


class StudentSessionService:
    """Servicio para crear, validar y destruir sesiones de estudiantes."""

    # Tiempo de expiración de la sesión del estudiante
    SESSION_EXPIRE_MINUTES = 30

    @staticmethod
    def create_student_token(student: Student) -> str:
        """
        Crea un JWT para el estudiante.

        Args:
            student: Estudiante autenticado

        Returns:
            Token JWT firmado
        """
        from app.core.security import create_access_token

        return create_access_token({
            "sub": str(student.id),
            "type": "student",
            "email": student.email,
            "matricula": student.matricula,
            "name": student.full_name,
            "iat": datetime.now(timezone.utc).timestamp(),
        })

    @staticmethod
    def set_student_cookie(
        response: Response,
        token: str,
        clear_existing: bool = False
    ) -> None:
        """
        Configura la cookie de sesión del estudiante.

        Args:
            response: Objeto Response de FastAPI
            token: Token JWT del estudiante
            clear_existing: Si True, primero borra cookies previas
        """
        is_production = settings.ENVIRONMENT == "production"

        if clear_existing:
            # Borrar cookie previa antes de setear nueva
            response.delete_cookie(
                key="student_token",
                path="/",
            )

        response.set_cookie(
            key="student_token",
            value=token,
            httponly=True,
            secure=is_production,
            samesite="lax",
            max_age=60 * StudentSessionService.SESSION_EXPIRE_MINUTES,
            path="/",
        )

    @staticmethod
    def clear_student_session(response: Response) -> None:
        """
        Borra la sesión del estudiante.

        Args:
            response: Objeto Response de FastAPI
        """
        response.delete_cookie(
            key="student_token",
            path="/",
        )

    @staticmethod
    def get_student_from_request(request: Request) -> Optional[dict]:
        """
        Extrae y valida el token del estudiante desde la request.

        Args:
            request: Objeto Request de FastAPI

        Returns:
            Payload del token si es válido, None si no hay o es inválido
        """
        token = request.cookies.get("student_token")
        if not token:
            return None

        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET,
                algorithms=[settings.JWT_ALG],
            )
            return payload
        except JWTError:
            return None

    @staticmethod
    def has_active_session(request: Request) -> bool:
        """
        Verifica si hay una sesión activa de estudiante.

        Args:
            request: Objeto Request de FastAPI

        Returns:
            True si hay sesión válida
        """
        payload = StudentSessionService.get_student_from_request(request)
        if not payload:
            return False

        # Verificar expiración
        exp = payload.get("exp")
        if exp and datetime.now(timezone.utc).timestamp() > exp:
            return False

        return True

    @staticmethod
    def get_session_info(request: Request) -> Optional[dict]:
        """
        Obtiene información legible de la sesión actual.

        Args:
            request: Objeto Request de FastAPI

        Returns:
            Dict con info del estudiante o None
        """
        payload = StudentSessionService.get_student_from_request(request)
        if not payload:
            return None

        return {
            "student_id": payload.get("sub"),
            "email": payload.get("email"),
            "matricula": payload.get("matricula"),
            "name": payload.get("name"),
        }
