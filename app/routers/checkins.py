# app/routers/checkins.py
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.models.student import Student
from app.models.checkin import Checkin
from app.core.security import get_user_flex

router = APIRouter(prefix="/checkins", tags=["checkins"])


class CheckinScanIn(BaseModel):
    matricula: str  # Simplificado: solo la matrícula en texto plano


def require_roles(*allowed_roles: str):
    def _dep(user: User = Depends(get_user_flex)):
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
    payload: CheckinScanIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("BECARIO", "ADMIN")),
):
    matricula = payload.matricula.strip().upper()

    # 1. Buscar estudiante por matrícula
    student = db.query(Student).filter(Student.matricula == matricula).first()
    if not student:
        raise HTTPException(
            status_code=404,
            detail=f"No se encontró ningún estudiante con matrícula {matricula}. "
                   "Pídele que inicie sesión con su cuenta del Tec primero.",
        )

    # 2. Verificar si ya tiene check-in (idempotente: no es error, solo avisa)
    existing = db.query(Checkin).filter(Checkin.student_id == student.id).first()
    if existing:
        return {
            "ok": True,
            "already_checked_in": True,
            "message": f"✅ {student.full_name or student.matricula} ya tenía check-in registrado.",
            "student": {
                "id": str(student.id),
                "matricula": student.matricula,
                "full_name": student.full_name,
                "career": student.career,
            },
            "checked_in_at": existing.checked_in_at.isoformat(),
        }

    # 3. Crear check-in
    checkin = Checkin(
        student_id=student.id,
        becario_user_id=user.id,
        method="QR",
    )
    db.add(checkin)
    db.commit()
    db.refresh(checkin)

    return {
        "ok": True,
        "already_checked_in": False,
        "message": f"✅ Check-in registrado para {student.full_name or student.matricula}.",
        "student": {
            "id": str(student.id),
            "matricula": student.matricula,
            "full_name": student.full_name,
            "career": student.career,
        },
        "checked_in_at": checkin.checked_in_at.isoformat(),
    }