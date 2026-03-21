# app/routers/socio.py
from datetime import datetime, timedelta
import uuid
import csv
from io import StringIO

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.deps import require_roles, get_current_user
from app.models.project import Project
from app.models.temp_code import TempCode
from app.models.registration import Registration
from app.models.student import Student

router = APIRouter(prefix="/socio", tags=["Socio"])


# -----------------------------
# LISTAR PROYECTOS DEL SOCIO
# -----------------------------
@router.get("/projects")
def get_my_projects(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("SOCIO")),
):
    projects = (
        db.query(Project)
        .filter(Project.owner_user_id == current_user.id)
        .all()
    )

    result = []

    for project in projects:
        taken_slots = (
            db.query(Registration)
            .filter(Registration.project_id == project.id)
            .count()
        )

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

        result.append(
            {
                "id": project.id,
                "name": project.name,
                "description": project.description,
                "capacity": project.capacity,
                "taken_slots": taken_slots,
                "remaining_slots": project.capacity - taken_slots,
                "active_codes": active_codes,
                "is_active": project.is_active,
            }
        )

    return {"projects": result}


# -----------------------------
# DETALLE DE PROYECTO
# -----------------------------
@router.get("/projects/{project_id}")
def get_my_project_detail(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("SOCIO")),
):
    project = (
        db.query(Project)
        .filter(
            Project.id == project_id,
            Project.owner_user_id == current_user.id,
        )
        .first()
    )

    if not project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")

    # FIX: crear el query correctamente
    taken_slots_query = db.query(Registration).filter(
        Registration.project_id == project.id
    )

    if hasattr(Registration, "status"):
        taken_slots_query = taken_slots_query.filter(
            Registration.status != "CANCELLED"
        )

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
            TempCode.expires_at < datetime.utcnow(),
        )
        .count()
    )

    return {
        "project": {
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "capacity": project.capacity,
            "taken_slots": taken_slots,
            "remaining_slots": project.capacity - taken_slots,
            "active_codes": active_codes,
            "used_codes": used_codes,
            "expired_codes": expired_codes,
            "is_active": project.is_active,
        }
    }


# -----------------------------
# GENERAR CODIGO TEMPORAL
# -----------------------------
@router.post("/temp-codes")
def generate_temp_code(
    payload: dict,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("SOCIO")),
):
    project_id = payload.get("project_id")
    expires_in_minutes = payload.get("expires_in_minutes", 10)

    project = (
        db.query(Project)
        .filter(
            Project.id == project_id,
            Project.owner_user_id == current_user.id,
        )
        .first()
    )

    if not project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")

    code_value = str(uuid.uuid4())[:8].upper()

    temp_code = TempCode(
        id=uuid.uuid4(),
        project_id=project.id,
        code=code_value,
        expires_at=datetime.utcnow() + timedelta(minutes=expires_in_minutes),
        is_active=True,
        used_at=None,
    )

    db.add(temp_code)
    db.commit()
    db.refresh(temp_code)

    return {
        "temp_code": {
            "id": temp_code.id,
            "code": temp_code.code,
            "expires_at": temp_code.expires_at,
        }
    }


# -----------------------------
# LISTAR CODIGOS
# -----------------------------
@router.get("/projects/{project_id}/codes")
def get_project_codes(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("SOCIO")),
):
    codes = (
        db.query(TempCode)
        .filter(TempCode.project_id == project_id)
        .order_by(TempCode.created_at.desc())
        .all()
    )

    result = []

    for code in codes:
        result.append(
            {
                "id": code.id,
                "code": code.code,
                "is_active": code.is_active,
                "is_used": code.is_used,
                "is_expired": code.expires_at < datetime.utcnow(),
                "expires_at": code.expires_at,
            }
        )

    return {"codes": result}


# -----------------------------
# DESACTIVAR CODIGO
# -----------------------------
@router.patch("/temp-codes/{temp_code_id}/deactivate")
def deactivate_temp_code(
    temp_code_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("SOCIO")),
):
    code = db.query(TempCode).filter(TempCode.id == temp_code_id).first()

    if not code:
        raise HTTPException(status_code=404, detail="Código no encontrado")

    code.is_active = False
    db.commit()

    return {"message": "Código desactivado"}


# -----------------------------
# LISTAR ESTUDIANTES
# -----------------------------
@router.get("/projects/{project_id}/students")
def get_project_students(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("SOCIO")),
):
    registrations = (
        db.query(Registration)
        .join(Student)
        .filter(Registration.project_id == project_id)
        .all()
    )

    result = []

    for reg in registrations:
        student = reg.student_id

        result.append(
            {
                "matricula": student.matricula,
                "email": student.email,
                "full_name": getattr(student, "full_name", ""),
                "status": getattr(reg, "status", ""),
                "registered_at": reg.created_at,
            }
        )

    return {"students": result}


# -----------------------------
# EXPORTAR CSV
# -----------------------------
@router.get("/projects/{project_id}/students/export")
def export_project_students(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("SOCIO")),
):
    registrations = (
        db.query(Registration)
        .join(Student)
        .filter(Registration.project_id == project_id)
        .all()
    )

    output = StringIO()
    writer = csv.writer(output)

    writer.writerow(["Matricula", "Correo", "Nombre"])

    for reg in registrations:
        student = reg.student
        writer.writerow(
            [
                student.matricula,
                student.email,
                getattr(student, "full_name", ""),
            ]
        )

    output.seek(0)

    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=students.csv"},
    )