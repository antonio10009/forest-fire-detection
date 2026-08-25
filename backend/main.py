# backend/main.py actualizado
# Agregar el router de configuración

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.database import engine, Base
from backend.models.sensor import Sensor, Lectura, Alerta
from backend.models.config import Configuracion
from backend.routers import sensors, alerts, stats, config
from backend.routers import ml

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="🔥 Forest Fire Detection API",
    description="Sistema IoT de detección temprana de incendios forestales",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sensors.router, prefix="/api/sensors", tags=["Sensores"])
app.include_router(alerts.router,  prefix="/api/alerts",  tags=["Alertas"])
app.include_router(stats.router,   prefix="/api/stats",   tags=["Estadísticas"])
app.include_router(ml.router,      prefix="/api/ml",      tags=["IA"])
app.include_router(config.router,  prefix="/api/config",  tags=["Configuración"])

@app.get("/")
def root():
    return {
        "mensaje": "🔥 Forest Fire Detection API funcionando",
        "version": "2.0.0",
        "estado": "activo"
    }

@app.get("/health")
def health_check():
    return {"estado": "ok"}