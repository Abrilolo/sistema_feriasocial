# app/core/auth_errors.py
"""
Códigos de error semánticos para el sistema de autenticación.
Permiten diagnóstico preciso sin exponer detalles sensibles al cliente.
"""

from enum import Enum
from typing import Optional


class AuthErrorCode(str, Enum):
    """Códigos de error para el flujo de autenticación."""

    # Errores de configuración
    CONFIG_MISSING_CLIENT_ID = "AUTH_CONFIG_MISSING_CLIENT_ID"
    CONFIG_MISSING_CLIENT_SECRET = "AUTH_CONFIG_MISSING_CLIENT_SECRET"
    CONFIG_INVALID_REDIRECT_URI = "AUTH_CONFIG_INVALID_REDIRECT_URI"

    # Errores de state OAuth
    STATE_MISSING = "AUTH_STATE_MISSING"
    STATE_INVALID_FORMAT = "AUTH_STATE_INVALID_FORMAT"
    STATE_INVALID_HMAC = "AUTH_STATE_INVALID_HMAC"
    STATE_MISMATCH = "AUTH_STATE_MISMATCH"
    STATE_ALREADY_USED = "AUTH_STATE_ALREADY_USED"
    STATE_EXPIRED = "AUTH_STATE_EXPIRED"

    # Errores de token exchange
    GOOGLE_CODE_EXCHANGE_FAILED = "AUTH_GOOGLE_CODE_EXCHANGE_FAILED"
    GOOGLE_TOKEN_INVALID = "AUTH_GOOGLE_TOKEN_INVALID"
    GOOGLE_USERINFO_FAILED = "AUTH_GOOGLE_USERINFO_FAILED"

    # Errores de dominio/identidad
    FORBIDDEN_DOMAIN = "AUTH_FORBIDDEN_DOMAIN"
    INVALID_EMAIL_FORMAT = "AUTH_INVALID_EMAIL_FORMAT"
    MISSING_REQUIRED_CLAIMS = "AUTH_MISSING_REQUIRED_CLAIMS"

    # Errores de estudiante
    STUDENT_UPSERT_FAILED = "AUTH_STUDENT_UPSERT_FAILED"
    STUDENT_NOT_FOUND = "AUTH_STUDENT_NOT_FOUND"
    STUDENT_BLOCKED = "AUTH_STUDENT_BLOCKED"

    # Errores de sesión
    SESSION_ISSUE_FAILED = "AUTH_SESSION_ISSUE_FAILED"
    SESSION_INVALID = "AUTH_SESSION_INVALID"
    SESSION_EXPIRED = "AUTH_SESSION_EXPIRED"

    # Errores federados
    FEDERATED_LOGOUT_FAILED = "AUTH_FEDERATED_LOGOUT_FAILED"
    POST_LOGOUT_HANDLER_FAILED = "AUTH_POST_LOGOUT_HANDLER_FAILED"

    # Errores generales
    UNKNOWN_ERROR = "AUTH_UNKNOWN_ERROR"
    RATE_LIMIT_EXCEEDED = "AUTH_RATE_LIMIT_EXCEEDED"


class AuthException(Exception):
    """Excepción base para errores de autenticación."""

    def __init__(
        self,
        code: AuthErrorCode,
        message: str,
        auth_request_id: Optional[str] = None,
        details: Optional[dict] = None
    ):
        self.code = code
        self.message = message
        self.auth_request_id = auth_request_id
        self.details = details or {}
        super().__init__(self.message)

    def to_log_dict(self) -> dict:
        """Convierte la excepción a dict para logging estructurado."""
        return {
            "event": "AUTH_FAILURE",
            "error_code": self.code.value,
            "error_message": self.message,
            "auth_request_id": self.auth_request_id,
            "details": self.details,
        }

    def to_client_response(self) -> dict:
        """Respuesta segura para enviar al cliente (sin detalles internos)."""
        user_messages = {
            AuthErrorCode.STATE_MISSING: "Tu sesión de autenticación expiró. Intenta de nuevo.",
            AuthErrorCode.STATE_INVALID_FORMAT: "La sesión de autenticación es inválida. Intenta de nuevo.",
            AuthErrorCode.STATE_INVALID_HMAC: "La sesión de autenticación fue alterada. Intenta de nuevo.",
            AuthErrorCode.STATE_MISMATCH: "La sesión de autenticación no coincide. Intenta de nuevo.",
            AuthErrorCode.STATE_ALREADY_USED: "Este enlace de autenticación ya fue usado. Intenta de nuevo.",
            AuthErrorCode.STATE_EXPIRED: "Tu sesión de autenticación expiró. Intenta de nuevo.",
            AuthErrorCode.GOOGLE_CODE_EXCHANGE_FAILED: "No pudimos validar tu inicio de sesión con Google. Intenta de nuevo.",
            AuthErrorCode.GOOGLE_TOKEN_INVALID: "El token de Google no es válido. Intenta de nuevo.",
            AuthErrorCode.FORBIDDEN_DOMAIN: "Solo se permiten cuentas institucionales del Tec.",
            AuthErrorCode.INVALID_EMAIL_FORMAT: "El formato del correo no es válido.",
            AuthErrorCode.MISSING_REQUIRED_CLAIMS: "Falta información necesaria de tu cuenta.",
            AuthErrorCode.STUDENT_UPSERT_FAILED: "Error al registrar tu cuenta. Contacta a soporte.",
            AuthErrorCode.SESSION_ISSUE_FAILED: "Error al crear tu sesión. Intenta de nuevo.",
            AuthErrorCode.FEDERATED_LOGOUT_FAILED: "Error al cerrar sesión en el sistema federado.",
            AuthErrorCode.RATE_LIMIT_EXCEEDED: "Demasiados intentos. Espera un momento.",
        }

        return {
            "error": True,
            "code": self.code.value,
            "message": user_messages.get(self.code, "Ocurrió un error de autenticación. Intenta de nuevo."),
            "auth_request_id": self.auth_request_id,  # Para soporte
        }
