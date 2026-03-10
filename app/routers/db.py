from fastapi import APIRouter
from app.db.session import db_ping

router = APIRouter(tags=["default"])

@router.get("/db/ping")
def ping_db():
    ok = db_ping()
    return {"db_ok": ok}