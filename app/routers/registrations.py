# app/routers/registrations.py
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.db.session import get_db

from app.models.student import Student
from app.models.checkin import Checkin
from app.models.project import Project
from app.models.temp_code import TempCode
from app.models.registration import Registration

router = APIRouter(prefix="/registrations", tags=["registrations"])


class RegistrationCreateIn(BaseModel):
    matricula: str
    email: EmailStr
    temp_code: str


@router.post("", status_code=status.HTTP_201_CREATED)
def create_registration(
    payload: RegistrationCreateIn,
    db: Session = Depends(get_db),
):
    now = datetime.utcnow()

    # 1) Buscar estudiante por matrícula + email
    student = (
        db.query(Student)
        .filter(
            Student.matricula == payload.matricula.strip().upper(),
            Student.email == payload.email.strip().lower(),
        )
        .first()
    )

    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Estudiante no encontrado con esa matrícula y correo.",
        )

    # 2) Validar que ya hizo check-in
    checkin = db.query(Checkin).filter(Checkin.student_id == student.id).first()
    if not checkin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El estudiante debe hacer check-in antes de registrarse a un proyecto.",
        )

    # 3) Validar que no esté ya registrado en otro proyecto
    existing_registration_query = (
        db.query(Registration)
        .filter(Registration.student_id == student.id)
        .first()
    )

    if hasattr(Registration, "status"):
        existing_registration_query = existing_registration_query.filter(Registration.status != "CANCELLED")
    existing_registration = existing_registration_query.first()    

    if existing_registration:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El estudiante ya está registrado en un proyecto.",
        )

    # 4) Buscar código temporal
    temp_code = (
        db.query(TempCode)
        .filter(TempCode.code == payload.temp_code.strip())
        .first()
    )

    if not temp_code:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Código temporal no encontrado.",
        )

    # 5) Validar código activo
    if not temp_code.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El código temporal ya no está activo.",
        )

    # 6) Validar expiración
    if temp_code.expires_at <= now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El código temporal ya expiró.",
        )

    # 7) Validar que no se haya usado
    if temp_code.used_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El código temporal ya fue utilizado.",
        )

    # 8) Buscar proyecto del código
    project = db.query(Project).filter(Project.id == temp_code.project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El proyecto asociado al código no existe.",
        )

    if not project.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El proyecto ya no está activo.",
        )

    # 9) Validar cupo
    taken_slots = (
        db.query(Registration)
        .filter(Registration.project_id == project.id)
        .count()
    )

    if taken_slots >= project.capacity:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya no hay cupo disponible en este proyecto.",
        )

    # 10) Crear registro + marcar código como usado
    registration = Registration(
        student_id=student.id,
        project_id=project.id,
        temp_code_id=temp_code.id,
        status="CONFIRMED",
    )

    temp_code.used_at = now
    temp_code.is_active = False

    try:
        db.add(registration)
        db.commit()
        db.refresh(registration)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo completar el registro.",
        )

    return {
        "ok": True,
        "message": "Registro completado correctamente.",
        "registration_id": str(registration.id),
        "student": {
            "id": str(student.id),
            "matricula": student.matricula,
            "email": student.email,
            "full_name": student.full_name,
        },
        "project": {
            "id": str(project.id),
            "name": project.name,
            "capacity": project.capacity,
            "taken_slots": taken_slots + 1,
            "remaining_slots": project.capacity - (taken_slots + 1),
        },
        "temp_code": {
            "id": str(temp_code.id),
            "code": temp_code.code,
            "used_at": temp_code.used_at.isoformat() if temp_code.used_at else None,
        },
        "registered_at": registration.created_at.isoformat(),
    }