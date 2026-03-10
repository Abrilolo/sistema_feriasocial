from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.student import Student
from app.models.checkin import Checkin
from app.models.temp_code import TempCode
from app.models.project import Project
from app.models.registration import Registration

router = APIRouter(prefix="/public", tags=["public"])


class RegisterProjectRequest(BaseModel):
    matricula: str
    email: EmailStr
    temp_code: str


@router.get("/ping")
def public_ping():
    return {"ok": True, "message": "public router working"}


@router.post("/register", status_code=201)
def register_project(
    payload: RegisterProjectRequest,
    db: Session = Depends(get_db),
):
    matricula = payload.matricula.strip()
    email = payload.email.strip().lower()
    temp_code_value = payload.temp_code.strip().upper()

    # 1) Buscar estudiante
    student = db.query(Student).filter(Student.matricula == matricula).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Estudiante no encontrado.",
        )

    # 2) Validar correo
    if student.email.lower() != email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El correo no coincide con la matrícula registrada.",
        )

    # 3) Verificar check-in
    checkin = db.query(Checkin).filter(Checkin.student_id == student.id).first()
    if not checkin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Debes hacer check-in en la entrada antes de registrar proyectos.",
        )

    # 4) Verificar que no tenga ya un registro
    existing_registration = (
        db.query(Registration)
        .filter(Registration.student_id == student.id)
        .first()
    )
    if existing_registration:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El estudiante ya está registrado en un proyecto.",
        )

    # 5) Buscar código temporal
    temp_code = (
        db.query(TempCode)
        .filter(TempCode.code == temp_code_value)
        .first()
    )
    if not temp_code:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Código temporal inválido.",
        )

    # 6) Validar que esté activo
    if not temp_code.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El código temporal ya no está activo.",
        )

    # 7) Validar que no haya sido usado
    if temp_code.used_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El código temporal ya fue utilizado.",
        )

    # 8) Validar expiración
    now = datetime.now(timezone.utc)
    expires_at = temp_code.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at < now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El código temporal ya expiró.",
        )

    # 9) Obtener proyecto
    project = db.query(Project).filter(Project.id == temp_code.project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proyecto no encontrado.",
        )

    # 10) Validar que proyecto siga activo
    if not project.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El proyecto no está activo.",
        )

    # 11) Validar cupo contando registros actuales
    current_registrations = (
        db.query(Registration)
        .filter(Registration.project_id == project.id)
        .count()
    )

    if current_registrations >= project.capacity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El proyecto ya no tiene cupo disponible.",
        )

    # 12) Crear registro
    registration = Registration(
        student_id=student.id,
        project_id=project.id,
        temp_code_id=temp_code.id,
        status="CONFIRMED",
        created_at=datetime.utcnow(),
    )
    db.add(registration)

    # 13) Marcar código como usado e inactivo
    temp_code.used_at = datetime.utcnow()
    temp_code.is_active = False

    db.commit()
    db.refresh(registration)

    return {
        "ok": True,
        "message": "Registro exitoso.",
        "student_id": str(student.id),
        "project_id": str(project.id),
        "registration_id": str(registration.id),
    }