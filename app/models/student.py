#app/models/student.py
import uuid
from datetime import datetime

from sqlalchemy import String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Student(Base):
    __tablename__ = "students"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    matricula: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)

    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    career: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Campos para autenticación con Google OAuth
    google_id: Mapped[str | None] = mapped_column(String(255), unique=True, index=True, nullable=True)
    picture_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
