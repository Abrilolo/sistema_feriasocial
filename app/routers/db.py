from fastapi import APIRouter, Depends
from app.db.session import db_ping
from app.core.security import require_role

router = APIRouter(tags=["default"])

@router.get("/db/ping")
def ping_db(_=Depends(require_role("ADMIN"))):
    """Verifica conectividad con la BD. Solo accesible para ADMIN."""
    ok = db_ping()
    return {"db_ok": ok}