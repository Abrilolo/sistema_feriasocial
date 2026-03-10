# scripts/seed_student.py
import sys
import uuid
from datetime import datetime

from app.db.session import SessionLocal
from app.models.student import Student


def main():
    print("[INFO] Iniciando seed_student...")

    if len(sys.argv) < 4:
        raise Exception(
            "Uso: python -m scripts.seed_student <matricula> <email> <full_name>\n"
            'Ejemplo: python -m scripts.seed_student A01234567 alumno@tec.mx "Juan Perez"'
        )

    matricula = sys.argv[1].strip().upper()
    email = sys.argv[2].strip().lower()
    full_name = sys.argv[3].strip()

    db = SessionLocal()

    existing_by_matricula = db.query(Student).filter(Student.matricula == matricula).first()
    if existing_by_matricula:
        print(
            f"[OK] Ya existe un alumno con esa matrícula: "
            f"{existing_by_matricula.matricula} | id={existing_by_matricula.id}"
        )
        return

    existing_by_email = db.query(Student).filter(Student.email == email).first()
    if existing_by_email:
        print(
            f"[OK] Ya existe un alumno con ese email: "
            f"{existing_by_email.email} | id={existing_by_email.id}"
        )
        return

    student = Student(
        id=uuid.uuid4(),
        matricula=matricula,
        email=email,
        full_name=full_name,
        created_at=datetime.utcnow(),
    )

    db.add(student)
    db.commit()
    db.refresh(student)

    print("[OK] Alumno creado correctamente:")
    print(f"     id={student.id}")
    print(f"     matricula={student.matricula}")
    print(f"     email={student.email}")
    print(f"     full_name={student.full_name}")


if __name__ == "__main__":
    main()