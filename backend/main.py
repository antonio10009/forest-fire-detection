from fastapi import FastAPI
from backend.database import engine, Base

# Importar modelos para que SQLAlchemy los registre
from backend.models.sensor import Sensor, Lectura, Alerta

# Crear todas las tablas en PostgreSQL
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="🔥 Forest Fire Detection API",
    description="Sistema IoT de detección temprana de incendios forestales",
    version="1.0.0"
)

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