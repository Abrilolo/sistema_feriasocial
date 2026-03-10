#app/models/checkin.py
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Checkin(Base):
    __tablename__ = "checkins"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Un estudiante solo puede hacer check-in una vez
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("students.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )

    # Becario que verificó (usuario con role=BECARIO)
    becario_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )

    method: Mapped[str | None] = mapped_column(String(50), nullable=True)  # ej. "QR", "MANUAL"
    checked_in_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
