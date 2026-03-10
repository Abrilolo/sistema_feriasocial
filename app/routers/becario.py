from fastapi import APIRouter, Depends
from app.core.security import require_role

router = APIRouter(prefix="/becario", tags=["becario"])

@router.get("/ping")
def becario_ping(_=Depends(require_role("BECARIO"))):
    return {"ok": True, "role_required": "BECARIO"}