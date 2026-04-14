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
def logout(request: Request):
    """
    Logout completo: limpia tokens de admin, estudiante y sesión.
    Agrega headers anti-cache para evitar que el navegador mantenga sesión.
    """
    # Limpiar sesión primero
    request.session.clear()

    # Crear respuesta con redirección
    response = RedirectResponse(url="/acceso-estudiante", status_code=302)

    # Eliminar todas las cookies de sesión
    response.delete_cookie(key="access_token", path="/")
    response.delete_cookie(key="student_token", path="/")
    response.delete_cookie(key="session", path="/")

    # Headers anti-cache CRÍTICOS para dispositivos compartidos
    # Evitan que el navegador muestre la página anterior desde caché
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    return response


@router.get("/logout-google")
def logout_google_complete(request: Request):
    """
    Logout TOTAL: limpia todo localmente Y redirige a Google para cerrar sesión allí.
    USO: Cuando un estudiante quiere asegurarse de que el siguiente usuario no vea su cuenta.
    """
    import urllib.parse

    # Limpiar todo localmente primero
    request.session.clear()

    # Redirigir al logout de Google
    # Google desconectará la cuenta y luego volverá a nuestra página
    frontend_return = urllib.parse.quote("/acceso-estudiante", safe='')

    response = RedirectResponse(
        url=f"https://accounts.google.com/Logout?continue={frontend_return}",
        status_code=302
    )

    # Limpiar cookies locales también
    response.delete_cookie(key="access_token", path="/")
    response.delete_cookie(key="student_token", path="/")
    response.delete_cookie(key="session", path="/")

    return response


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
    Redirige al usuario a la página de login de Google.
    El flujo OAuth2 permite autenticación segura sin compartir contraseñas.
    """
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth no está configurado. Contacta al administrador."
        )

    # 1. Limpiar sesión previa
    request.session.clear()

    redirect_uri = request.url_for('google_callback')
    
    # Generamos la respuesta de redirección a Google
    google_redirect = await oauth.google.authorize_redirect(
        request,
        str(redirect_uri),
    )

    # 2. Añadir headers anti-cache para evitar que el navegador reuse la redirección anterior
    from fastapi.responses import RedirectResponse as RR
    response = RR(url=google_redirect.headers['location'], status_code=302)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    
    # Copiar cookies de sesión (para el state de Authlib) a la nueva respuesta
    for key, value in google_redirect.headers.items():
        if key.lower() == 'set-cookie':
            response.raw_headers.append((b'set-cookie', value.encode()))

    return response


@router.get("/google/callback", name="google_callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    """
    Callback de Google OAuth. Recibe el token de acceso, valida el usuario
    y crea/sincroniza el estudiante en la base de datos.
    """
    # DEBUG: Log de la URL completa recibida para verificar parámetros
    print(f"DEBUG: Callback URL -> {request.url}")
    print(f"DEBUG: Query params -> {dict(request.query_params)}")

    try:
        # Obtener token de acceso de Google
        token = await oauth.google.authorize_access_token(request)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Error al autorizar con Google: {str(e)}"
        )

    # Obtener información del usuario desde Google
    user_info = token.get('userinfo')
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No se pudo obtener información del usuario de Google"
        )

    email = user_info.get('email', '').lower()
    google_id = user_info.get('sub')
    full_name = user_info.get('name')
    picture_url = user_info.get('picture')
    
    print("\n" + "="*50)
    print(f"DEBUG: NUEVO LOGIN DETECTADO -> {email}")
    print("="*50 + "\n")

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
            print(f"DEBUG: Enlazando estudiante existente ({email}) con google_id")

    if student:
        # Siempre sincronizar datos frescos de Google
        student.google_id = google_id
        student.email = email  # Actualizar email por si cambio
        student.full_name = full_name or student.full_name
        student.picture_url = picture_url or student.picture_url
        db.commit()
    else:
        # Crear nuevo estudiante (Just-In-Time Provisioning)
        student = Student(
            email=email,
            matricula=matricula,
            full_name=full_name,
            google_id=google_id,
            picture_url=picture_url,
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
        max_age=60 * 60 * 2,  # 2 horas
        path="/",
    )

    return response