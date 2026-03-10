# scripts/seed_user.py
import os
import sys
import uuid
from datetime import datetime

from app.db.session import SessionLocal
from app.models.user import User
from app.core.security import hash_password


def main():
    print("[INFO] Iniciando seed_user...")

    if len(sys.argv) < 4:
        raise Exception(
            "Uso: python -m scripts.seed_user <email> <password> <role>\n"
            "Ejemplo: python -m scripts.seed_user socio1@tec.mx 123456 SOCIO"
        )

    email = sys.argv[1].strip().lower()
    password = sys.argv[2].strip()
    role = sys.argv[3].strip().upper()

    if role not in {"ADMIN", "SOCIO", "BECARIO"}:
        raise Exception("El role debe ser ADMIN, SOCIO o BECARIO")

    db = SessionLocal()

    existing = db.query(User).filter(User.email == email).first()

    if existing:
        print(f"[OK] El usuario ya existe: {email} | id={existing.id} | role={existing.role}")
        return

    user = User(
        id=uuid.uuid4(),
        email=email,
        hashed_password=hash_password(password),
        role=role,
        is_active=True,
        created_at=datetime.utcnow(),
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    print(f"[OK] Usuario creado: {user.email} | id={user.id} | role={user.role}")


if __name__ == "__main__":
    main()