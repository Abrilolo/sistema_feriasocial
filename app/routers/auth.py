#app/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config

from app.db.session import get_db
from app.models.user import User
from app.models.student import Student
from app.core.security import verify_password, create_access_token, get_current_user
from app.core.config import settings
from app.core.limiter import limiter

router = APIRouter(prefix="/auth", tags=["auth"])

# Configuración de logging
import logging
import re

logger = logging.getLogger(__name__)

# Validación SSRF: solo permitir imágenes de dominios de Google confiables
ALLOWED_PICTURE_DOMAINS = re.compile(
    r'^https://([a-z0-9]+\.)?googleusercontent\.com/',
    re.IGNORECASE
)


def validate_picture_url(url: str | None) -> str | None:
    """Valida que la URL de la imagen sea de un dominio confiable para prevenir SSRF."""
    if not url:
        return None
    if ALLOWED_PICTURE_DOMAINS.match(url):
        return url
    logger.warning(f"URL de imagen rechazada por validación SSRF: {url}")
    return None


# Configuración de OAuth para Google
oauth = OAuth()
if settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET:
    oauth.register(
        name='google',
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'openid email profile',
            'prompt': 'select_account',  # Forzar selector a nivel global (Authlib)
        }
    )


@router.post("/login")
@limiter.limit("5/minute")
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    # Swagger manda username = email, password = password
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
        )

    access_token = create_access_token({"sub": str(user.id), "role": user.role})
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/login-cookie")
@limiter.limit("5/minute")
def login_cookie(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Login que configura cookie HttpOnly segura"""
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
        )

    access_token = create_access_token({"sub": str(user.id), "role": user.role})

    from fastapi.responses import JSONResponse
    response = JSONResponse(
        content={
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": str(user.id),
                "email": user.email,
                "role": user.role,
                "organization_name": getattr(user, "organization_name", None),
            }
        }
    )

    # Configurar cookie segura (HttpOnly, Secure, SameSite=Lax)
    # Nota: Secure=True requiere HTTPS. En desarrollo local puede causar problemas.
    import os
    is_production = os.getenv("ENVIRONMENT", "development") == "production"

    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,  # No accesible desde JavaScript (protección XSS)
        secure=is_production,  # Solo HTTPS en producción
        samesite="lax",  # Protección CSRF
        max_age=60 * 60 * 24 * 7,  # 7 días
        path="/",
    )

    return response


@router.get("/logout")
@router.post("/logout")
async def nuclear_logout(request: Request):
    """
    Logout de 4 capas:
    1. Destruye sesión de Starlette (state OAuth)
    2. Borra todas las cookies del dominio
    3. Clear-Site-Data: borra cookies y localStorage del navegador
    4. Redirige a Microsoft para destruir la sesión ADFS federada

    Este es el único método que resuelve el 'silent login' de Microsoft en @tec.mx.
    """
    import urllib.parse

    # 1. Destruir sesión de Starlette
    if hasattr(request, 'session'):
        request.session.clear()

    # 2. URL base para el redirect post-logout
    if settings.APP_BASE_URL:
        base = settings.APP_BASE_URL.rstrip('/')
    else:
        base = str(request.base_url).rstrip('/')

    post_logout_uri = urllib.parse.quote(f"{base}/acceso-estudiante", safe='')

    # 3. Logout de Microsoft (destruye sesión ADFS federada con @tec.mx)
    # Esto es lo único que previene el silent login del ADFS del Tec
    microsoft_logout_url = (
        f"https://login.microsoftonline.com/common/oauth2/v2.0/logout"
        f"?post_logout_redirect_uri={post_logout_uri}"
    )

    response = RedirectResponse(url=microsoft_logout_url, status_code=302)

    # 4. Borrar todas las cookies conocidas
    cookies_to_delete = [
        "access_token", "student_token", "session", "_oauth_state",
    ]
    for cookie_name in cookies_to_delete:
        response.delete_cookie(key=cookie_name, path="/")

    # 5. Header nuclear: le dice al navegador que borre TODO (cookies + localStorage)
    response.headers["Clear-Site-Data"] = '"cookies", "storage"'
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    return response


@router.get("/logout-google")
async def logout_google_legacy(request: Request):
    """Alias del logout nuclear para compatibilidad con links existentes."""
    return await nuclear_logout(request)


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return {
        "id": str(user.id),
        "email": user.email,
        "role": user.role,
        "organization_name": getattr(user, "organization_name", None),
        "is_active": user.is_active,
    }


# =====================================================
# GOOGLE OAUTH - LOGIN PARA ESTUDIANTES
# =====================================================

@router.get("/google/login")
async def google_login(request: Request):
    """
    Redirige al usuario a Google OAuth con forzado completo de selección de cuenta.

    Arquitectura stateless:
    - El OAuth state se guarda en una cookie propia (_oauth_state) con path restringido
    - No depende del SessionMiddleware global para evitar colisiones con usuarios concurrentes
    - Construye la URL manualmente para máximo control de parámetros
    """
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth no está configurado. Contacta al administrador."
        )

    import secrets
    import hashlib
    import hmac
    import urllib.parse

    # 1. Construir redirect_uri explícito (evita http:// en proxies HTTPS de Render)
    if settings.APP_BASE_URL:
        redirect_uri = f"{settings.APP_BASE_URL.rstrip('/')}/auth/google/callback"
    else:
        redirect_uri = str(request.url_for('google_callback'))

    # 2. Generar state firmado con HMAC (stateless — no depende de SessionMiddleware)
    nonce = secrets.token_urlsafe(32)
    mac = hmac.new(
        settings.JWT_SECRET.encode(),
        nonce.encode(),
        hashlib.sha256
    ).hexdigest()
    state = f"{nonce}.{mac}"

    logger.debug(f"OAuth login iniciado. redirect_uri={redirect_uri}")

    # 3. Construir URL de Google manualmente para control total
    # prompt=select_account+consent fuerza re-autenticación incluyendo a través de ADFS
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
    auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)

    response = RedirectResponse(url=auth_url, status_code=302)

    # 4. Guardar state en cookie dedicada (path restringido al callback, 5 min de vida)
    # Esto evita colisiones de estado entre múltiples usuarios concurrentes
    is_prod = settings.ENVIRONMENT == "production"
    response.set_cookie(
        key="_oauth_state",
        value=state,
        httponly=True,
        secure=is_prod,
        samesite="lax",
        max_age=300,   # 5 minutos — solo dura el tiempo del flujo OAuth
        path="/",
    )

    # 5. Headers anti-cache
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "Thu, 01 Jan 1970 00:00:00 GMT"

    return response


@router.get("/google/callback", name="google_callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    """
    Callback de Google OAuth. Valida el state HMAC, intercambia el código por token
    y crea/sincroniza el estudiante en la base de datos.
    """
    import hashlib
    import hmac

    logger.debug(f"Callback recibido. Params: {dict(request.query_params)}")

    # 1. Verificar CSRF: comparar state de Google con la cookie _oauth_state
    state_from_google = request.query_params.get("state", "")
    state_from_cookie = request.cookies.get("_oauth_state", "")

    if not state_from_google or not state_from_cookie:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Falta el parámetro state OAuth. Intenta iniciar sesión de nuevo."
        )

    # Verificar que el state de la cookie coincida con el de Google
    if not hmac.compare_digest(state_from_google, state_from_cookie):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="State OAuth inválido. Posible ataque CSRF. Intenta de nuevo."
        )

    # Verificar firma HMAC del state (asegura que lo emitimos nosotros)
    try:
        nonce, received_mac = state_from_google.rsplit(".", 1)
        expected_mac = hmac.new(
            settings.JWT_SECRET.encode(),
            nonce.encode(),
            hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected_mac, received_mac):
            raise ValueError("HMAC inválido")
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="State OAuth corrupto. Intenta iniciar sesión de nuevo."
        )

    try:
        # 2. Intercambiar código por token con Google
        # Construir redirect_uri consistente con el login
        if settings.APP_BASE_URL:
            redirect_uri = f"{settings.APP_BASE_URL.rstrip('/')}/auth/google/callback"
        else:
            redirect_uri = str(request.url_for('google_callback'))

        import httpx
        token_response = httpx.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": request.query_params.get("code"),
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            }
        )
        token_data = token_response.json()

        if "error" in token_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Error de Google: {token_data.get('error_description', token_data['error'])}"
            )

        # 3. Obtener info del usuario del ID token
        id_token = token_data.get("id_token")
        userinfo_response = httpx.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {token_data.get('access_token')}"},
        )
        user_info = userinfo_response.json()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Error al autorizar con Google: {str(e)}"
        )

    email = user_info.get('email', '').lower()
    google_id = user_info.get('sub')
    full_name = user_info.get('name')
    picture_url = user_info.get('picture')
    
    logger.debug("Nuevo login OAuth detectado")  # No incluir PII en logs

    # Validación CRÍTICA: verificar que el email sea del dominio institucional
    if not email.endswith(f"@{settings.STUDENT_EMAIL_DOMAIN}"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Solo se permiten correos @{settings.STUDENT_EMAIL_DOMAIN}"
        )

    # Extraer matrícula del email (formato: A01234567@tec.mx -> A01234567)
    matricula = email.split('@')[0].upper()

    # UPSERT de estudiante siguiendo el estandar de Federated Identity:
    # Primero buscar por google_id (sub) - es el identificador INMUTABLE de Google
    # Fallback a email - para estudiantes creados antes de implementar OAuth
    student = db.query(Student).filter(Student.google_id == google_id).first()

    if not student:
        # Fallback: buscar por email (para migrar registros previos)
        student = db.query(Student).filter(Student.email == email).first()
        if student:
            logger.debug("Enlazando estudiante existente con google_id")  # No incluir PII

    if student:
        # Siempre sincronizar datos frescos de Google
        student.google_id = google_id
        student.email = email  # Actualizar email por si cambio
        student.full_name = full_name or student.full_name
        # Validar picture_url para prevenir SSRF
        validated_picture = validate_picture_url(picture_url)
        if validated_picture:
            student.picture_url = validated_picture
        db.commit()
    else:
        # Crear nuevo estudiante (Just-In-Time Provisioning)
        # Validar picture_url para prevenir SSRF
        validated_picture = validate_picture_url(picture_url)
        student = Student(
            email=email,
            matricula=matricula,
            full_name=full_name,
            google_id=google_id,
            picture_url=validated_picture,
        )
        db.add(student)
        db.commit()
        db.refresh(student)

    # Generar token JWT del sistema para el estudiante
    access_token = create_access_token({
        "sub": str(student.id),
        "type": "student",
        "email": student.email,
        "matricula": student.matricula,
        "name": student.full_name
    })

    # Redirigir a la página del QR con el token en cookie
    response = RedirectResponse(url="/acceso-estudiante", status_code=302)
    response.set_cookie(
        key="student_token",
        value=access_token,
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="lax",
        max_age=60 * 30,  # 30 minutos (dispositivos compartidos en la feria)
        path="/",
    )

    return response