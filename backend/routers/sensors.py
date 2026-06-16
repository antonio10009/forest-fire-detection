from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models.sensor import Sensor, Lectura, Alerta
from backend.schemas.schemas import SensorCreate, SensorResponse, LecturaCreate, LecturaResponse
from backend.notifications import disparar_alerta_incendio
from typing import List

router = APIRouter()

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
    nivel = "VERDE"
    if lectura.temperatura > 50 or lectura.humo_ppm > 200:
        nivel = "AMARILLO"
    if lectura.temperatura > 70 or lectura.humo_ppm > 500:
        nivel = "ROJO"

    nueva_lectura = Lectura(**lectura.model_dump(), nivel_alerta=nivel)
    db.add(nueva_lectura)

    # Si llego GPS valido, actualiza la posicion del sensor en el mapa
    if lectura.latitud is not None and lectura.longitud is not None:
        sensor = db.query(Sensor).filter(Sensor.id == lectura.sensor_id).first()
        if sensor:
            sensor.latitud = lectura.latitud
            sensor.longitud = lectura.longitud

    if nivel == "ROJO":
        alerta = Alerta(
            sensor_id=lectura.sensor_id,
            tipo="INCENDIO",
            mensaje=f"🔥 Alerta crítica: Temperatura {lectura.temperatura}°C, Humo {lectura.humo_ppm}ppm"
        )
        db.add(alerta)

    db.commit()
    db.refresh(nueva_lectura)
    return nueva_lectura

# ─── LISTAR LECTURAS POR SENSOR ───────────
@router.get("/{sensor_id}/lecturas", response_model=List[LecturaResponse])
def listar_lecturas(sensor_id: int, db: Session = Depends(get_db)):
    return db.query(Lectura).filter(Lectura.sensor_id == sensor_id).all()