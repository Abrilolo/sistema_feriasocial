# app/services/federated_logout_service.py
"""
Servicio para manejo de logout federado con Microsoft/ADFS.
"""

import logging
import urllib.parse
from enum import Enum
from typing import Optional

from fastapi import Request
from starlette.responses import RedirectResponse

from app.core.config import settings

logger = logging.getLogger(__name__)

# Almacenamiento temporal de intenciones de logout
# En producción con múltiples workers, usar Redis
_logout_intentions: dict = {}


class LogoutReason(str, Enum):
    """Razones posibles para el logout."""
    SIMPLE_LOGOUT = "simple_logout"
    SWITCH_ACCOUNT = "switch_account"
    SESSION_EXPIRED = "session_expired"
    SECURITY_LOGOUT = "security_logout"


def _get_base_url(request: Request) -> str:
    """Obtiene la URL base del sistema."""
    if settings.APP_BASE_URL:
        return settings.APP_BASE_URL.rstrip("/")
    return str(request.base_url).rstrip("/")


class FederatedLogoutService:
    """Servicio para manejar logout federado con Microsoft."""

    @staticmethod
    def set_logout_intention(
        session_id: str,
        reason: LogoutReason,
        redirect_after: Optional[str] = None,
    ) -> None:
        """
        Registra la intención de logout para recuperarla después del post-logout.

        Args:
            session_id: Identificador único de la sesión
            reason: Razón del logout
            redirect_after: URL a redirigir después del logout federado
        """
        _logout_intentions[session_id] = {
            "reason": reason,
            "redirect_after": redirect_after or "/acceso-estudiante",
            "timestamp": __import__("time").time(),
        }

    @staticmethod
    def get_logout_intention(session_id: str) -> Optional[dict]:
        """
        Recupera y elimina la intención de logout.

        Args:
            session_id: Identificador de la sesión

        Returns:
            Dict con la intención o None
        """
        intention = _logout_intentions.pop(session_id, None)
        # Limpiar entradas antiguas (más de 5 minutos)
        current_time = __import__("time").time()
        expired = [
            sid
            for sid, data in _logout_intentions.items()
            if current_time - data.get("timestamp", 0) > 300
        ]
        for sid in expired:
            del _logout_intentions[sid]
        return intention

    @staticmethod
    def build_microsoft_logout_url(
        request: Request,
        post_logout_redirect: Optional[str] = None,
    ) -> str:
        """
        Construye la URL de logout federado de Microsoft.

        Args:
            request: Request de FastAPI
            post_logout_redirect: URL de retorno después del logout

        Returns:
            URL de logout de Microsoft
        """
        base = _get_base_url(request)

        if post_logout_redirect:
            # Si se proporciona un redirect específico, usarlo
            redirect_url = (
                post_logout_redirect
                if post_logout_redirect.startswith("http")
                else f"{base}{post_logout_redirect}"
            )
        else:
            redirect_url = f"{base}/auth/post-logout"

        encoded_redirect = urllib.parse.quote(redirect_url, safe="")

        return (
            "https://login.microsoftonline.com/common/oauth2/v2.0/logout"
            f"?post_logout_redirect_uri={encoded_redirect}"
        )

    @staticmethod
    def create_logout_response(
        request: Request,
        reason: LogoutReason = LogoutReason.SIMPLE_LOGOUT,
        session_id: Optional[str] = None,
        redirect_after: Optional[str] = None,
    ) -> RedirectResponse:
        """
        Crea una respuesta de logout completa con limpieza de cookies y redirección federada.

        Args:
            request: Request de FastAPI
            reason: Razón del logout
            session_id: ID de sesión para recuperar intención
            redirect_after: URL de redirección después del logout

        Returns:
            RedirectResponse configurada
        """
        import uuid

        # Generar session_id si no se proporciona
        if not session_id:
            session_id = str(uuid.uuid4())

        # Guardar intención
        FederatedLogoutService.set_logout_intention(
            session_id=session_id,
            reason=reason,
            redirect_after=redirect_after,
        )

        # Construir URL de post-logout con el session_id
        base = _get_base_url(request)
        post_logout_url = f"{base}/auth/post-logout?sid={session_id}"

        # Construir logout de Microsoft
        microsoft_url = FederatedLogoutService.build_microsoft_logout_url(
            request=request,
            post_logout_redirect=post_logout_url,
        )

        response = RedirectResponse(url=microsoft_url, status_code=302)

        # Limpiar todas las cookies de sesión
        cookies_to_delete = [
            "access_token",
            "student_token",
            "session",
            "_oauth_state",
        ]
        for cookie_name in cookies_to_delete:
            response.delete_cookie(key=cookie_name, path="/")

        # Headers anti-cache y de limpieza
        response.headers["Clear-Site-Data"] = '"cookies", "storage"'
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"

        logger.info(
            f"Logout iniciado - reason={reason}, session_id={session_id}"
        )

        return response

    @staticmethod
    def handle_post_logout(
        request: Request,
        session_id: Optional[str] = None,
    ) -> RedirectResponse:
        """
        Maneja el retorno después del logout federado.

        Args:
            request: Request de FastAPI
            session_id: ID de sesión para recuperar intención

        Returns:
            RedirectResponse según la intención previa
        """
        if session_id:
            intention = FederatedLogoutService.get_logout_intention(session_id)
            if intention:
                reason = intention.get("reason")
                redirect_after = intention.get("redirect_after", "/acceso-estudiante")

                logger.info(f"Post-logout - reason={reason}, redirecting to {redirect_after}")

                # Si era switch-account, redirigir automáticamente al login
                if reason == LogoutReason.SWITCH_ACCOUNT:
                    base = _get_base_url(request)
                    return RedirectResponse(
                        url=f"{base}/auth/google/login",
                        status_code=302,
                    )

                # En otros casos, ir al destino especificado
                return RedirectResponse(url=redirect_after, status_code=302)

        # Default: ir a acceso-estudiante
        return RedirectResponse(url="/acceso-estudiante", status_code=302)


class SimpleLogoutService:
    """Servicio para logout simple sin federación (para staff/admin)."""

    @staticmethod
    def create_logout_response(request: Request) -> RedirectResponse:
        """
        Crea una respuesta de logout simple para usuarios de staff.

        Args:
            request: Request de FastAPI

        Returns:
            RedirectResponse con limpieza de cookies
        """
        response = RedirectResponse(url="/login", status_code=302)

        # Limpiar cookies de staff
        cookies_to_delete = ["access_token", "session"]
        for cookie_name in cookies_to_delete:
            response.delete_cookie(key=cookie_name, path="/")

        # Headers anti-cache
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"

        return response
