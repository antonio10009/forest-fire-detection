# backend/models/config.py
# Modelo SQLAlchemy para la tabla de configuración de umbrales

from sqlalchemy import Column, Integer, Float, DateTime
from sqlalchemy.sql import func
from backend.database import Base

class Configuracion(Base):
    __tablename__ = "configuracion"

    id                 = Column(Integer, primary_key=True, default=1)
    temp_amarillo_min  = Column(Float, default=45.0)   # °C inicio pre-alarma
    temp_rojo_min      = Column(Float, default=55.0)   # °C inicio incendio real
    humo_amarillo_min  = Column(Float, default=200.0)  # ppm inicio pre-alarma
    humo_rojo_min      = Column(Float, default=500.0)  # ppm incendio real
    humedad_riesgo_max = Column(Float, default=30.0)   # % umbral factor de riesgo
    humedad_normal_min = Column(Float, default=40.0)   # % inicio zona normal
    humedad_normal_max = Column(Float, default=70.0)   # % fin zona normal
    actualizado_en     = Column(DateTime, server_default=func.now(), onupdate=func.now())
