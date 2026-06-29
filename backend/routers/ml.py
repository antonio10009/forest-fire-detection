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

"""
============================================================
PASO 15 - Endpoint de Anomaly Detection
INSTRUCCIÓN: Agrega este código AL FINAL de backend/routers/ml.py
(no reemplaces el archivo, solo añade al final)
============================================================
"""

# ── RUTAS DE LOS MODELOS DE ANOMALIA ─────────────────────────
ANOMALY_MODEL_PATH  = "backend/ml/modelo_anomalia.pkl"
ANOMALY_SCALER_PATH = "backend/ml/scaler_anomalia.pkl"

_modelo_anomalia = None
_scaler_anomalia = None

def get_anomaly_modelo():
    global _modelo_anomalia, _scaler_anomalia
    if _modelo_anomalia is None:
        if not os.path.exists(ANOMALY_MODEL_PATH):
            raise HTTPException(
                status_code=503,
                detail="Modelo anomalia no encontrado. Ejecuta train_anomaly.py primero."
            )
        _modelo_anomalia = joblib.load(ANOMALY_MODEL_PATH)
        _scaler_anomalia = joblib.load(ANOMALY_SCALER_PATH)
    return _modelo_anomalia, _scaler_anomalia

# ── SCHEMA RESPUESTA ANOMALIA ─────────────────────────────────
class AnomaliaResponse(BaseModel):
    es_anomalia: bool
    score_anomalia: float
    nivel_riesgo: str
    mensaje: str
    temperatura: float
    humo_ppm: float
    humedad: float

# ── ENDPOINT ANOMALY DETECTION ────────────────────────────────
@router.post("/anomalia", response_model=AnomaliaResponse)
def detectar_anomalia(datos: PrediccionInput):
    """
    Detecta si una lectura de sensores es anómala comparada
    con el comportamiento normal aprendido del historial.

    Complementa al clasificador del paso 14:
    - El clasificador dice QUÉ nivel es (VERDE/AMARILLO/ROJO)
    - El detector de anomalías dice si el comportamiento es INUSUAL
      aunque no supere los umbrales de alerta

    Score de anomalía: cuanto más negativo, más anómalo.
    Umbral típico: valores menores a -0.60 indican anomalía.
    """
    if datos.temperatura == 0 and datos.humedad == 0:
        return AnomaliaResponse(
            es_anomalia=False,
            score_anomalia=0.0,
            nivel_riesgo="ERROR_SENSOR",
            mensaje="DHT22 sin lectura válida, no se puede evaluar.",
            temperatura=datos.temperatura,
            humo_ppm=datos.humo_ppm,
            humedad=datos.humedad
        )

    modelo, scaler = get_anomaly_modelo()

    X = np.array([[datos.temperatura, datos.humo_ppm, datos.humedad]])
    X_scaled = scaler.transform(X)

    pred = modelo.predict(X_scaled)[0]
    score = float(modelo.score_samples(X_scaled)[0])
    es_anomalia = pred == -1

    # Nivel de riesgo basado en el score
    if not es_anomalia:
        nivel_riesgo = "NORMAL"
        mensaje = "Comportamiento dentro de los parámetros normales históricos."
    elif score > -0.65:
        nivel_riesgo = "SOSPECHOSO"
        mensaje = "Comportamiento ligeramente inusual. Monitorear."
    elif score > -0.70:
        nivel_riesgo = "ANOMALO"
        mensaje = "⚠️ Comportamiento anómalo detectado. Verificar sensores."
    else:
        nivel_riesgo = "CRITICO"
        mensaje = "🔥 Anomalía crítica. Alta probabilidad de incendio o falla."

    return AnomaliaResponse(
        es_anomalia=es_anomalia,
        score_anomalia=round(score, 4),
        nivel_riesgo=nivel_riesgo,
        mensaje=mensaje,
        temperatura=datos.temperatura,
        humo_ppm=datos.humo_ppm,
        humedad=datos.humedad
    )

