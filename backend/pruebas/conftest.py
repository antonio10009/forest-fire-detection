# Pruebas del servidor v3 en el PC, con SQLite y sin mandar nada de verdad (WhatsApp simulado).
# Uso, desde la carpeta del proyecto:
#   pip install pytest httpx
#   python -m pytest backend/pruebas -q
import os
import sys
import tempfile

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, RAIZ)
_db = os.path.join(tempfile.mkdtemp(prefix="ff_pruebas_"), "pruebas.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_db}"
os.environ["DEVICE_API_KEY"] = "clave-padres"
os.environ["ADMIN_API_KEY"] = "clave-admin"
for v in ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_MSG_SVC_SID", "TWILIO_FROM_WA", "TWILIO_CONTENT_SID",
          "TWILIO_CONTENT_SID_TECNICO", "AVISOS_TECNICOS_WA", "PERMITIR_LECTURA_SIN_CLAVE"):
    os.environ.pop(v, None)

import threading  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from backend import avisos_v3  # noqa: E402
from backend.database import Base, SessionLocal, engine  # noqa: E402
from backend.main import app  # noqa: E402
from backend.models.suscriptor import Suscriptor  # noqa: E402

CLAVE = {"X-Api-Key": "clave-padres"}
ADMIN = {"X-Admin-Key": "clave-admin"}


class Envios:
    """Reemplaza a Twilio: guarda lo que se habría mandado por WhatsApp."""
    def __init__(self):
        self.lock = threading.Lock()
        self.wa = []          # (numero, texto, variables, content_sid)
        self.wa_ok = True

    def whatsapp(self, numero, texto, variables=None, content_sid="", al_crear=None):
        with self.lock:
            self.wa.append((numero, texto, variables, content_sid))
            sid = f"SMprueba{len(self.wa)}"
        if al_crear and self.wa_ok:
            al_crear(numero, sid)
        return self.wa_ok

    def total(self):
        return len(self.wa)

    def esperar(self, n, segundos=3.0):
        """Los avisos técnicos salen en segundo plano: espera a que haya al menos n envíos."""
        import time
        fin = time.monotonic() + segundos
        while self.total() < n and time.monotonic() < fin:
            time.sleep(0.01)
        return self.total() >= n


@pytest.fixture
def envios(monkeypatch):
    e = Envios()
    monkeypatch.setattr(avisos_v3, "_enviar_whatsapp", e.whatsapp)
    monkeypatch.setattr(avisos_v3, "whatsapp_configurado", lambda: True)
    return e


@pytest.fixture
def cliente():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    return TestClient(app)          # sin "with": no arranca la vigilancia de fondo


@pytest.fixture
def db(cliente):
    s = SessionLocal()
    yield s
    s.close()


def suscribir(db, *numeros):
    for n in numeros:
        db.add(Suscriptor(numero_wa=n, activo=True))
    db.commit()
