from datetime import datetime
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.core.security import require_role, hash_password
from app.db.session import get_db

from app.models.user import User
from app.models.student import Student
from app.models.project import Project
from app.models.checkin import Checkin
from app.models.registration import Registration
from app.models.temp_code import TempCode

router = APIRouter(prefix="/admin", tags=["admin"])


class AdminStudentCreateIn(BaseModel):
    matricula: str = Field(min_length=1, max_length=50)
    email: EmailStr
    full_name: str | None = None
    auto_checkin: bool = False


class AdminUserCreateIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=72)
    role: str


class AdminProjectCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    capacity: int = Field(gt=0)
    owner_user_id: str
    periodo: str | None = None
    carreras_permitidas: str | None = None
    objetivo: str | None = None
    actividades: str | None = None
    horario: str | None = None
    competencias_requeridas: str | None = None
    modalidad: str | None = None
    lugar_trabajo: str | None = None
    duracion: str | None = None
    poblacion_atendida: str | None = None
    horas_acreditar: str | None = None
    comentarios_adicionales: str | None = None
    clave_programa: str | None = None

class AdminProjectUpdateIn(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    capacity: int | None = Field(None, gt=0)
    owner_user_id: str | None = None
    periodo: str | None = None
    carreras_permitidas: str | None = None
    objetivo: str | None = None
    actividades: str | None = None
    horario: str | None = None
    competencias_requeridas: str | None = None
    modalidad: str | None = None
    lugar_trabajo: str | None = None
    duracion: str | None = None
    poblacion_atendida: str | None = None
    horas_acreditar: str | None = None
    comentarios_adicionales: str | None = None
    clave_programa: str | None = None

@router.get("/ping")
def admin_ping(_=Depends(require_role("ADMIN"))):
    return {"ok": True, "role_required": "ADMIN"}


@router.get("/metrics")
def admin_metrics(
    db: Session = Depends(get_db),
    _=Depends(require_role("ADMIN")),
):
    now = datetime.utcnow()

    total_users = db.query(User).count()
    total_admins = db.query(User).filter(User.role == "ADMIN").count()
    total_socios = db.query(User).filter(User.role == "SOCIO").count()
    total_becarios = db.query(User).filter(User.role == "BECARIO").count()

    total_students = db.query(Student).count()

    total_projects = db.query(Project).count()
    active_projects = db.query(Project).filter(Project.is_active == True).count()

    total_checkins = db.query(Checkin).count()

    total_registrations_query = db.query(Registration)
    if hasattr(Registration, "status"):
        total_registrations_query = total_registrations_query.filter(
            Registration.status != "CANCELLED"
        )
    total_registrations = total_registrations_query.count()

    active_codes = (
        db.query(TempCode)
        .filter(
            TempCode.is_active == True,
            TempCode.used_at.is_(None),
            TempCode.expires_at > now,
        )
        .count()
    )

    used_codes = db.query(TempCode).filter(TempCode.used_at.is_not(None)).count()

    expired_codes = (
        db.query(TempCode)
        .filter(
            TempCode.used_at.is_(None),
            TempCode.expires_at <= now,
        )
        .count()
    )

    projects = db.query(Project).all()

    project_occupancy = []
    full_projects = 0

    for project in projects:
        taken_slots_query = (
            db.query(Registration)
            .filter(Registration.project_id == project.id)
        )

        if hasattr(Registration, "status"):
            taken_slots_query = taken_slots_query.filter(
                Registration.status != "CANCELLED"
            )

        taken_slots = taken_slots_query.count()
        remaining_slots = max(project.capacity - taken_slots, 0)

        if project.capacity > 0 and taken_slots >= project.capacity:
            full_projects += 1

        occupancy_percent = 0
        if project.capacity > 0:
            occupancy_percent = round((taken_slots / project.capacity) * 100, 2)

        project_occupancy.append(
            {
                "project_id": str(project.id),
                "name": project.name,
                "capacity": project.capacity,
                "taken_slots": taken_slots,
                "remaining_slots": remaining_slots,
                "occupancy_percent": occupancy_percent,
                "is_active": project.is_active,
            }
        )

    return {
        "ok": True,
        "metrics": {
            "users": {
                "total": total_users,
                "admins": total_admins,
                "socios": total_socios,
                "becarios": total_becarios,
            },
            "students": {
                "total": total_students,
            },
            "projects": {
                "total": total_projects,
                "active": active_projects,
                "full": full_projects,
            },
            "operations": {
                "checkins": total_checkins,
                "registrations": total_registrations,
            },
            "temp_codes": {
                "active": active_codes,
                "used": used_codes,
                "expired": expired_codes,
            },
        },
        "project_occupancy": project_occupancy,
    }


@router.post("/users", status_code=status.HTTP_201_CREATED)
def create_user(
    payload: AdminUserCreateIn,
    db: Session = Depends(get_db),
    _=Depends(require_role("ADMIN")),
):
    role = payload.role.strip().upper()

    if role not in {"ADMIN", "SOCIO", "BECARIO"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rol inválido. Usa ADMIN, SOCIO o BECARIO.",
        )

    email = payload.email.strip().lower()

    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un usuario con ese correo.",
        )

    user = User(
        email=email,
        hashed_password=hash_password(payload.password),
        role=role,
        is_active=True,
    )

    try:
        db.add(user)
        db.commit()
        db.refresh(user)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo crear el usuario.",
        )

    return {
        "ok": True,
        "message": "Usuario creado correctamente.",
        "user": {
            "id": str(user.id),
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active,
        },
    }

@router.get("/users")
def list_all_users(
    db: Session = Depends(get_db),
    _=Depends(require_role("ADMIN")),
):
    users = db.query(User).order_by(User.created_at.desc()).all()
    results = [
        {
            "id": str(u.id),
            "email": u.email,
            "role": u.role,
            "is_active": u.is_active,
            "organization_name": getattr(u, "organization_name", None)
        } for u in users
    ]
    return {
        "ok": True,
        "users": results
    }


@router.post("/projects", status_code=status.HTTP_201_CREATED)
def create_project(
    payload: AdminProjectCreateIn,
    db: Session = Depends(get_db),
    _=Depends(require_role("ADMIN")),
):
    owner = db.query(User).filter(User.id == payload.owner_user_id).first()

    if not owner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El owner_user_id no corresponde a ningún usuario.",
        )

    if owner.role not in {"SOCIO", "ADMIN"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El owner del proyecto debe tener rol SOCIO o ADMIN.",
        )

    existing = (
        db.query(Project)
        .filter(
            Project.name == payload.name.strip(),
            Project.owner_user_id == owner.id,
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un proyecto con ese nombre para ese owner.",
        )

    project = Project(
        name=payload.name.strip(),
        description=(payload.description or "").strip() or None,
        capacity=payload.capacity,
        owner_user_id=owner.id,
        is_active=True,
        periodo=payload.periodo.strip() if payload.periodo else None,
        carreras_permitidas=payload.carreras_permitidas.strip() if payload.carreras_permitidas else None,
        objetivo=payload.objetivo.strip() if payload.objetivo else None,
        actividades=payload.actividades.strip() if payload.actividades else None,
        horario=payload.horario.strip() if payload.horario else None,
        competencias_requeridas=payload.competencias_requeridas.strip() if payload.competencias_requeridas else None,
        modalidad=payload.modalidad.strip() if payload.modalidad else None,
        lugar_trabajo=payload.lugar_trabajo.strip() if payload.lugar_trabajo else None,
        duracion=payload.duracion.strip() if payload.duracion else None,
        poblacion_atendida=payload.poblacion_atendida.strip() if payload.poblacion_atendida else None,
        horas_acreditar=payload.horas_acreditar.strip() if payload.horas_acreditar else None,
        comentarios_adicionales=payload.comentarios_adicionales.strip() if payload.comentarios_adicionales else None,
    )

    try:
        db.add(project)
        db.commit()
        db.refresh(project)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo crear el proyecto.",
        )

    return {
        "ok": True,
        "message": "Proyecto creado correctamente.",
        "project": {
            "id": str(project.id),
            "name": project.name,
            "description": project.description,
            "capacity": project.capacity,
            "owner_user_id": str(project.owner_user_id),
            "is_active": project.is_active,
        },
    }


@router.get("/projects")
def list_all_projects(
    db: Session = Depends(get_db),
    _=Depends(require_role("ADMIN")),
):
    projects = db.query(Project).order_by(Project.created_at.desc()).all()

    results = []

    for project in projects:
        owner = db.query(User).filter(User.id == project.owner_user_id).first()

        taken_slots_query = (
            db.query(Registration)
            .filter(Registration.project_id == project.id)
        )

        if hasattr(Registration, "status"):
            taken_slots_query = taken_slots_query.filter(
                Registration.status != "CANCELLED"
            )

        taken_slots = taken_slots_query.count()
        remaining_slots = max(project.capacity - taken_slots, 0)

        occupancy_percent = 0
        if project.capacity > 0:
            occupancy_percent = round((taken_slots / project.capacity) * 100, 2)

        results.append(
            {
                "id": str(project.id),
                "name": project.name,
                "description": project.description,
                "capacity": project.capacity,
                "taken_slots": taken_slots,
                "remaining_slots": remaining_slots,
                "occupancy_percent": occupancy_percent,
                "is_active": project.is_active,
                "created_at": project.created_at.isoformat(),
                "periodo": getattr(project, "periodo", None),
                "carreras_permitidas": getattr(project, "carreras_permitidas", None),
                "objetivo": getattr(project, "objetivo", None),
                "actividades": getattr(project, "actividades", None),
                "horario": getattr(project, "horario", None),
                "competencias_requeridas": getattr(project, "competencias_requeridas", None),
                "modalidad": getattr(project, "modalidad", None),
                "lugar_trabajo": getattr(project, "lugar_trabajo", None),
                "duracion": getattr(project, "duracion", None),
                "poblacion_atendida": getattr(project, "poblacion_atendida", None),
                "horas_acreditar": getattr(project, "horas_acreditar", None),
                "comentarios_adicionales": getattr(project, "comentarios_adicionales", None),
                "clave_programa": getattr(project, "clave_programa", None),
                "owner": {
                    "id": str(owner.id) if owner else None,
                    "email": owner.email if owner else None,
                    "role": owner.role if owner else None,
                },
            }
        )

    return {
        "ok": True,
        "count": len(results),
        "projects": results,
    }


@router.post("/students", status_code=status.HTTP_201_CREATED)
def create_student_admin(
    payload: AdminStudentCreateIn,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("ADMIN")),
):
    matricula = payload.matricula.strip().upper()
    email = payload.email.strip().lower()

    existing = db.query(Student).filter(
        (Student.matricula == matricula) | (Student.email == email)
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un estudiante con esa matrícula o correo."
        )

    student = Student(
        matricula=matricula,
        email=email,
        full_name=payload.full_name.strip() if payload.full_name else None,
    )

    try:
        db.add(student)
        db.commit()
        db.refresh(student)
        
        if payload.auto_checkin:
            checkin = Checkin(
                student_id=student.id,
                becario_user_id=current_user.id,
                method="ADMIN_MANUAL",
            )
            db.add(checkin)
            db.commit()
            
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo crear el estudiante. Por favor, intente más tarde.",
        )

    return {
        "ok": True,
        "message": "Estudiante creado exitosamente.",
        "student": {
            "id": str(student.id),
            "matricula": student.matricula,
            "email": student.email,
        }
    }


@router.get("/students")
def list_all_students(
    db: Session = Depends(get_db),
    _=Depends(require_role("ADMIN")),
):
    students = db.query(Student).order_by(Student.created_at.desc()).all()

    results = []

    for student in students:
        checkin = (
            db.query(Checkin)
            .filter(Checkin.student_id == student.id)
            .first()
        )

        registration_query = (
            db.query(Registration)
            .filter(Registration.student_id == student.id)
        )

        if hasattr(Registration, "status"):
            registration_query = registration_query.filter(
                Registration.status != "CANCELLED"
            )

        registration = registration_query.first()

        project = None
        if registration:
            project = db.query(Project).filter(Project.id == registration.project_id).first()

        results.append(
            {
                "id": str(student.id),
                "matricula": student.matricula,
                "email": student.email,
                "full_name": student.full_name,
                "created_at": student.created_at.isoformat(),
                "has_checkin": checkin is not None,
                "checkin_at": checkin.checked_in_at.isoformat() if checkin else None,
                "is_registered": registration is not None,
                "registration_id": str(registration.id) if registration else None,
                "project": {
                    "id": str(project.id),
                    "name": project.name,
                    "clave_programa": getattr(project, "clave_programa", None),
                } if project else None,
            }
        )

    return {
        "ok": True,
        "count": len(results),
        "students": results,
    }


@router.patch("/registrations/{registration_id}/cancel")
def cancel_registration(
    registration_id: uuid.UUID,
    db: Session = Depends(get_db),
    _=Depends(require_role("ADMIN")),
):
    registration = (
        db.query(Registration)
        .filter(Registration.id == registration_id)
        .first()
    )

    if not registration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registro no encontrado.",
        )

    current_status = getattr(registration, "status", None)

    if current_status == "CANCELLED":
        return {
            "ok": True,
            "message": "El registro ya estaba cancelado.",
            "registration": {
                "id": str(registration.id),
                "status": current_status,
            },
        }

    if hasattr(registration, "status"):
        registration.status = "CANCELLED"
        action = "updated"
    else:
        db.delete(registration)
        action = "deleted"

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo cancelar el registro.",
        )

    project = db.query(Project).filter(Project.id == registration.project_id).first()
    student = db.query(Student).filter(Student.id == registration.student_id).first()

    taken_slots = 0
    remaining_slots = None

    if project:
        active_registrations_query = db.query(Registration).filter(
            Registration.project_id == project.id
        )

        if hasattr(Registration, "status"):
            active_registrations_query = active_registrations_query.filter(
                Registration.status != "CANCELLED"
            )

        taken_slots = active_registrations_query.count()
        remaining_slots = max(project.capacity - taken_slots, 0)

    return {
        "ok": True,
        "message": "Registro cancelado correctamente.",
        "mode": action,
        "registration": {
            "id": str(registration.id),
            "student_id": str(registration.student_id),
            "project_id": str(registration.project_id),
            "status": getattr(registration, "status", "DELETED"),
        },
        "student": {
            "id": str(student.id) if student else None,
            "matricula": student.matricula if student else None,
            "email": student.email if student else None,
        },
        "project": {
            "id": str(project.id) if project else None,
            "name": project.name if project else None,
            "capacity": project.capacity if project else None,
            "taken_slots": taken_slots,
            "remaining_slots": remaining_slots,
        },
    }

@router.patch("/projects/{project_id}")
def update_project(
    project_id: uuid.UUID,
    payload: AdminProjectUpdateIn,
    db: Session = Depends(get_db),
    _=Depends(require_role("ADMIN")),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proyecto no encontrado.",
        )

    update_data = payload.dict(exclude_unset=True)
    if not update_data:
        return {"ok": True, "message": "No hay datos para actualizar."}

    for key, value in update_data.items():
        setattr(project, key, value)

    try:
        db.commit()
        db.refresh(project)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al actualizar el proyecto. Por favor, intente más tarde.",
        )

    return {"ok": True, "message": "Proyecto actualizado correctamente."}

@router.patch("/projects/{project_id}/deactivate")
def deactivate_project(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    _=Depends(require_role("ADMIN")),
):
    project = db.query(Project).filter(Project.id == project_id).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proyecto no encontrado.",
        )

    if not project.is_active:
        return {
            "ok": True,
            "message": "El proyecto ya estaba inactivo.",
            "project": {
                "id": str(project.id),
                "name": project.name,
                "is_active": project.is_active,
            },
        }

    project.is_active = False

    try:
        db.commit()
        db.refresh(project)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo desactivar el proyecto.",
        )

    return {
        "ok": True,
        "message": "Proyecto desactivado correctamente.",
        "project": {
            "id": str(project.id),
            "name": project.name,
            "is_active": project.is_active,
        },
    }


@router.patch("/projects/{project_id}/activate")
def activate_project(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    _=Depends(require_role("ADMIN")),
):
    project = db.query(Project).filter(Project.id == project_id).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proyecto no encontrado.",
        )

    if project.is_active:
        return {
            "ok": True,
            "message": "El proyecto ya estaba activo.",
            "project": {
                "id": str(project.id),
                "name": project.name,
                "is_active": project.is_active,
            },
        }

    project.is_active = True

    try:
        db.commit()
        db.refresh(project)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo activar el proyecto.",
        )

    return {
        "ok": True,
        "message": "Proyecto activado correctamente.",
        "project": {
            "id": str(project.id),
            "name": project.name,
            "is_active": project.is_active,
        },
    }