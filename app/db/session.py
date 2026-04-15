# app/db/session.py
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

logger = logging.getLogger(__name__)


def _pick_database_url() -> str:
    # Si quieres probar sin depender de Supabase, pon USE_LOCAL_DB=1 en .env
    if settings.USE_LOCAL_DB == 1:
        return settings.LOCAL_DATABASE_URL
    return settings.DATABASE_URL


DATABASE_URL = _pick_database_url()

# Para Supabase normalmente necesitas SSL
connect_args = {}
if "supabase.co" in DATABASE_URL and "sslmode=" not in DATABASE_URL:
    connect_args = {"sslmode": "require"}

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,      # Verifica que la conexión esté viva antes de usar
    pool_size=20,            # Conexiones base en el pool (soporta alta concurrencia)
    max_overflow=30,         # Conexiones adicionales bajo demanda (picos de 500 alumnos)
    pool_timeout=30,         # Segundos máx de espera por conexión disponible
    pool_recycle=1800,       # Reciclar conexiones cada 30 min (evita timeouts de Supabase)
    connect_args=connect_args,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def db_ping() -> bool:
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database ping failed: {e}")
        return False
    finally:
        db.close()