# backend/models/suscriptor.py

from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from backend.database import Base


class Suscriptor(Base):
    __tablename__ = "suscriptores"

    id             = Column(Integer, primary_key=True, index=True)
    numero_wa      = Column(String(20), unique=True, nullable=False)  # ej: +56937247294
    nombre         = Column(String(100), nullable=True)
    zona           = Column(String(100), default="General")
    activo         = Column(Boolean, default=True)
    fecha_registro = Column(DateTime, server_default=func.now())
    fecha_baja     = Column(DateTime, nullable=True)