#scripts/seed_admin.py
import os
import uuid
from datetime import datetime

from app.db.session import SessionLocal
from app.models.user import User
from app.core.security import hash_password


def main():
    print("[INFO] Iniciando seed_admin...")

    db = SessionLocal()

    admin_email = os.getenv("ADMIN_EMAIL")
    admin_password = os.getenv("ADMIN_PASSWORD")

    print(f"[INFO] ADMIN_EMAIL={admin_email!r}")
    print(f"[INFO] ADMIN_PASSWORD definida={bool(admin_password)}")

    if not admin_email or not admin_password:
        raise Exception("ADMIN_EMAIL y ADMIN_PASSWORD deben estar definidos")

    existing = db.query(User).filter(User.email == admin_email).first()

    if existing:
        print(f"[OK] Admin ya existe: {admin_email} | id={existing.id}")
        return

    user = User(
        id=uuid.uuid4(),
        email=admin_email,
        hashed_password=hash_password(admin_password),
        role="ADMIN",
        is_active=True,
        created_at=datetime.utcnow(),
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    print(f"[OK] Admin creado: {user.email} | id={user.id}")


if __name__ == "__main__":
    main()