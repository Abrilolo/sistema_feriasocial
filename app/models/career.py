import uuid
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Career(Base):
    __tablename__ = "careers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre_carrera: Mapped[str] = mapped_column(String(255), nullable=False)
    siglas: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    escuela: Mapped[str] = mapped_column(String(255), nullable=False)
