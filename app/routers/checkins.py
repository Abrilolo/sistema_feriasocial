# app/routers/checkins.py
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.models.student import Student
from app.models.checkin import Checkin
from app.models.qr_token import QRToken
from app.core.security import get_user_flex

router = APIRouter(prefix="/checkins", tags=["checkins"])


class CheckinScanIn(BaseModel):
    token: str  # UUID opaco del QR — sin matrícula ni PII


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
    """
    FASE 3: Escaneo de QR con token opaco.

    Seguridad:
    - El payload NO contiene matrícula ni datos personales.
    - El servidor busca el token en BD y verifica que no esté usado ni expirado.
    - El token se invalida inmediatamente tras el primer escaneo (un solo uso).
    - Sin acceso a la BD, el QR no puede ser falsificado ni reutilizado.
    """
    token_value = payload.token.strip()

    # 1. Buscar el QR token en BD
    qr = db.query(QRToken).filter(QRToken.token == token_value).first()

    if not qr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="QR no reconocido. Pide al estudiante que genere uno nuevo.",
        )

    # 2. Verificar que no haya sido ya escaneado (un solo uso)
    if qr.used_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este QR ya fue escaneado. El estudiante debe generar uno nuevo.",
        )

    # 3. Verificar que no haya expirado
    now = datetime.now(timezone.utc)
    expires = qr.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)

    if expires < now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este QR ha expirado. El estudiante debe generar uno nuevo.",
        )

    # 4. Obtener el estudiante vinculado al token
    student = db.query(Student).filter(Student.id == qr.student_id).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Estudiante no encontrado en la base de datos.",
        )

    # 5. Verificar si ya tiene check-in (idempotente — no es error, solo avisa)
    existing = db.query(Checkin).filter(Checkin.student_id == student.id).first()
    if existing:
        # Invalidar el token igual para que no sea reutilizable
        qr.used_at = datetime.utcnow()
        db.commit()
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

    # 6. Crear check-in e invalidar el token en una sola transacción
    checkin = Checkin(
        student_id=student.id,
        becario_user_id=user.id,
        method="QR",
    )
    db.add(checkin)

    # Invalidar el token — un solo uso
    qr.used_at = datetime.utcnow()

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
