# backend/models/red.py
# Tablas de la red v3 (padres e hijos ESP-NOW). Son tablas nuevas: create_all las crea
# sin tocar sensores/lecturas/alertas, que siguen igual para la web actual.

from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, ForeignKey, Index
from backend.database import Base
from backend.horario import ahora_utc


class NodoRed(Base):
    """Estado actual de cada padre o hijo (una fila por NODO_ID)."""
    __tablename__ = "red_nodos"

    id            = Column(Integer, primary_key=True, index=True)
    codigo        = Column(String(32), unique=True, nullable=False, index=True)  # NODO_ID del config.h
    tipo          = Column(String(10), nullable=False)          # "padre" | "hijo"
    mac           = Column(String(17))
    sensor_id     = Column(Integer, ForeignKey("sensores.id"), nullable=True)   # fila en la tabla vieja (mapa y gráficos)
    ubicacion     = Column(String(200))                         # texto libre, se edita con PUT /api/v3/nodos/{codigo}

    # enlace (hijos)
    padre         = Column(String(32))                          # padre que lo reportó por última vez
    en_respaldo   = Column(Boolean, default=False)              # está usando su padre de RESPALDO
    respaldo_desde = Column(DateTime)
    cambios_padre = Column(Integer)
    rssi          = Column(Integer)
    entrega_pct   = Column(Float)

    # sensores
    temperatura   = Column(Float)
    humedad       = Column(Float)
    gas           = Column(Integer)
    gas_base      = Column(Integer)
    nivel         = Column(String(10), default="VERDE")
    riesgo        = Column(String(12))
    llama         = Column(Boolean, default=False)
    calentando    = Column(Boolean, default=False)
    bateria_mv    = Column(Integer)
    latitud       = Column(Float)
    longitud      = Column(Float)
    coord_manual  = Column(Boolean, default=False)              # coordenadas puestas a mano: el latido no las pisa

    # solo padres
    fw            = Column(String(20))
    uptime_s      = Column(Integer)
    wifi_rssi     = Column(Integer)
    canal         = Column(Integer)
    modo_prueba   = Column(Boolean)
    hijos         = Column(Integer)

    ultimo_visto  = Column(DateTime, index=True)                # UTC
    ultima_lectura = Column(DateTime)                           # última fila guardada en "lecturas"

    # avisos técnicos ya enviados (para no repetirlos)
    sin_senal       = Column(Boolean, default=False)
    aviso_respaldo  = Column(Boolean, default=False)
    bateria_baja    = Column(Boolean, default=False)

    creado_en     = Column(DateTime, default=ahora_utc)


class AlertaRed(Base):
    """Cada aviso que mandó un padre (incendio o prueba). Una fila por aviso, aunque llegue repetido."""
    __tablename__ = "red_alertas"

    id             = Column(Integer, primary_key=True, index=True)
    nodo           = Column(String(32), nullable=False)        # de dónde salió (hijo o el mismo padre)
    padre          = Column(String(32))                        # primer padre que la reportó
    padres         = Column(String(120), default="")           # todos los padres que la reportaron
    mac            = Column(String(17))
    tipo           = Column(String(16), nullable=False)        # incendio | prueba_enlace | boton_padre
    prueba         = Column(Boolean, default=False)
    recordatorio   = Column(Boolean, default=False)
    arranque_id    = Column(Integer, nullable=False)
    alerta_id      = Column(Integer, nullable=False)

    temperatura    = Column(Float)
    humedad        = Column(Float)
    gas            = Column(Integer)
    gas_base       = Column(Integer)
    gas_umbral     = Column(Integer)
    riesgo         = Column(String(12))
    rssi           = Column(Integer)
    padre_respaldo = Column(Boolean, default=False)
    latitud        = Column(Float)
    longitud       = Column(Float)
    coord_del_padre = Column(Boolean, default=False)
    bateria_mv     = Column(Integer)
    ms_llama_confirm = Column(Integer)
    ms_radio       = Column(Integer)
    ms_padre       = Column(Integer)
    hora_padre     = Column(String(12))

    recibida_en    = Column(DateTime, default=ahora_utc, index=True)   # UTC
    veces          = Column(Integer, default=0)                # cuántas veces llegó (reintentos o por dos padres)
    avisada        = Column(Boolean, default=False)            # alguien (servidor o padre) ya mandó el aviso
    enviando       = Column(Boolean, default=False)
    estado_aviso   = Column(String(300))                       # ej. "WhatsApp 3/3 con plantilla"
    alerta_web_id  = Column(Integer, ForeignKey("alertas.id"), nullable=True)

    __table_args__ = (Index("ix_red_alertas_clave", "nodo", "arranque_id", "alerta_id", "tipo"),)


class EnvioWhatsApp(Base):
    """Cada WhatsApp de un aviso y lo que Twilio informó después: así se mide cuánto tardó en llegar al celular."""
    __tablename__ = "red_envios"

    id           = Column(Integer, primary_key=True, index=True)
    alerta_id    = Column(Integer, ForeignKey("red_alertas.id"), nullable=True, index=True)
    numero       = Column(String(20))
    sid          = Column(String(40), unique=True, nullable=False, index=True)   # id del mensaje en Twilio
    estado       = Column(String(20))                       # sent, delivered, read, failed...
    error        = Column(String(10))
    creado_en    = Column(DateTime, default=ahora_utc)       # UTC, como todas las fechas
    enviado_en   = Column(DateTime)                         # Twilio lo entregó a WhatsApp
    entregado_en = Column(DateTime)                         # llegó al celular
    leido_en     = Column(DateTime)                         # la persona lo abrió
