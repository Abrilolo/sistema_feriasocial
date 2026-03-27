# app/main.py
import logging
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

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

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Ajustar en producción
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
