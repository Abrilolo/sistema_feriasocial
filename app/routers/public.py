from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.limiter import limiter
from app.models.student import Student
from app.models.checkin import Checkin
from app.models.temp_code import TempCode
from app.models.project import Project
from app.models.user import User
from app.models.registration import Registration
from app.models.qr_token import QRToken
from app.core.security import get_current_student

router = APIRouter(prefix="/public", tags=["public"])


class RegisterProjectRequest(BaseModel):
    temp_code: str | None = None
    codigo: str | None = None


class GenerateQRRequest(BaseModel):
    career: str | None = None


@router.get("/ping")
def public_ping():
    return {"ok": True, "message": "public router working"}


@router.post("/register", status_code=201)
@limiter.limit("5/minute")
def register_project(
    request: Request,
    payload: RegisterProjectRequest,
    db: Session = Depends(get_db),
    student: Student = Depends(get_current_student),
):
    temp_code_value = (payload.temp_code or payload.codigo or "").strip().upper()

    # 1) Verificar check-in — flujo obligatorio de la feria
    checkin = db.query(Checkin).filter(Checkin.student_id == student.id).first()
    if not checkin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Debes presentar tu código QR al staff de la entrada para hacer "
                "check-in antes de registrarte en un proyecto."
            ),
        )

    # 2) Verificar que no tenga ya un registro
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

    # 3) Buscar código temporal
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

    # 4) Validaciones del código
    if not temp_code.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El código temporal ya no está activo.",
        )

    if temp_code.used_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El código temporal ya fue utilizado.",
        )

    now = datetime.now(timezone.utc)
    expires_at = temp_code.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at < now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El código temporal ya expiró.",
        )

    # 5) Obtener proyecto
    project = db.query(Project).filter(Project.id == temp_code.project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proyecto no encontrado.",
        )

    if not project.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El proyecto no está activo.",
        )

    # 6) Validar cupo
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

    # 7) Crear registro y marcar código
    registration = Registration(
        student_id=student.id,
        project_id=project.id,
        temp_code_id=temp_code.id,
        status="CONFIRMED",
        created_at=datetime.utcnow(),
    )
    db.add(registration)

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


@router.post("/generate-qr")
@limiter.limit("10/minute")
def generate_qr_token(
    request: Request,
    payload: GenerateQRRequest,
    db: Session = Depends(get_db),
    student: Student = Depends(get_current_student),
):
    """
    FASE 3: Genera un QR con UUID opaco de un solo uso.

    Seguridad:
    - El QR NO contiene la matrícula ni ningún dato personal (PII).
    - El token UUID es generado en el servidor y guardado en BD.
    - Caduca en 2 horas y se invalida tras el primer escaneo.
    - No puede ser falsificado sin acceso a la BD.
    """
    # Guardar carrera si viene en el payload
    if payload.career:
        student.career = payload.career.strip().upper()
        db.commit()

    # Invalidar QR tokens anteriores del mismo estudiante (no usados)
    # Así solo hay un QR válido por estudiante a la vez
    db.query(QRToken).filter(
        QRToken.student_id == student.id,
        QRToken.used_at.is_(None),
    ).delete(synchronize_session=False)
    db.commit()

    # Crear nuevo token opaco
    qr = QRToken(
        token=QRToken.generate_token(),     # UUID v4 aleatorio
        student_id=student.id,
        expires_at=QRToken.get_default_expiry(),
    )
    db.add(qr)
    db.commit()
    db.refresh(qr)

    return {
        "ok": True,
        "qr_data": qr.token,   # UUID opaco — sin PII
        "expires_at": qr.expires_at.isoformat(),
        "student": {
            "matricula": student.matricula,
            "full_name": student.full_name,
            "career": student.career,
        },
    }


@router.get("/projects")
def get_projects(
    db: Session = Depends(get_db),
    student: Student = Depends(get_current_student),  # Requiere sesión activa
):
    """
    Lista proyectos activos. Requiere student_token para no exponer datos públicamente.
    """
    query = (
        db.query(Project, User)
        .join(User, Project.owner_user_id == User.id)
        .filter(Project.is_active == True)
    )
    results = query.all()

    output = []
    for p, u in results:
        current_regs = db.query(Registration).filter(Registration.project_id == p.id).count()
        available = max(0, p.capacity - current_regs)

        output.append({
            "id": str(p.id),
            "name": p.name,
            "description": p.description,
            "organization": u.organization_name or "Socio Formador",
            "image_url": f"/static/img/projects/{p.image_filename}" if p.image_filename else None,
            "capacity": p.capacity,
            "available": available,
            "periodo": p.periodo,
            "carreras": p.carreras_permitidas,
            "modalidad": p.modalidad,
            "horas": p.horas_acreditar,
            "clave": p.clave_programa or "N/A",
        })

    return output
