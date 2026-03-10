# scripts/generate_invite_qr.py
import sys
from datetime import timedelta

from app.db.session import SessionLocal
from app.models.student import Student
from app.core.security import create_access_token


def main():
    print("[INFO] Iniciando generate_invite_qr...")

    if len(sys.argv) < 2:
        raise Exception(
            "Uso:\n"
            "  python -m scripts.generate_invite_qr <student_id>\n"
            "  python -m scripts.generate_invite_qr <matricula> --by-matricula\n"
            "\n"
            "Ejemplos:\n"
            "  python -m scripts.generate_invite_qr 11111111-2222-3333-4444-555555555555\n"
            "  python -m scripts.generate_invite_qr A01234567 --by-matricula"
        )

    value = sys.argv[1].strip()
    by_matricula = "--by-matricula" in sys.argv

    db = SessionLocal()

    if by_matricula:
        student = db.query(Student).filter(Student.matricula == value.upper()).first()
    else:
        student = db.query(Student).filter(Student.id == value).first()

    if not student:
        raise Exception("Estudiante no encontrado.")

    qr_token = create_access_token(
        data={
            "sub": str(student.id),
            "type": "invite",
        },
        expires_delta=timedelta(days=7),  # puedes cambiarlo si quieres
    )

    print("[OK] QR token generado:")
    print(f"student_id={student.id}")
    print(f"matricula={student.matricula}")
    print(f"email={student.email}")
    print()
    print(qr_token)


if __name__ == "__main__":
    main()