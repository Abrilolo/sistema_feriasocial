# app/services/auth_service.py
"""
Servicios de autenticación federada para el flujo OAuth con Google.
Implementa separación de responsabilidades y trazabilidad completa.
"""

import hashlib
import hmac
import logging
import secrets
import time
import urllib.parse
from datetime import datetime, timezone
from typing import Optional, Tuple

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.auth_errors import AuthErrorCode, AuthException
from app.core.config import settings
from app.models.student import Student

logger = logging.getLogger(__name__)

# Almacenamiento temporal en memoria para states consumidos
# En producción con múltiples workers, usar Redis o similar
_consumed_states: set = set()
_state_timestamps: dict = {}

# Ventana de tiempo para limpieza de states antiguos (10 minutos)
STATE_CLEANUP_WINDOW = 600


def _cleanup_old_states():
    """Limpia states antiguos para evitar crecimiento indefinido."""
    global _consumed_states, _state_timestamps
    now = time.time()
    expired_states = {
        state for state, timestamp in _state_timestamps.items()
        if now - timestamp > STATE_CLEANUP_WINDOW
    }
    _consumed_states -= expired_states
    for state in expired_states:
        del _state_timestamps[state]


class OAuthStateService:
    """Servicio para manejo de state OAuth - generación, validación e invalidación."""

    @staticmethod
    def generate_state() -> Tuple[str, str]:
        """
        Genera un state firmado con HMAC.

        Returns:
            Tuple de (state_completo, auth_request_id)
        """
        auth_request_id = secrets.token_urlsafe(16)
        nonce = secrets.token_urlsafe(32)
        mac = hmac.new(
            settings.JWT_SECRET.encode(),
            f"{auth_request_id}.{nonce}".encode(),
            hashlib.sha256
        ).hexdigest()
        state = f"{auth_request_id}.{nonce}.{mac}"
        return state, auth_request_id

    @staticmethod
    def validate_state(state_from_google: str, state_from_cookie: str) -> str:
        """
        Valida que el state de Google coincida con el de la cookie y no haya sido usado.

        Args:
            state_from_google: State recibido en el callback
            state_from_cookie: State almacenado en la cookie

        Returns:
            auth_request_id extraído del state

        Raises:
            AuthException: Si el state es inválido o ya fue usado
        """
        if not state_from_google or not state_from_cookie:
            raise AuthException(
                AuthErrorCode.STATE_MISSING,
                "Falta el parámetro state OAuth",
            )

        if not hmac.compare_digest(state_from_google, state_from_cookie):
            raise AuthException(
                AuthErrorCode.STATE_MISMATCH,
                "State de Google no coincide con el de la cookie",
                details={"state_present": bool(state_from_google)}
            )

        # Verificar formato y HMAC
        try:
            parts = state_from_google.rsplit(".", 2)
            if len(parts) != 3:
                raise ValueError("Formato incorrecto")
            auth_request_id, nonce, received_mac = parts

            expected_mac = hmac.new(
                settings.JWT_SECRET.encode(),
                f"{auth_request_id}.{nonce}".encode(),
                hashlib.sha256
            ).hexdigest()

            if not hmac.compare_digest(expected_mac, received_mac):
                raise ValueError("HMAC inválido")

        except Exception as e:
            raise AuthException(
                AuthErrorCode.STATE_INVALID_HMAC,
                f"State corrupto: {str(e)}",
            )

        # Verificar que no haya sido usado (single-use)
        if state_from_google in _consumed_states:
            raise AuthException(
                AuthErrorCode.STATE_ALREADY_USED,
                "State OAuth ya fue consumido",
                auth_request_id=auth_request_id,
            )

        return auth_request_id

    @staticmethod
    def consume_state(state: str, auth_request_id: str) -> None:
        """
        Marca un state como consumido para prevenir replay.

        Args:
            state: El state completo a invalidar
            auth_request_id: ID de la solicitud para logging
        """
        _cleanup_old_states()
        _consumed_states.add(state)
        _state_timestamps[state] = time.time()
        logger.debug(f"State consumido - auth_request_id={auth_request_id}")


class FederatedAuthService:
    """Servicio para interacción con Google OAuth y manejo de tokens."""

    @staticmethod
    def build_google_auth_url(state: str, redirect_uri: str) -> str:
        """
        Construye la URL de autenticación de Google.

        Args:
            state: State firmado para validación CSRF
            redirect_uri: URI de callback registrada

        Returns:
            URL completa de autenticación
        """
        params = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "prompt": "select_account consent",
            "hd": settings.STUDENT_EMAIL_DOMAIN,
            "access_type": "online",
        }
        return "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)

    @staticmethod
    def exchange_code_for_token(code: str, redirect_uri: str) -> dict:
        """
        Intercambia el código de autorización por tokens de Google.

        Args:
            code: Código recibido en el callback
            redirect_uri: URI de callback (debe coincidir con el login)

        Returns:
            Dict con los tokens de Google

        Raises:
            AuthException: Si el exchange falla
        """
        try:
            response = httpx.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            error_data = e.response.json() if e.response else {}
            raise AuthException(
                AuthErrorCode.GOOGLE_CODE_EXCHANGE_FAILED,
                f"Error al intercambiar código: {error_data.get('error_description', str(e))}",
                details={
                    "error": error_data.get("error"),
                    "status_code": e.response.status_code if e.response else None,
                }
            )
        except Exception as e:
            raise AuthException(
                AuthErrorCode.GOOGLE_CODE_EXCHANGE_FAILED,
                f"Error inesperado en exchange: {str(e)}",
            )

    @staticmethod
    def get_userinfo(access_token: str) -> dict:
        """
        Obtiene información del usuario desde Google.

        Args:
            access_token: Token de acceso de Google

        Returns:
            Dict con la información del usuario

        Raises:
            AuthException: Si no se puede obtener la información
        """
        try:
            response = httpx.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10.0,
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            raise AuthException(
                AuthErrorCode.GOOGLE_USERINFO_FAILED,
                f"Error al obtener userinfo: {e.response.text}",
                details={"status_code": e.response.status_code}
            )
        except Exception as e:
            raise AuthException(
                AuthErrorCode.GOOGLE_USERINFO_FAILED,
                f"Error inesperado al obtener userinfo: {str(e)}",
            )


class StudentAuthService:
    """Servicio para manejo de estudiantes en el flujo de autenticación."""

    @staticmethod
    def validate_email_domain(email: str, auth_request_id: Optional[str] = None) -> bool:
        """
        Valida que el email pertenezca al dominio institucional.

        Args:
            email: Email a validar
            auth_request_id: ID para trazabilidad

        Returns:
            True si el dominio es válido

        Raises:
            AuthException: Si el dominio no es válido
        """
        if not email:
            raise AuthException(
                AuthErrorCode.INVALID_EMAIL_FORMAT,
                "Email vacío",
                auth_request_id=auth_request_id,
            )

        email_lower = email.lower()
        expected_domain = f"@{settings.STUDENT_EMAIL_DOMAIN.lower()}"

        if not email_lower.endswith(expected_domain):
            raise AuthException(
                AuthErrorCode.FORBIDDEN_DOMAIN,
                f"Dominio no permitido: {email}",
                auth_request_id=auth_request_id,
                details={
                    "email_domain": email_lower.split("@")[-1] if "@" in email else None,
                    "expected_domain": settings.STUDENT_EMAIL_DOMAIN,
                }
            )

        return True

    @staticmethod
    def extract_matricula(email: str) -> str:
        """
        Extrae la matrícula del email institucional.

        Args:
            email: Email institucional (ej: A01234567@tec.mx)

        Returns:
            Matrícula en mayúsculas (ej: A01234567)
        """
        return email.split("@")[0].upper()

    @staticmethod
    def upsert_student(
        db: Session,
        google_id: str,
        email: str,
        full_name: Optional[str],
        picture_url: Optional[str],
        auth_request_id: Optional[str] = None,
    ) -> Student:
        """
        Crea o actualiza un estudiante de forma atómica (upsert).

        Args:
            db: Sesión de base de datos
            google_id: ID de Google (sub)
            email: Email del estudiante
            full_name: Nombre completo
            picture_url: URL de la foto de perfil
            auth_request_id: ID para trazabilidad

        Returns:
            Estudiante creado o actualizado

        Raises:
            AuthException: Si el upsert falla
        """
        matricula = StudentAuthService.extract_matricula(email)

        # Upsert atómico resistente a race conditions
        upsert_sql = text("""
            INSERT INTO students
                (id, google_id, email, matricula, full_name, picture_url, created_at)
            VALUES
                (gen_random_uuid(), :google_id, :email, :matricula, :full_name, :picture_url, now())
            ON CONFLICT (google_id) DO UPDATE SET
                email       = EXCLUDED.email,
                matricula   = EXCLUDED.matricula,
                full_name   = COALESCE(EXCLUDED.full_name, students.full_name),
                picture_url = COALESCE(EXCLUDED.picture_url, students.picture_url),
                updated_at  = now()
            RETURNING id
        """)

        try:
            result = db.execute(upsert_sql, {
                "google_id": google_id,
                "email": email,
                "matricula": matricula,
                "full_name": full_name,
                "picture_url": picture_url,
            })
            db.commit()
            row = result.fetchone()

            if not row:
                raise AuthException(
                    AuthErrorCode.STUDENT_UPSERT_FAILED,
                    "Upsert no retornó ID",
                    auth_request_id=auth_request_id,
                )

            # Recuperar el estudiante completo
            student = db.query(Student).filter(Student.id == row.id).first()
            if not student:
                raise AuthException(
                    AuthErrorCode.STUDENT_NOT_FOUND,
                    "Estudiante creado pero no encontrado",
                    auth_request_id=auth_request_id,
                )

            return student

        except AuthException:
            db.rollback()
            raise
        except Exception as e:
            db.rollback()
            raise AuthException(
                AuthErrorCode.STUDENT_UPSERT_FAILED,
                f"Error en upsert: {str(e)}",
                auth_request_id=auth_request_id,
                details={"error_type": type(e).__name__},
            )


class AuthLogger:
    """Servicio para logging estructurado de eventos de autenticación."""

    @staticmethod
    def log_event(
        event: str,
        auth_request_id: Optional[str] = None,
        **kwargs
    ) -> None:
        """
        Loguea un evento de autenticación de forma estructurada.

        Args:
            event: Nombre del evento (ej: AUTH_LOGIN_STARTED)
            auth_request_id: ID de la solicitud
            **kwargs: Campos adicionales para el log
        """
        log_data = {
            "event": event,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "auth_request_id": auth_request_id,
            **kwargs
        }

        # Filtrar campos sensibles
        safe_log = {k: v for k, v in log_data.items() if v is not None}
        logger.info(f"AUTH_EVENT: {safe_log}")

    @staticmethod
    def log_failure(
        error_code: AuthErrorCode,
        message: str,
        auth_request_id: Optional[str] = None,
        **kwargs
    ) -> None:
        """
        Loguea un fallo de autenticación.

        Args:
            error_code: Código de error
            message: Mensaje descriptivo
            auth_request_id: ID de la solicitud
            **kwargs: Campos adicionales
        """
        log_data = {
            "event": "AUTH_FAILURE",
            "error_code": error_code.value,
            "error_message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "auth_request_id": auth_request_id,
            **kwargs
        }
        logger.warning(f"AUTH_FAILURE: {log_data}")
