from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from backend.database import Base

class Sensor(Base):
    __tablename__ = "sensores"

    id          = Column(Integer, primary_key=True, index=True)
    nombre      = Column(String(100), nullable=False)
    ubicacion   = Column(String(200))
    latitud     = Column(Float, nullable=False)
    longitud    = Column(Float, nullable=False)
    activo      = Column(Boolean, default=True)
    creado_en   = Column(DateTime, default=datetime.utcnow)

    lecturas    = relationship("Lectura", back_populates="sensor")
    alertas     = relationship("Alerta", back_populates="sensor")


class Lectura(Base):
    __tablename__ = "lecturas"

    id              = Column(Integer, primary_key=True, index=True)
    sensor_id       = Column(Integer, ForeignKey("sensores.id"))
    temperatura     = Column(Float)
    humo_ppm        = Column(Float)
    humedad         = Column(Float)
    nivel_alerta    = Column(String(20), default="VERDE")
    registrado_en   = Column(DateTime, default=datetime.utcnow)

    sensor          = relationship("Sensor", back_populates="lecturas")


class Alerta(Base):
    __tablename__ = "alertas"

    id          = Column(Integer, primary_key=True, index=True)
    sensor_id   = Column(Integer, ForeignKey("sensores.id"))
    tipo        = Column(String(50))
    mensaje     = Column(String(500))
    activa      = Column(Boolean, default=True)
    creada_en   = Column(DateTime, default=datetime.utcnow)

    sensor      = relationship("Sensor", back_populates="alertas")