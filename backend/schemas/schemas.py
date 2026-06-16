from pydantic import BaseModel
from datetime import datetime
from typing import Optional

# ─── SENSOR ───────────────────────────────
class SensorBase(BaseModel):
    nombre: str
    ubicacion: str
    latitud: float
    longitud: float

class SensorCreate(SensorBase):
    pass

class SensorResponse(SensorBase):
    id: int
    activo: bool
    creado_en: datetime

    class Config:
        from_attributes = True

# ─── LECTURA ──────────────────────────────
class LecturaBase(BaseModel):
    sensor_id: int
    temperatura: float
    humo_ppm: float
    humedad: float

class LecturaCreate(LecturaBase):
    latitud: Optional[float] = None
    longitud: Optional[float] = None

class LecturaResponse(LecturaBase):
    id: int
    nivel_alerta: str
    registrado_en: datetime

    class Config:
        from_attributes = True

# ─── ALERTA ───────────────────────────────
class AlertaResponse(BaseModel):
    id: int
    sensor_id: int
    tipo: str
    mensaje: str
    activa: bool
    creada_en: datetime

    class Config:
        from_attributes = True