# app/routers/socio.py
import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.models.project import Project
from app.models.temp_code import TempCode
from app.core.security import get_current_user
from app.models.student import Student
from app.models.registration import Registration
import csv
from io import StringIO
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/socio", tags=["socio"])


def require_roles(*allowed_roles: str):
    def _dep(user: User = Depends(get_current_user)):
        role = getattr(user, "role", None)
        if role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para esta acción.",
            )
        return user
    return _dep


class TempCodeCreateIn(BaseModel):
    project_id: str
    expires_in_minutes: int = Field(default=10, ge=1, le=120)


def _generate_temp_code(length: int = 10) -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))


@router.get("/projects")
def list_my_projects(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("SOCIO", "ADMIN")),
):
    projects = (
        db.query(Project)
        .filter(Project.owner_user_id == user.id)
        .order_by(Project.created_at.desc())
        .all()
    )

    results = []
    for project in projects:
        taken_slots_query = (
            db.query(Registration).filter(Registration.project_id == project.id)
        )

        if hasattr(Registration, "status"):
            taken_slots_query = taken_slots_query.filter(Registration.status != "CANCELLED")
        taken_slots = taken_slots_query.count()

        active_codes = (
            db.query(TempCode)
            .filter(
                TempCode.project_id == project.id,
                TempCode.is_active == True,
                TempCode.used_at.is_(None),
                TempCode.expires_at > datetime.utcnow(),
            )
            .count()
        )

        results.append(
            {
                "id": str(project.id),
                "name": project.name,
                "description": project.description,
                "capacity": project.capacity,
                "taken_slots": taken_slots,
                "remaining_slots": max(project.capacity - taken_slots, 0),
                "active_codes": active_codes,
                "is_active": project.is_active,
                "created_at": project.created_at.isoformat(),
            }
        )

    return {
        "ok": True,
        "count": len(results),
        "projects": results,
    }


@router.get("/projects/{project_id}")
def get_my_project_detail(
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("SOCIO", "ADMIN")),
):
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.owner_user_id == user.id)
        .first()
    )

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proyecto no encontrado o no te pertenece.",
        )

    registrations_query = (
        db.query(Registration)
        .filter(Registration.project_id == project.id)
        .count()
    )
    if hasattr(Registration, "status"):
        taken_slots_query = taken_slots_query.filter(Registration.status != "CANCELLED")
        taken_slots = taken_slots_query.count()

    active_codes = (
        db.query(TempCode)
        .filter(
            TempCode.project_id == project.id,
            TempCode.is_active == True,
            TempCode.used_at.is_(None),
            TempCode.expires_at > datetime.utcnow(),
        )
        .count()
    )

    used_codes = (
        db.query(TempCode)
        .filter(
            TempCode.project_id == project.id,
            TempCode.used_at.is_not(None),
        )
        .count()
    )

    expired_codes = (
        db.query(TempCode)
        .filter(
            TempCode.project_id == project.id,
            TempCode.expires_at <= datetime.utcnow(),
        )
        .count()
    )

    return {
        "ok": True,
        "project": {
            "id": str(project.id),
            "name": project.name,
            "description": project.description,
            "capacity": project.capacity,
            "taken_slots_query": registrations_query,
            "remaining_slots": max(project.capacity - registrations_query, 0),
            "active_codes": active_codes,
            "used_codes": used_codes,
            "expired_codes": expired_codes,
            "is_active": project.is_active,
            "created_at": project.created_at.isoformat(),
        },
    }


@router.post("/temp-codes", status_code=status.HTTP_201_CREATED)
def create_temp_code(
    payload: TempCodeCreateIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("SOCIO", "ADMIN")),
):
    project = (
        db.query(Project)
        .filter(Project.id == payload.project_id, Project.owner_user_id == user.id)
        .first()
    )

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proyecto no encontrado o no te pertenece.",
        )

    if not project.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El proyecto no está activo.",
        )

    taken_slots = (
        db.query(Registration)
        .filter(Registration.project_id == project.id)
        .count()
    )

    if taken_slots >= project.capacity:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El proyecto ya no tiene cupo disponible.",
        )

    active_unused_codes = (
        db.query(TempCode)
        .filter(
            TempCode.project_id == project.id,
            TempCode.is_active == True,
            TempCode.used_at.is_(None),
            TempCode.expires_at > datetime.utcnow(),
        )
        .count()
    )

    available_slots = project.capacity - taken_slots

    if active_unused_codes >= available_slots:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existen suficientes códigos activos para cubrir el cupo disponible.",
        )

    code = _generate_temp_code()
    while db.query(TempCode).filter(TempCode.code == code).first():
        code = _generate_temp_code()

    expires_at = datetime.utcnow() + timedelta(minutes=payload.expires_in_minutes)

    temp_code = TempCode(
        code=code,
        project_id=project.id,
        created_by_user_id=user.id,
        expires_at=expires_at,
        is_active=True,
    )

    try:
        db.add(temp_code)
        db.commit()
        db.refresh(temp_code)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo generar el código temporal.",
        )

    return {
        "ok": True,
        "message": "Código temporal generado correctamente.",
        "temp_code": {
            "id": str(temp_code.id),
            "code": temp_code.code,
            "project_id": str(project.id),
            "project_name": project.name,
            "expires_at": temp_code.expires_at.isoformat(),
            "is_active": temp_code.is_active,
            "created_at": temp_code.created_at.isoformat(),
        },
        "project": {
            "capacity": project.capacity,
            "taken_slots": taken_slots,
            "remaining_slots": project.capacity - taken_slots,
        },
    }


@router.get("/projects/{project_id}/codes")
def list_project_codes(
    project_id: str,
    only_active: bool = Query(default=False),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("SOCIO", "ADMIN")),
):
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.owner_user_id == user.id)
        .first()
    )

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proyecto no encontrado o no te pertenece.",
        )

    query = db.query(TempCode).filter(TempCode.project_id == project.id)

    if only_active:
        query = query.filter(
            TempCode.is_active == True,
            TempCode.used_at.is_(None),
            TempCode.expires_at > datetime.utcnow(),
        )

    codes = query.order_by(TempCode.created_at.desc()).all()

    results = []
    now = datetime.utcnow()

    for item in codes:
        results.append(
            {
                "id": str(item.id),
                "code": item.code,
                "is_active": item.is_active,
                "is_used": item.used_at is not None,
                "is_expired": item.expires_at <= now,
                "expires_at": item.expires_at.isoformat(),
                "used_at": item.used_at.isoformat() if item.used_at else None,
                "created_at": item.created_at.isoformat(),
            }
        )

    return {
        "ok": True,
        "project": {
            "id": str(project.id),
            "name": project.name,
        },
        "count": len(results),
        "codes": results,
    }


@router.patch("/temp-codes/{temp_code_id}/deactivate")
def deactivate_temp_code(
    temp_code_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("SOCIO", "ADMIN")),
):
    temp_code = (
        db.query(TempCode)
        .join(Project, Project.id == TempCode.project_id)
        .filter(
            TempCode.id == temp_code_id,
            Project.owner_user_id == user.id,
        )
        .first()
    )

    if not temp_code:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Código no encontrado o no te pertenece.",
        )

    if temp_code.used_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede desactivar un código que ya fue utilizado.",
        )

    if not temp_code.is_active:
        return {
            "ok": True,
            "message": "El código ya estaba inactivo.",
            "temp_code": {
                "id": str(temp_code.id),
                "code": temp_code.code,
                "is_active": temp_code.is_active,
            },
        }

    temp_code.is_active = False

    try:
        db.commit()
        db.refresh(temp_code)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo desactivar el código.",
        )

    return {
        "ok": True,
        "message": "Código desactivado correctamente.",
        "temp_code": {
            "id": str(temp_code.id),
            "code": temp_code.code,
            "is_active": temp_code.is_active,
        },
    }

@router.get("/projects/{project_id}/students")
def list_project_students(
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("SOCIO", "ADMIN")),
):
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.owner_user_id == user.id)
        .first()
    )

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proyecto no encontrado o no te pertenece.",
        )

    rows = (
        db.query(Registration, Student)
        .join(Student, Student.id == Registration.student_id)
        .filter(Registration.project_id == project.id)
        .order_by(Registration.created_at.asc())
        .all()
    )

    students = []
    for registration, student in rows:
        students.append(
            {
                "registration_id": str(registration.id),
                "student_id": str(student.id),
                "matricula": student.matricula,
                "email": student.email,
                "full_name": student.full_name,
                "registered_at": registration.created_at.isoformat(),
                "status": getattr(registration, "status", None),
            }
        )

    return {
        "ok": True,
        "project": {
            "id": str(project.id),
            "name": project.name,
            "capacity": project.capacity,
            "taken_slots": len(students),
            "remaining_slots": max(project.capacity - len(students), 0),
        },
        "count": len(students),
        "students": students,
    }

@router.get("/projects/{project_id}/students/export")
def export_project_students(
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("SOCIO", "ADMIN")),
):

    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.owner_user_id == user.id)
        .first()
    )

    if not project:
        raise HTTPException(
            status_code=404,
            detail="Proyecto no encontrado o no te pertenece."
        )

    rows = (
        db.query(Registration, Student)
        .join(Student, Student.id == Registration.student_id)
        .filter(Registration.project_id == project.id)
        .order_by(Registration.created_at.asc())
        .all()
    )

    buffer = StringIO()
    writer = csv.writer(buffer)

    writer.writerow([
        "matricula",
        "email",
        "full_name",
        "registered_at"
    ])

    for registration, student in rows:
        writer.writerow([
            student.matricula,
            student.email,
            student.full_name,
            registration.created_at.isoformat(),
        ])

    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=project_{project.id}_students.csv"
        },
    )
