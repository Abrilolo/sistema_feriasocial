#app/models/qr_token.py
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class QRToken(Base):
    __tablename__ = "qr_tokens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # El token UUID que se muestra en el QR
    token: Mapped[str] = mapped_column(String(36), unique=True, index=True, nullable=False)

    # Estudiante al que pertenece
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("students.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    # Fecha de expiración (2 horas por defecto)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # Fecha de uso (NULL = no usado; fecha = ya escaneado)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    @staticmethod
    def generate_token() -> str:
        """Genera un UUID v4 como token opaco"""
        return str(uuid.uuid4())

    @staticmethod
    def get_default_expiry() -> datetime:
        """Retorna la fecha de expiración por defecto (2 horas desde ahora)"""
        return datetime.now(timezone.utc) + timedelta(hours=2)

    def is_expired(self) -> bool:
        """Verifica si el token ha expirado"""
        return datetime.now(timezone.utc) >= self.expires_at.replace(tzinfo=timezone.utc)

    def is_used(self) -> bool:
        """Verifica si el token ya fue usado"""
        return self.used_at is not None

    def is_valid(self) -> bool:
        """Verifica si el token es válido (no expirado y no usado)"""
        return not self.is_expired() and not self.is_used()
