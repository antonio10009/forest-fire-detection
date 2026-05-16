from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models.sensor import Alerta
from backend.schemas.schemas import AlertaResponse
from typing import List

router = APIRouter()

# ─── LISTAR ALERTAS ACTIVAS ───────────────
@router.get("/", response_model=List[AlertaResponse])
def listar_alertas(db: Session = Depends(get_db)):
    return db.query(Alerta).filter(Alerta.activa == True).all()

# ─── LISTAR TODAS LAS ALERTAS ─────────────
@router.get("/historial", response_model=List[AlertaResponse])
def historial_alertas(db: Session = Depends(get_db)):
    return db.query(Alerta).order_by(Alerta.creada_en.desc()).all()

# ─── DESACTIVAR ALERTA ────────────────────
@router.put("/{alerta_id}/desactivar")
def desactivar_alerta(alerta_id: int, db: Session = Depends(get_db)):
    alerta = db.query(Alerta).filter(Alerta.id == alerta_id).first()
    if not alerta:
        return {"error": "Alerta no encontrada"}
    alerta.activa = False
    db.commit()
    return {"mensaje": "Alerta desactivada correctamente"}