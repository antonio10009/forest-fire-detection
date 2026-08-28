# backend/routers/sensors.py
# Versión actualizada con lógica AND para evitar falsos positivos por luz solar

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models.sensor import Sensor, Lectura, Alerta
from backend.models.config import Configuracion
from backend.schemas.schemas import SensorCreate, SensorResponse, LecturaCreate, LecturaResponse
from backend.notifications import disparar_alerta_incendio
from typing import List

router = APIRouter()

def get_config(db: Session) -> Configuracion:
    config = db.query(Configuracion).filter(Configuracion.id == 1).first()
    if not config:
        config = Configuracion(id=1)
        db.add(config)
        db.commit()
        db.refresh(config)
    return config

def clasificar_nivel(lectura: LecturaCreate, config: Configuracion) -> str:
    """
    Clasifica el nivel de alerta con lógica AND para evitar falsos positivos.

    VERDE  — Condiciones normales, sin riesgo.
    AMARILLO — Pre-alarma o señal ambigua que requiere vigilancia.
    ROJO   — Incendio real confirmado por múltiples sensores simultáneos.

    Lógica anti-falso positivo:
      La llama sola (sin calor ni humo elevado) activa AMARILLO, no ROJO.
      Esto evita que la luz solar directa dispare falsas alarmas de incendio.
      Un incendio real siempre produce llama + calor O llama + humo simultáneamente.

    ROJO si:
      - Llama + temperatura >= temp_amarillo_min (calor confirmado con llama)
      - Llama + humo >= humo_amarillo_min (gases confirmados con llama)
      - Temperatura >= temp_rojo_min + humo >= humo_amarillo_min (calor extremo + gases)
      - Humo >= humo_rojo_min solo (gases críticos sin llama, ej. fuego oculto)

    AMARILLO si:
      - Llama sola sin calor ni humo elevado (posible luz solar, vigilar)
      - Temperatura entre temp_amarillo_min y temp_rojo_min
      - Humo entre humo_amarillo_min y humo_rojo_min
      - Humedad <= humedad_riesgo_max (factor de riesgo contextual)

    VERDE en cualquier otro caso.
    """
    temp  = lectura.temperatura
    humo  = lectura.humo_ppm
    hum   = lectura.humedad
    llama = lectura.llama or False

    # DHT22 fallido (0,0) → no clasificar por temp ni humedad
    dht_ok = not (temp == 0 and hum == 0)

    # ── ROJO — incendio real confirmado ───────────────────────
    # Llama + calor confirmado (descarta luz solar sola)
    if llama and dht_ok and temp >= config.temp_amarillo_min:
        return "ROJO"

    # Llama + humo elevado confirmado (descarta luz solar sola)
    if llama and humo >= config.humo_amarillo_min:
        return "ROJO"

    # Temperatura extrema + humo elevado (fuego sin llama visible)
    if dht_ok and temp >= config.temp_rojo_min and humo >= config.humo_amarillo_min:
        return "ROJO"

    # Humo crítico solo (fuego oculto bajo vegetación)
    if humo >= config.humo_rojo_min:
        return "ROJO"

    # ── AMARILLO — pre-alarma o señal ambigua ─────────────────
    # Llama sola sin calor ni humo = posible luz solar, vigilar
    if llama:
        return "AMARILLO"

    # Temperatura en zona de pre-alarma
    if dht_ok and config.temp_amarillo_min <= temp < config.temp_rojo_min:
        return "AMARILLO"

    # Humo en zona de pre-alarma
    if config.humo_amarillo_min <= humo < config.humo_rojo_min:
        return "AMARILLO"

    # Humedad baja: factor de riesgo contextual
    if dht_ok and hum <= config.humedad_riesgo_max:
        return "AMARILLO"

    # ── VERDE — condiciones normales ──────────────────────────
    return "VERDE"

# ─── CREAR SENSOR ─────────────────────────
@router.post("/", response_model=SensorResponse)
def crear_sensor(sensor: SensorCreate, db: Session = Depends(get_db)):
    nuevo_sensor = Sensor(**sensor.model_dump())
    db.add(nuevo_sensor)
    db.commit()
    db.refresh(nuevo_sensor)
    return nuevo_sensor

# ─── LISTAR SENSORES ──────────────────────
@router.get("/", response_model=List[SensorResponse])
def listar_sensores(db: Session = Depends(get_db)):
    return db.query(Sensor).filter(Sensor.activo == True).all()

# ─── OBTENER SENSOR POR ID ────────────────
@router.get("/{sensor_id}", response_model=SensorResponse)
def obtener_sensor(sensor_id: int, db: Session = Depends(get_db)):
    sensor = db.query(Sensor).filter(Sensor.id == sensor_id).first()
    if not sensor:
        raise HTTPException(status_code=404, detail="Sensor no encontrado")
    return sensor

# ─── RECIBIR LECTURA DEL ESP32 ────────────
@router.post("/lectura", response_model=LecturaResponse)
def recibir_lectura(lectura: LecturaCreate, db: Session = Depends(get_db)):

    config = get_config(db)
    nivel = clasificar_nivel(lectura, config)

    nueva_lectura = Lectura(**lectura.model_dump(), nivel_alerta=nivel)
    db.add(nueva_lectura)

    # Actualizar GPS y último nivel del sensor
    sensor_obj = db.query(Sensor).filter(Sensor.id == lectura.sensor_id).first()
    if sensor_obj:
        if lectura.latitud is not None and lectura.longitud is not None:
            sensor_obj.latitud  = lectura.latitud
            sensor_obj.longitud = lectura.longitud
        sensor_obj.ultimo_nivel = nivel

    # Disparar alerta solo en ROJO real (no en AMARILLO por luz solar)
    if nivel == "ROJO":
        alerta = Alerta(
            sensor_id=lectura.sensor_id,
            tipo="INCENDIO",
            mensaje=f"🔥 Alerta crítica: Temperatura {lectura.temperatura}°C, "
                    f"Humo {lectura.humo_ppm}ppm, Llama: {'SI' if lectura.llama else 'NO'}"
        )
        db.add(alerta)

        if sensor_obj:
            disparar_alerta_incendio(
                sensor_nombre=sensor_obj.nombre,
                ubicacion=sensor_obj.ubicacion,
                temperatura=lectura.temperatura,
                humo_ppm=lectura.humo_ppm
            )

    db.commit()
    db.refresh(nueva_lectura)
    return nueva_lectura

# ─── LISTAR LECTURAS POR SENSOR ───────────
@router.get("/{sensor_id}/lecturas", response_model=List[LecturaResponse])
def listar_lecturas(sensor_id: int, db: Session = Depends(get_db)):
    return db.query(Lectura).filter(Lectura.sensor_id == sensor_id).all()