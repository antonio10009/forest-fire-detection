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
    ultimo_nivel: Optional[str] = "VERDE"

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
    llama: Optional[bool] = False

class LecturaResponse(LecturaBase):
    id: int
    nivel_alerta: str
    registrado_en: datetime
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    llama: Optional[bool] = False

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

# Nueva configuración de umbrales.

# ─── CONFIGURACIÓN DE UMBRALES ────────────────────────────────
class ConfiguracionBase(BaseModel):
    temp_amarillo_min:  float = 45.0
    temp_rojo_min:      float = 55.0
    humo_amarillo_min:  float = 200.0
    humo_rojo_min:      float = 500.0
    humedad_riesgo_max: float = 30.0
    humedad_normal_min: float = 40.0
    humedad_normal_max: float = 70.0

class ConfiguracionUpdate(ConfiguracionBase):
    pass

class ConfiguracionResponse(ConfiguracionBase):
    id: int
    actualizado_en: datetime

    class Config:
        from_attributes = True