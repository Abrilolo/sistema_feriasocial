# app/db/session.py
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings


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
    pool_pre_ping=True,
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
        print(f"Database ping failed: {e}")
        return False
    finally:
        db.close()