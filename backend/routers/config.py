# backend/routers/config.py
# Endpoints para leer y actualizar la configuración de umbrales

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models.config import Configuracion
from backend.schemas.schemas import ConfiguracionUpdate, ConfiguracionResponse
from datetime import datetime

router = APIRouter()

def get_config(db: Session) -> Configuracion:
    """Obtiene la configuración actual o crea la default si no existe."""
    config = db.query(Configuracion).filter(Configuracion.id == 1).first()
    if not config:
        config = Configuracion(id=1)
        db.add(config)
        db.commit()
        db.refresh(config)
    return config

@router.get("/", response_model=ConfiguracionResponse)
def obtener_configuracion(db: Session = Depends(get_db)):
    """Retorna la configuración actual de umbrales."""
    return get_config(db)

@router.put("/", response_model=ConfiguracionResponse)
def actualizar_configuracion(
    datos: ConfiguracionUpdate,
    db: Session = Depends(get_db)
):
    """
    Actualiza los umbrales de clasificación de incendio.
    Los cambios afectan todas las lecturas futuras del ESP32.
    """
    config = get_config(db)

    config.temp_amarillo_min  = datos.temp_amarillo_min
    config.temp_rojo_min      = datos.temp_rojo_min
    config.humo_amarillo_min  = datos.humo_amarillo_min
    config.humo_rojo_min      = datos.humo_rojo_min
    config.humedad_riesgo_max = datos.humedad_riesgo_max
    config.humedad_normal_min = datos.humedad_normal_min
    config.humedad_normal_max = datos.humedad_normal_max
    config.actualizado_en     = datetime.utcnow()

    db.commit()
    db.refresh(config)
    return config
