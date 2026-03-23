import uuid
from datetime import datetime

from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    image_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)

    capacity: Mapped[int] = mapped_column(Integer, nullable=False)

    # El socio dueño del proyecto (usuario con role=SOCIO)
    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    periodo: Mapped[str | None] = mapped_column(String(255), nullable=True)
    carreras_permitidas: Mapped[str | None] = mapped_column(String(255), nullable=True)
    objetivo: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    actividades: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    horario: Mapped[str | None] = mapped_column(String(255), nullable=True)
    competencias_requeridas: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    modalidad: Mapped[str | None] = mapped_column(String(255), nullable=True)
    lugar_trabajo: Mapped[str | None] = mapped_column(String(255), nullable=True)
    duracion: Mapped[str | None] = mapped_column(String(255), nullable=True)
    poblacion_atendida: Mapped[str | None] = mapped_column(String(255), nullable=True)
    horas_acreditar: Mapped[str | None] = mapped_column(String(255), nullable=True)
    comentarios_adicionales: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    clave_programa: Mapped[str | None] = mapped_column(String(255), nullable=True)
