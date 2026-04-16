# app/main.py
import logging
import os
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware
from app.core.limiter import limiter
from app.core.config import settings

from app.routers.auth import router as auth_router
from app.routers.admin import router as admin_router
from app.routers.socio import router as socio_router
from app.routers.becario import router as becario_router
from app.routers.checkins import router as checkins_router
from app.routers.public import router as public_router
from app.routers.db import router as db_router
from app.routers import views
from app.db.session import db_ping

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Detectar entorno
is_production = os.getenv("ENVIRONMENT", "development").lower() == "production"

app = FastAPI(
    title="Feria Servicio Social Tec",
    description="Sistema de gestión para la feria de servicio social",
    version="1.0.0",
    docs_url=None if is_production else "/docs",
    redoc_url=None if is_production else "/redoc",
    openapi_url=None if is_production else "/openapi.json",
)

# Attach rate limiter to state
app.state.limiter = limiter

# Rate limit exceeded handler
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"detail": "Demasiadas solicitudes. Por favor, intenta más tarde."},
    )

# Configuración de CORS - Dominios permitidos
# En producción, solo se permite el dominio oficial configurado en FRONTEND_URL
is_production = os.getenv("ENVIRONMENT", "development").lower() == "production"

if is_production:
    # En producción: solo permitir el dominio configurado explícitamente
    ALLOWED_ORIGINS = []
    production_origin = os.getenv("FRONTEND_URL")
    if production_origin:
        ALLOWED_ORIGINS.append(production_origin)

    # Añadir dominios adicionales si están configurados
    additional_origins = os.getenv("ADDITIONAL_ALLOWED_ORIGINS", "")
    if additional_origins:
        for origin in additional_origins.split(","):
            origin = origin.strip()
            if origin and origin not in ALLOWED_ORIGINS:
                ALLOWED_ORIGINS.append(origin)

    # Si no hay orígenes configurados, rechitar todas las peticiones CORS
    if not ALLOWED_ORIGINS:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning("PRODUCCIÓN: No se ha configurado FRONTEND_URL. Las peticiones CORS serán rechazadas.")
else:
    # En desarrollo: permitir localhost
    ALLOWED_ORIGINS = [
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:3000",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-CSRF-Token"],
)

# Security Headers Middleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Content Security Policy - actualizado para permitir librerías externas y scripts inline necesarios
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://unpkg.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: blob:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self';"
        )

        # HTTPS Strict Transport Security
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions Policy - permite cámara en el mismo origen
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=(self)"

        return response

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(SessionMiddleware, secret_key=settings.JWT_SECRET)

# Archivos estáticos
app.mount("/static", StaticFiles(directory="app/static"), name="static")

def validate_required_config():
    """Valida que todas las configuraciones críticas estén presentes."""
    critical_vars = {
        "GOOGLE_CLIENT_ID": settings.GOOGLE_CLIENT_ID,
        "GOOGLE_CLIENT_SECRET": settings.GOOGLE_CLIENT_SECRET,
        "JWT_SECRET": settings.JWT_SECRET,
        "DATABASE_URL": settings.DATABASE_URL,
    }

    missing = [name for name, value in critical_vars.items() if not value]

    if missing:
        logger.error("=" * 60)
        logger.error("CONFIGURACIÓN INCOMPLETA - La aplicación no puede iniciar")
        logger.error("=" * 60)
        for var in missing:
            logger.error(f"  ✗ {var} no está configurada")
        logger.error("=" * 60)
        raise RuntimeError(
            f"Variables de entorno faltantes: {', '.join(missing)}. "
            "Verifica tu archivo .env"
        )

    # Validar JWT_SECRET tiene longitud suficiente
    if len(settings.JWT_SECRET) < 32:
        logger.error("JWT_SECRET debe tener al menos 32 caracteres")
        raise RuntimeError("JWT_SECRET demasiado corto")

    # Validar APP_BASE_URL en producción
    if is_production and not settings.APP_BASE_URL:
        logger.warning(
            "APP_BASE_URL no configurado en producción. "
            "Los redirects OAuth pueden fallar."
        )

    logger.info("✓ Configuración validada correctamente")


# Evento de inicio
@app.on_event("startup")
async def startup_event():
    logger.info("Iniciando la aplicación...")

    # Validar configuración crítica
    validate_required_config()

    # Verificar conexión a BD
    if db_ping():
        logger.info("✓ Conexión a la base de datos: OK")
    else:
        logger.error("✗ Error al conectar con la base de datos")

# Manejador de errores global para SQLAlchemy
@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    logger.error(f"Error de base de datos: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Error interno en la base de datos. Por favor, intente más tarde."},
    )

# Ruta base de salud - no revelar estado interno de la BD
@app.get("/health")
def health():
    return {"status": "ok"}

# Inclusión de routers
app.include_router(views.router)
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(socio_router)
app.include_router(becario_router)
app.include_router(checkins_router)
app.include_router(public_router)
app.include_router(db_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
