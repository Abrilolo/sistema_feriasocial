# app/routers/auth.py
"""
Router de autenticación - Refactor empresarial Fase 3.

Flujos soportados:
- Login staff (usuario/contraseña)
- Login estudiante OAuth (Google -> Microsoft/ADFS)
- Switch account (cambio de cuenta federada)
- Logout federado completo
- Post-logout handler
"""

import logging
import re
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.auth_errors import AuthErrorCode, AuthException
from app.core.config import settings
from app.core.limiter import limiter
from app.core.security import create_access_token, get_current_user, verify_password
from app.db.session import get_db
from app.models.student import Student
from app.models.user import User
from app.services.auth_service import (
    AuthLogger,
    FederatedAuthService,
    OAuthStateService,
    StudentAuthService,
)
from app.services.federated_logout_service import (
    FederatedLogoutService,
    LogoutReason,
    SimpleLogoutService,
)
from app.services.student_session_service import StudentSessionService

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)

# ============================================================================
# Validación SSRF para URLs de imagen
# ============================================================================

ALLOWED_PICTURE_DOMAINS = re.compile(
    r"^https://([a-z0-9]+\.)?googleusercontent\.com/",
    re.IGNORECASE,
)


def validate_picture_url(url: Optional[str]) -> Optional[str]:
    """Valida URL de imagen para prevenir SSRF."""
    if not url:
        return None
    if ALLOWED_PICTURE_DOMAINS.match(url):
        return url
    logger.warning(f"URL de imagen rechazada por SSRF: {url}")
    return None


# ============================================================================
# AUTENTICACIÓN DE STAFF (Admin/Socio/Becario)
# ============================================================================


@router.post("/login")
@limiter.limit("5/minute")
def login_staff(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Login para staff (usuarios con rol ADMIN, SOCIO, BECARIO)."""
    AuthLogger.log_event(
        "AUTH_STAFF_LOGIN_ATTEMPT",
        email=form_data.username,
    )

    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        AuthLogger.log_failure(
            AuthErrorCode.INVALID_EMAIL_FORMAT,
            "Credenciales inválidas",
            email=form_data.username,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
        )

    access_token = create_access_token({"sub": str(user.id), "role": user.role})

    AuthLogger.log_event(
        "AUTH_STAFF_LOGIN_SUCCESS",
        user_id=str(user.id),
        role=user.role,
    )

    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/login-cookie")
@limiter.limit("5/minute")
def login_staff_cookie(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Login para staff con cookie HttpOnly."""
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
        )

    access_token = create_access_token({"sub": str(user.id), "role": user.role})

    response = JSONResponse(
        content={
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": str(user.id),
                "email": user.email,
                "role": user.role,
                "organization_name": getattr(user, "organization_name", None),
            },
        }
    )

    is_production = settings.ENVIRONMENT == "production"
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        secure=is_production,
        samesite="lax",
        max_age=60 * 60 * 24 * 7,
        path="/",
    )

    return response


# ============================================================================
# AUTENTICACIÓN FEDERADA - ESTUDIANTES (Google -> Microsoft/ADFS)
# ============================================================================


@router.get("/google/login")
async def google_login(request: Request):
    """
    Inicia el flujo OAuth con Google para estudiantes.

    Verifica configuración, genera state firmado, y redirige a Google.
    """
    # Validar configuración
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        logger.error("OAuth no configurado: faltan credenciales de Google")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth no está configurado. Contacta al administrador.",
        )

    # Generar state y auth_request_id
    state, auth_request_id = OAuthStateService.generate_state()

    # Construir redirect_uri consistente
    if settings.APP_BASE_URL:
        redirect_uri = f"{settings.APP_BASE_URL.rstrip('/')}/auth/google/callback"
    else:
        redirect_uri = str(request.url_for("google_callback"))

    AuthLogger.log_event(
        "AUTH_LOGIN_STARTED",
        auth_request_id=auth_request_id,
        redirect_uri=redirect_uri,
    )

    # Construir URL de Google
    auth_url = FederatedAuthService.build_google_auth_url(state, redirect_uri)

    response = RedirectResponse(url=auth_url, status_code=302)

    # Guardar state en cookie segura
    is_prod = settings.ENVIRONMENT == "production"
    response.set_cookie(
        key="_oauth_state",
        value=state,
        httponly=True,
        secure=is_prod,
        samesite="lax",
        max_age=300,
        path="/",
    )

    # Headers anti-cache
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    return response


@router.get("/google/switch-account")
async def google_switch_account(request: Request):
    """
    Flujo dedicado para cambio de cuenta.

    Limpia sesión actual y encadena logout federado antes de iniciar nuevo login.
    """
    import uuid

    session_id = str(uuid.uuid4())

    AuthLogger.log_event(
        "AUTH_SWITCH_ACCOUNT_STARTED",
        session_id=session_id,
    )

    return FederatedLogoutService.create_logout_response(
        request=request,
        reason=LogoutReason.SWITCH_ACCOUNT,
        session_id=session_id,
    )


@router.get("/google/callback", name="google_callback")
async def google_callback(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Callback de Google OAuth.

    Valida state, intercambia código, obtiene userinfo,
    crea/actualiza estudiante, y emite sesión.
    """
    # Extraer state de Google y cookie
    state_from_google = request.query_params.get("state", "")
    state_from_cookie = request.cookies.get("_oauth_state", "")
    error_from_google = request.query_params.get("error")

    # Manejar errores de Google
    if error_from_google:
        logger.warning(f"Error de Google OAuth: {error_from_google}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Autenticación cancelada o rechazada: {error_from_google}",
        )

    # Validar state y obtener auth_request_id
    try:
        auth_request_id = OAuthStateService.validate_state(
            state_from_google, state_from_cookie
        )
    except AuthException as e:
        AuthLogger.log_failure(
            e.code,
            e.message,
            details=e.details,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.to_client_response()["message"],
        )

    # Marcar state como consumido (single-use)
    OAuthStateService.consume_state(state_from_google, auth_request_id)

    AuthLogger.log_event(
        "AUTH_CALLBACK_RECEIVED",
        auth_request_id=auth_request_id,
    )

    # Construir redirect_uri consistente
    if settings.APP_BASE_URL:
        redirect_uri = f"{settings.APP_BASE_URL.rstrip('/')}/auth/google/callback"
    else:
        redirect_uri = str(request.url_for("google_callback"))

    # Intercambiar código por token
    try:
        code = request.query_params.get("code")
        if not code:
            raise AuthException(
                AuthErrorCode.GOOGLE_CODE_EXCHANGE_FAILED,
                "No se recibió código de autorización",
                auth_request_id=auth_request_id,
            )

        token_data = FederatedAuthService.exchange_code_for_token(code, redirect_uri)
        access_token = token_data.get("access_token")

        AuthLogger.log_event(
            "AUTH_TOKEN_EXCHANGED",
            auth_request_id=auth_request_id,
        )

    except AuthException as e:
        AuthLogger.log_failure(
            e.code,
            e.message,
            auth_request_id=auth_request_id,
            details=e.details,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No pudimos validar tu inicio de sesión. Intenta de nuevo.",
        )

    # Obtener información del usuario
    try:
        user_info = FederatedAuthService.get_userinfo(access_token)
    except AuthException as e:
        AuthLogger.log_failure(
            e.code,
            e.message,
            auth_request_id=auth_request_id,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No pudimos obtener tu información. Intenta de nuevo.",
        )

    email = user_info.get("email", "").lower()
    google_id = user_info.get("sub")
    full_name = user_info.get("name")
    picture_url = validate_picture_url(user_info.get("picture"))

    AuthLogger.log_event(
        "AUTH_USERINFO_RECEIVED",
        auth_request_id=auth_request_id,
        email_domain=email.split("@")[-1] if "@" in email else None,
    )

    # Validar dominio institucional
    try:
        StudentAuthService.validate_email_domain(email, auth_request_id)
    except AuthException as e:
        AuthLogger.log_failure(
            e.code,
            e.message,
            auth_request_id=auth_request_id,
            details=e.details,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo se permiten cuentas institucionales del Tec (@tec.mx).",
        )

    # Verificar que el estudiante haya hecho pre-registro
    try:
        StudentAuthService.require_preregistration(
            db=db,
            email=email,
            auth_request_id=auth_request_id,
        )
    except AuthException as e:
        AuthLogger.log_failure(
            e.code,
            e.message,
            auth_request_id=auth_request_id,
        )
        return RedirectResponse(
            url="/preregistro?error=prereg_required",
            status_code=302,
        )

    # Upsert atómico del estudiante
    try:
        student = StudentAuthService.upsert_student(
            db=db,
            google_id=google_id,
            email=email,
            full_name=full_name,
            picture_url=picture_url,
            auth_request_id=auth_request_id,
        )

        AuthLogger.log_event(
            "AUTH_STUDENT_UPSERTED",
            auth_request_id=auth_request_id,
            student_id=str(student.id),
        )

        # Integrar datos de pre-registro si existen
        StudentAuthService.integrate_preregistration(
            db=db,
            student=student,
            auth_request_id=auth_request_id,
        )

    except AuthException as e:
        AuthLogger.log_failure(
            e.code,
            e.message,
            auth_request_id=auth_request_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al registrar tu cuenta. Contacta a soporte.",
        )

    # Generar sesión JWT
    try:
        student_token = StudentSessionService.create_student_token(student)

        AuthLogger.log_event(
            "AUTH_SESSION_ISSUED",
            auth_request_id=auth_request_id,
            student_id=str(student.id),
        )

    except Exception as e:
        logger.error(f"Error al crear sesión: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al crear tu sesión. Intenta de nuevo.",
        )

    # Redirigir con cookie de sesión
    response = RedirectResponse(url="/acceso-estudiante", status_code=302)

    # Limpiar cookie de state OAuth
    response.delete_cookie(key="_oauth_state", path="/")

    # Establecer cookie de estudiante
    StudentSessionService.set_student_cookie(response, student_token)

    return response


# ============================================================================
# LOGOUT Y POST-LOGOUT
# ============================================================================


@router.get("/logout")
@router.post("/logout")
async def logout(request: Request):
    """
    Logout completo para estudiantes con federación Microsoft.

    Limpia cookies locales y redirige al logout federado.
    """
    return FederatedLogoutService.create_logout_response(
        request=request,
        reason=LogoutReason.SIMPLE_LOGOUT,
    )


@router.get("/post-logout")
async def post_logout(
    request: Request,
    sid: Optional[str] = None,
):
    """
    Handler para retorno después del logout federado.

    Recupera intención y redirige según corresponda.
    """
    return FederatedLogoutService.handle_post_logout(request, session_id=sid)


@router.get("/logout-staff")
async def logout_staff(request: Request):
    """Logout simple para usuarios de staff (sin federación)."""
    return SimpleLogoutService.create_logout_response(request)


# ============================================================================
# INFORMACIÓN DE SESIÓN
# ============================================================================


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    """Información del usuario staff autenticado."""
    return {
        "id": str(user.id),
        "email": user.email,
        "role": user.role,
        "organization_name": getattr(user, "organization_name", None),
        "is_active": user.is_active,
    }


@router.get("/session")
async def get_session_info(request: Request):
    """
    Información de la sesión actual del estudiante.

    Usado por el frontend para mostrar identidad actual y opciones.
    """
    session_info = StudentSessionService.get_session_info(request)

    if session_info:
        return {
            "authenticated": True,
            "student": {
                "id": session_info.get("student_id"),
                "email": session_info.get("email"),
                "matricula": session_info.get("matricula"),
                "name": session_info.get("name"),
            },
        }

    return {
        "authenticated": False,
        "student": None,
    }
