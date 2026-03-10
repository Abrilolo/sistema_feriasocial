#app/models/user.py
import uuid
from datetime import datetime

from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    email = Column(String, unique=True, nullable=False, index=True)

    hashed_password = Column(String, nullable=False)

    role = Column(String, nullable=False, default="ADMIN")

    # Usuario activo
    is_active = Column(Boolean, nullable=False, default=True)

    # !ESTA ES LA COLUMNA QUE FALTABA
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)