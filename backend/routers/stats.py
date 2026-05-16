from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date
from backend.database import get_db
from backend.models.sensor import Lectura, Alerta, Sensor

router = APIRouter()

# ─── RESUMEN GENERAL ──────────────────────
@router.get("/resumen")
def resumen_general(db: Session = Depends(get_db)):
    total_sensores  = db.query(Sensor).filter(Sensor.activo == True).count()
    total_alertas   = db.query(Alerta).filter(Alerta.activa == True).count()
    total_lecturas  = db.query(Lectura).count()
    alertas_hoy     = db.query(Alerta).filter(
        cast(Alerta.creada_en, Date) == func.current_date()
    ).count()

    return {
        "total_sensores":  total_sensores,
        "alertas_activas": total_alertas,
        "total_lecturas":  total_lecturas,
        "alertas_hoy":     alertas_hoy,
    }

# ─── ALERTAS POR DÍA ──────────────────────
@router.get("/alertas-por-dia")
def alertas_por_dia(db: Session = Depends(get_db)):
    resultados = db.query(
        cast(Alerta.creada_en, Date).label("fecha"),
        func.count(Alerta.id).label("total")
    ).group_by(
        cast(Alerta.creada_en, Date)
    ).order_by(
        cast(Alerta.creada_en, Date)
    ).limit(30).all()

    return [{"fecha": str(r.fecha), "total": r.total} for r in resultados]

# ─── TEMPERATURA PROMEDIO POR SENSOR ──────
@router.get("/temperatura-promedio")
def temperatura_promedio(db: Session = Depends(get_db)):
    resultados = db.query(
        Lectura.sensor_id,
        func.avg(Lectura.temperatura).label("temp_promedio"),
        func.avg(Lectura.humo_ppm).label("humo_promedio"),
        func.max(Lectura.temperatura).label("temp_max"),
    ).group_by(Lectura.sensor_id).all()

    return [{
        "sensor_id":    r.sensor_id,
        "temp_promedio": round(r.temp_promedio, 2),
        "humo_promedio": round(r.humo_promedio, 2),
        "temp_max":      round(r.temp_max, 2),
    } for r in resultados]

# ─── NIVELES DE ALERTA ────────────────────
@router.get("/niveles")
def niveles_alerta(db: Session = Depends(get_db)):
    resultados = db.query(
        Lectura.nivel_alerta,
        func.count(Lectura.id).label("total")
    ).group_by(Lectura.nivel_alerta).all()

    return [{"nivel": r.nivel_alerta, "total": r.total} for r in resultados]

# ─── ZONA MÁS CRÍTICA ─────────────────────
@router.get("/zona-critica")
def zona_critica(db: Session = Depends(get_db)):
    resultado = db.query(
        Sensor.nombre,
        Sensor.ubicacion,
        func.count(Alerta.id).label("total_alertas")
    ).join(
        Alerta, Alerta.sensor_id == Sensor.id
    ).group_by(
        Sensor.id, Sensor.nombre, Sensor.ubicacion
    ).order_by(
        func.count(Alerta.id).desc()
    ).first()

    if not resultado:
        return {"mensaje": "Sin datos suficientes"}

    return {
        "nombre":        resultado.nombre,
        "ubicacion":     resultado.ubicacion,
        "total_alertas": resultado.total_alertas
    }