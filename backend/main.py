from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.database import engine, Base
from backend.models.sensor import Sensor, Lectura, Alerta
from backend.routers import sensors, alerts

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="🔥 Forest Fire Detection API",
    description="Sistema IoT de detección temprana de incendios forestales",
    version="1.0.0"
)

# CORS para que el dashboard pueda conectarse
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sensors.router, prefix="/api/sensors", tags=["Sensores"])
app.include_router(alerts.router,  prefix="/api/alerts",  tags=["Alertas"])

@app.get("/")
def root():
    return {
        "mensaje": "🔥 Forest Fire Detection API funcionando",
        "version": "1.0.0",
        "estado": "activo"
    }

@app.get("/health")
def health_check():
    return {"estado": "ok"}