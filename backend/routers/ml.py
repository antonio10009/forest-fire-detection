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

"""
============================================================
PASO 16 - Endpoint de Predicción de Propagación
INSTRUCCIÓN: Agrega este código AL FINAL de backend/routers/ml.py
============================================================
"""

import math as _math

# ── SCHEMAS ───────────────────────────────────────────────────
class PropagacionInput(BaseModel):
    latitud: float
    longitud: float
    temperatura: float
    humedad: float
    viento_velocidad: float  # km/h
    viento_direccion: float  # grados (0=Norte, 90=Este, 180=Sur, 270=Oeste)
    minutos: int = 30        # proyección en minutos (default 30 min)

class PropagacionResponse(BaseModel):
    zona_riesgo: dict        # GeoJSON Feature con el polígono
    centro: dict             # lat/lng del foco
    parametros: dict         # parámetros usados
    peligro: str
    area_hectareas: float
    ros_m_por_min: float
    mensaje: str

# ── FUNCIÓN DEL MODELO FÍSICO ─────────────────────────────────
def _calcular_elipse_propagacion(
    lat: float, lng: float,
    temperatura: float, humedad: float,
    viento_velocidad: float, viento_direccion: float,
    minutos: int
) -> dict:
    """
    Modelo de elipse de propagación basado en McArthur Forest Fire
    Danger Index, adaptado para condiciones de Chile central.
    """
    # Factores de propagación
    factor_temp   = max(0.1, (temperatura - 10) / 20) if temperatura > 10 else 0.1
    factor_hum    = max(0.1, (100 - humedad) / 100)
    factor_viento = 1 + (viento_velocidad / 20)

    # Tasas de propagación en m/min
    ros_cabeza = 5 * factor_temp * factor_hum * factor_viento
    ros_flanco = ros_cabeza * 0.4
    ros_cola   = ros_cabeza * 0.1

    # Distancias en metros
    dist_cabeza = ros_cabeza * minutos
    dist_flanco = ros_flanco * minutos

    # Generar polígono elíptico rotado según dirección del viento
    dir_rad = _math.radians(viento_direccion)
    metros_por_lat = 111320
    metros_por_lng = 111320 * _math.cos(_math.radians(lat))

    puntos = []
    for i in range(36):
        angulo = 2 * _math.pi * i / 36
        if _math.cos(angulo) >= 0:
            rx = dist_cabeza * _math.cos(angulo)
        else:
            rx = (ros_cola * minutos) * abs(_math.cos(angulo)) * (-1)
        ry = dist_flanco * _math.sin(angulo)
        x_rot = rx * _math.cos(dir_rad) - ry * _math.sin(dir_rad)
        y_rot = rx * _math.sin(dir_rad) + ry * _math.cos(dir_rad)
        puntos.append([
            lng + (x_rot / metros_por_lng),
            lat + (y_rot / metros_por_lat)
        ])
    puntos.append(puntos[0])

    area_ha = (_math.pi * dist_cabeza * dist_flanco) / 10000

    return {
        "ros_cabeza": round(ros_cabeza, 2),
        "dist_cabeza": round(dist_cabeza, 0),
        "dist_flanco": round(dist_flanco, 0),
        "area_ha": round(area_ha, 2),
        "puntos": puntos
    }

# ── ENDPOINT ──────────────────────────────────────────────────
@router.post("/propagacion", response_model=PropagacionResponse)
def predecir_propagacion(datos: PropagacionInput):
    """
    Predice la zona de propagación de un incendio forestal.

    Usa el modelo de elipse de Huygens basado en McArthur FFDI,
    el mismo estándar que usa CONAF para predicción de incendios.

    Devuelve un GeoJSON que puede pintarse directamente en el mapa
    como zona de riesgo con color según nivel de peligro.

    Dirección del viento: 0=Norte, 90=Este, 180=Sur, 270=Oeste
    """
    resultado = _calcular_elipse_propagacion(
        lat=datos.latitud,
        lng=datos.longitud,
        temperatura=datos.temperatura,
        humedad=datos.humedad,
        viento_velocidad=datos.viento_velocidad,
        viento_direccion=datos.viento_direccion,
        minutos=datos.minutos
    )

    area_ha = resultado['area_ha']
    ros = resultado['ros_cabeza']

    # Nivel de peligro
    if area_ha < 1:
        peligro = "BAJO"
        color = "#FFFF00"
    elif area_ha < 10:
        peligro = "MODERADO"
        color = "#FFA500"
    elif area_ha < 50:
        peligro = "ALTO"
        color = "#FF4500"
    else:
        peligro = "EXTREMO"
        color = "#CC0000"

    mensajes = {
        "BAJO":     f"Propagación lenta. ~{area_ha} ha en {datos.minutos} min.",
        "MODERADO": f"Propagación moderada. ~{area_ha} ha en {datos.minutos} min. Evacuar zona.",
        "ALTO":     f"⚠️ Propagación rápida. ~{area_ha} ha en {datos.minutos} min. Evacuar URGENTE.",
        "EXTREMO":  f"🔥 Propagación EXTREMA. ~{area_ha} ha en {datos.minutos} min. EMERGENCIA MÁXIMA."
    }

    zona_geojson = {
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [resultado['puntos']]
        },
        "properties": {
            "peligro": peligro,
            "color": color,
            "area_hectareas": area_ha,
            "minutos": datos.minutos,
            "ros_m_min": ros,
            "dist_frente_m": resultado['dist_cabeza'],
            "dist_flanco_m": resultado['dist_flanco']
        }
    }

    return PropagacionResponse(
        zona_riesgo=zona_geojson,
        centro={"lat": datos.latitud, "lng": datos.longitud},
        parametros={
            "temperatura": datos.temperatura,
            "humedad": datos.humedad,
            "viento_velocidad_kmh": datos.viento_velocidad,
            "viento_direccion_grados": datos.viento_direccion,
            "minutos_proyeccion": datos.minutos
        },
        peligro=peligro,
        area_hectareas=area_ha,
        ros_m_por_min=ros,
        mensaje=mensajes[peligro]
    )
