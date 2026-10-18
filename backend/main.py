# backend/main.py
# v3: rutas /api/v3 para los padres ESP-NOW, vigilancia de nodos sin señal y claves en las rutas que cambian datos

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.database import engine, Base
from backend.models.sensor import Sensor, Lectura, Alerta
from backend.models.config import Configuracion
from backend.models.suscriptor import Suscriptor
from backend.models.red import NodoRed, AlertaRed
from backend.routers import sensors, alerts, stats, config
from backend.routers import ml
from backend.routers import suscriptores
from backend.routers import red

Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    vigilancia = asyncio.create_task(red.vigilar())     # avisa si un nodo o un padre deja de reportar
    yield
    vigilancia.cancel()


app = FastAPI(
    title="🔥 Forest Fire Detection API",
    description="Sistema IoT de detección temprana de incendios forestales",
    version="3.0.0",
    lifespan=lifespan,
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
app.include_router(suscriptores.router, prefix="/api/suscriptores", tags=["Suscriptores"])
app.include_router(red.router,     prefix="/api/v3",      tags=["Red v3 (padres e hijos)"])

@app.get("/")
def root():
    return {
        "mensaje": "🔥 Forest Fire Detection API funcionando",
        "version": "3.0.0",
        "estado": "activo"
    }

@app.get("/health")
def health_check():
    return {"estado": "ok"}