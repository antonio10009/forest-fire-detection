"""
============================================================
PASO 14 - Endpoint de predicción con IA
Archivo: backend/routers/ml.py
============================================================

Agrega este router en backend/main.py:
    from backend.routers import ml
    app.include_router(ml.router, prefix="/api/ml", tags=["IA"])
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import joblib
import os
import numpy as np

router = APIRouter()

# ── RUTA DEL MODELO ───────────────────────────────────────────
MODEL_PATH = "backend/ml/modelo_incendio.pkl"

# Cargar el modelo al arrancar el servidor (una sola vez)
_modelo = None

def get_modelo():
    global _modelo
    if _modelo is None:
        if not os.path.exists(MODEL_PATH):
            raise HTTPException(
                status_code=503,
                detail=f"Modelo no encontrado en {MODEL_PATH}. Ejecuta train_model.py primero."
            )
        _modelo = joblib.load(MODEL_PATH)
    return _modelo

# ── SCHEMAS ───────────────────────────────────────────────────
class PrediccionInput(BaseModel):
    temperatura: float
    humo_ppm: float
    humedad: float

class PrediccionResponse(BaseModel):
    nivel_predicho: str
    confianza_porcentaje: float
    probabilidades: dict
    es_emergencia: bool
    mensaje: str

# ── ENDPOINT ──────────────────────────────────────────────────
@router.post("/predecir", response_model=PrediccionResponse)
def predecir_nivel(datos: PrediccionInput):
    """
    Recibe temperatura, humo_ppm y humedad.
    Devuelve el nivel de alerta predicho por el modelo de IA
    junto con la confianza y probabilidades por clase.
    """
    modelo = get_modelo()

    # Validar que el DHT22 no está fallando
    if datos.temperatura == 0 and datos.humedad == 0:
        return PrediccionResponse(
            nivel_predicho="ERROR_SENSOR",
            confianza_porcentaje=0.0,
            probabilidades={"VERDE": 0, "AMARILLO": 0, "ROJO": 0},
            es_emergencia=False,
            mensaje="DHT22 sin lectura válida, ignorando esta muestra."
        )

    X = np.array([[datos.temperatura, datos.humo_ppm, datos.humedad]])

    nivel = modelo.predict(X)[0]
    probas = modelo.predict_proba(X)[0]
    clases = modelo.classes_

    probabilidades = {
        clase: round(float(prob) * 100, 1)
        for clase, prob in zip(clases, probas)
    }

    confianza = round(float(max(probas)) * 100, 1)
    es_emergencia = nivel == "ROJO"

    mensajes = {
        "VERDE": "Condiciones normales. Sin riesgo detectado.",
        "AMARILLO": "Condiciones anómalas. Monitorear de cerca.",
        "ROJO": "🔥 ALERTA: Alta probabilidad de incendio forestal."
    }

    return PrediccionResponse(
        nivel_predicho=nivel,
        confianza_porcentaje=confianza,
        probabilidades=probabilidades,
        es_emergencia=es_emergencia,
        mensaje=mensajes[nivel]
    )

@router.get("/info")
def info_modelo():
    """Devuelve información sobre el modelo cargado."""
    modelo = get_modelo()
    return {
        "tipo": type(modelo).__name__,
        "clases": list(modelo.classes_),
        "n_estimadores": modelo.n_estimators,
        "features": ["temperatura", "humo_ppm", "humedad"],
        "estado": "activo"
    }
