from datetime import datetime

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


class AdminUserCreateIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=72)
    role: str


class AdminProjectCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    capacity: int = Field(gt=0)
    owner_user_id: str


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
                "registered_at": registration.created_at.isoformat() if registration else None,
                "project": {
                    "id": str(project.id),
                    "name": project.name,
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
    registration_id: str,
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


@router.patch("/projects/{project_id}/deactivate")
def deactivate_project(
    project_id: str,
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
    project_id: str,
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