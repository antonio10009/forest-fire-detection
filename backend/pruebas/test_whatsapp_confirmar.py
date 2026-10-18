# Twilio a veces acepta el mensaje y lo marca fallido después (ej. 21703: el Messaging Service no tiene número).
# El servidor tiene que darse cuenta para que el padre avise directo.
import time
from types import SimpleNamespace

from backend import avisos_v3
from conftest import CLAVE, suscribir
from test_red_v3 import alerta


class TwilioFalso:
    """Imita client.messages: create() devuelve el primer estado y cada fetch() el siguiente."""
    def __init__(self, *estados, error=None, fetch_falla=False):
        self.estados = list(estados)
        self.error = error
        self.fetch_falla = fetch_falla
        self.creados = 0
        self.consultas = 0

    def _mensaje(self):
        estado = self.estados.pop(0) if len(self.estados) > 1 else self.estados[0]
        return SimpleNamespace(sid="SM1", status=estado, error_code=self.error if estado == "failed" else None)

    def create(self, **kw):
        self.creados += 1
        return self._mensaje()

    def __call__(self, sid):
        def fetch():
            self.consultas += 1
            if self.fetch_falla:
                raise RuntimeError("sin conexión")
            return self._mensaje()
        return SimpleNamespace(fetch=fetch)


def usar(monkeypatch, falso):
    monkeypatch.setenv("TWILIO_FROM_WA", "whatsapp:+14155238886")
    monkeypatch.setattr(avisos_v3, "_cliente_twilio", lambda: SimpleNamespace(messages=falso))
    monkeypatch.setattr(avisos_v3, "CONFIRMAR_PASO_S", 0.01)
    monkeypatch.setattr(avisos_v3, "CONFIRMAR_S", 0.2)


def test_falla_despues_de_aceptado(monkeypatch):
    falso = TwilioFalso("accepted", "failed", error=21703)
    usar(monkeypatch, falso)
    assert avisos_v3._enviar_whatsapp("+56911111111", "hola") is False
    assert falso.consultas == 1


def test_sale_bien(monkeypatch):
    falso = TwilioFalso("queued", "sent")
    usar(monkeypatch, falso)
    assert avisos_v3._enviar_whatsapp("+56911111111", "hola") is True


def test_sin_estado_definitivo_se_da_por_enviado(monkeypatch):
    falso = TwilioFalso("queued")
    usar(monkeypatch, falso)
    assert avisos_v3._enviar_whatsapp("+56911111111", "hola") is True
    assert falso.consultas >= 1


def test_si_no_se_puede_consultar_se_da_por_enviado(monkeypatch):
    falso = TwilioFalso("queued", fetch_falla=True)
    usar(monkeypatch, falso)
    assert avisos_v3._enviar_whatsapp("+56911111111", "hola") is True


def test_alerta_con_messaging_service_sin_numero_hace_avisar_al_padre(cliente, db, monkeypatch):
    suscribir(db, "+56911111111")
    usar(monkeypatch, TwilioFalso("accepted", "failed", error=21703))
    r = cliente.post("/api/v3/alerta", headers=CLAVE, json=alerta())
    assert r.status_code == 502          # el padre avisa directo por su secrets.h
    fin = time.monotonic() + 2           # el resultado se guarda en segundo plano
    while "0/1" not in (cliente.get("/api/v3/alertas").json()[0]["estado_aviso"] or "") and time.monotonic() < fin:
        time.sleep(0.02)
    assert "WhatsApp 0/1" in cliente.get("/api/v3/alertas").json()[0]["estado_aviso"]
