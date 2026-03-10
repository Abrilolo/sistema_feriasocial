# scripts/seed_project.py
import sys
import uuid
from datetime import datetime

from app.db.session import SessionLocal
from app.models.user import User
from app.models.project import Project


def main():
    print("[INFO] Iniciando seed_project...")

    if len(sys.argv) < 4:
        raise Exception(
            "Uso: python -m scripts.seed_project <email_socio> <nombre_proyecto> <capacity>\n"
            'Ejemplo: python -m scripts.seed_project socio1@tec.mx "Proyecto QR Feria" 10'
        )

    socio_email = sys.argv[1].strip().lower()
    project_name = sys.argv[2].strip()
    capacity = int(sys.argv[3])

    if capacity <= 0:
        raise Exception("capacity debe ser mayor que 0")

    db = SessionLocal()

    # 1) Buscar al socio
    socio = db.query(User).filter(User.email == socio_email).first()

    if not socio:
        raise Exception(f"No existe un usuario con email: {socio_email}")

    if socio.role not in {"SOCIO", "ADMIN"}:
        raise Exception(
            f"El usuario {socio_email} no tiene rol válido para dueño de proyecto. Rol actual: {socio.role}"
        )

    # 2) Evitar duplicados por nombre + owner
    existing = (
        db.query(Project)
        .filter(
            Project.name == project_name,
            Project.owner_user_id == socio.id,
        )
        .first()
    )

    if existing:
        print(
            f"[OK] El proyecto ya existe: {existing.name} | "
            f"id={existing.id} | owner_user_id={existing.owner_user_id}"
        )
        return

    # 3) Crear proyecto
    project = Project(
        id=uuid.uuid4(),
        name=project_name,
        description=f"Proyecto de prueba para {socio.email}",
        capacity=capacity,
        owner_user_id=socio.id,
        is_active=True,
        created_at=datetime.utcnow(),
    )

    db.add(project)
    db.commit()
    db.refresh(project)

    print("[OK] Proyecto creado correctamente:")
    print(f"     id={project.id}")
    print(f"     name={project.name}")
    print(f"     owner_user_id={project.owner_user_id}")
    print(f"     capacity={project.capacity}")
    print(f"     is_active={project.is_active}")


if __name__ == "__main__":
    main()