# app/routers/checkins.py
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.student import Student
from app.models.checkin import Checkin

from app.core.security import get_current_user, decode_access_token

router = APIRouter(prefix="/checkins", tags=["checkins"])


class CheckinQRIn(BaseModel):
    qr_token: str
    method: str | None = "QR"


def require_roles(*allowed_roles: str):
    def _dep(user=Depends(get_current_user)):
        role = getattr(user, "role", None)
        if role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para esta acción.",
            )
        return user
    return _dep


@router.post("/scan", status_code=201)
def scan_qr(
    payload: CheckinQRIn,
    db: Session = Depends(get_db),
    user=Depends(require_roles("BECARIO", "ADMIN")),
):

    # 1️⃣ decodificar QR token
    try:
        data = decode_access_token(payload.qr_token)
    except Exception:
        raise HTTPException(
            status_code=401,
            detail="QR inválido o expirado",
        )

    if data.get("type") != "invite":
        raise HTTPException(
            status_code=400,
            detail="Este QR no es de invitación",
        )

    student_id = data.get("sub")
    if not student_id:
        raise HTTPException(
            status_code=400,
            detail="QR sin student_id",
        )

    # 2️⃣ buscar estudiante
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(
            status_code=404,
            detail="Estudiante no encontrado",
        )

    # 3️⃣ revisar si ya tiene checkin
    existing = db.query(Checkin).filter(Checkin.student_id == student.id).first()

    if existing:
        return {
            "ok": True,
            "message": "El estudiante ya tenía check-in.",
            "student_id": str(student.id),
            "matricula": student.matricula,
            "checked_in_at": existing.checked_in_at.isoformat(),
        }

    # 4️⃣ crear checkin
    checkin = Checkin(
        student_id=student.id,
        becario_user_id=user.id,
        method=payload.method,
    )

    db.add(checkin)
    db.commit()
    db.refresh(checkin)

    return {
        "ok": True,
        "message": "Check-in registrado.",
        "student_id": str(student.id),
        "matricula": student.matricula,
        "checked_in_at": checkin.checked_in_at.isoformat(),
    }