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
from app.core.limiter import limiter

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

app = FastAPI(
    title="Feria Servicio Social Tec",
    description="Sistema de gestión para la feria de servicio social",
    version="1.0.0"
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
ALLOWED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:3000",
]

# Añadir dominio de producción desde variable de entorno si existe
production_origin = os.getenv("FRONTEND_URL")
if production_origin:
    ALLOWED_ORIGINS.append(production_origin)

# Añadir dominios adicionales desde variable de entorno (comma-separated)
additional_origins = os.getenv("ADDITIONAL_ALLOWED_ORIGINS", "")
if additional_origins:
    for origin in additional_origins.split(","):
        origin = origin.strip()
        if origin and origin not in ALLOWED_ORIGINS:
            ALLOWED_ORIGINS.append(origin)

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

        # Content Security Policy - estricto, no inline scripts
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-eval' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
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

        # Permissions Policy
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        return response

app.add_middleware(SecurityHeadersMiddleware)

# Archivos estáticos
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Evento de inicio
@app.on_event("startup")
async def startup_event():
    logger.info("Iniciando la aplicación...")
    if db_ping():
        logger.info("Conexión a la base de datos: OK")
    else:
        logger.error("Error al conectar con la base de datos")

# Manejador de errores global para SQLAlchemy
@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    logger.error(f"Error de base de datos: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Error interno en la base de datos. Por favor, intente más tarde."},
    )

# Ruta base de salud
@app.get("/health")
def health():
    return {"status": "healthy", "db": db_ping()}

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
