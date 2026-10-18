# El servidor mide cuántos segundos tarda cada aviso en llegar al celular: Twilio le informa
# "sent", "delivered" y "read" de cada WhatsApp en /api/v3/twilio/estado.
import time
from datetime import timedelta
from types import SimpleNamespace
from urllib.parse import urlencode

from twilio.request_validator import RequestValidator

from backend import avisos_v3
from backend.models.red import AlertaRed, EnvioWhatsApp
from backend.routers import red
from conftest import CLAVE, suscribir
from test_red_v3 import alerta

URL = "https://forest-fire.onrender.com/api/v3/twilio/estado"
TOKEN = "token-de-prueba"


def configurar(monkeypatch):
    monkeypatch.setenv("RENDER_EXTERNAL_URL", "https://forest-fire.onrender.com")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", TOKEN)


def informar(cliente, sid, estado, error=None, firma=None):
    datos = {"MessageSid": sid, "MessageStatus": estado, "To": "whatsapp:+56911111111"}
    if error:
        datos["ErrorCode"] = error
    firma = firma or RequestValidator(TOKEN).compute_signature(URL, datos)
    return cliente.post("/api/v3/twilio/estado", content=urlencode(datos),
                        headers={"Content-Type": "application/x-www-form-urlencoded", "X-Twilio-Signature": firma})


def a_los(monkeypatch, db, segundos):
    """Los estados que lleguen ahora quedan `segundos` después de que el servidor recibió la alerta."""
    recibida = db.query(AlertaRed).one().recibida_en
    monkeypatch.setattr(red, "ahora_utc", lambda: recibida + timedelta(seconds=segundos))


def test_url_publica(monkeypatch):
    monkeypatch.delenv("URL_PUBLICA", raising=False)
    monkeypatch.setenv("RENDER_EXTERNAL_URL", "https://forest-fire.onrender.com/")
    assert avisos_v3.url_estado() == URL
    monkeypatch.setenv("RENDER_EXTERNAL_URL", "http://localhost:8000")
    assert avisos_v3.url_estado() == ""
    monkeypatch.setenv("URL_PUBLICA", "https://otro.cl")
    assert avisos_v3.url_estado() == "https://otro.cl/api/v3/twilio/estado"


def test_pide_el_estado_solo_para_los_avisos(monkeypatch):
    configurar(monkeypatch)
    monkeypatch.setenv("TWILIO_FROM_WA", "whatsapp:+14155238886")
    pedidos = []

    def create(**kw):
        pedidos.append(kw)
        return SimpleNamespace(sid=f"SM{len(pedidos)}", status="sent")

    monkeypatch.setattr(avisos_v3, "_cliente_twilio", lambda: SimpleNamespace(messages=SimpleNamespace(create=create)))
    creados = []
    assert avisos_v3._enviar_whatsapp("+56911111111", "hola", al_crear=lambda n, sid: creados.append((n, sid)))
    assert avisos_v3._enviar_whatsapp("+56911111111", "aviso técnico")
    assert pedidos[0]["status_callback"] == URL
    assert "status_callback" not in pedidos[1]
    assert creados == [("+56911111111", "SM1")]


def test_segundos_hasta_el_celular(cliente, db, envios, monkeypatch):
    configurar(monkeypatch)
    suscribir(db, "+56911111111", "+56922222222")
    r = cliente.post("/api/v3/alerta", headers=CLAVE, json=alerta())
    assert r.status_code == 200
    fin = time.monotonic() + 2           # el segundo envío puede registrarse un poco después
    while db.query(EnvioWhatsApp).count() < 2 and time.monotonic() < fin:
        time.sleep(0.02)
    sids = [e.sid for e in db.query(EnvioWhatsApp).order_by(EnvioWhatsApp.id)]
    assert len(sids) == 2

    a_los(monkeypatch, db, 1.2)
    assert informar(cliente, sids[0], "sent").status_code == 204
    a_los(monkeypatch, db, 3.5)
    assert informar(cliente, sids[0], "delivered").status_code == 204
    a_los(monkeypatch, db, 6.0)
    assert informar(cliente, sids[1], "delivered").status_code == 204
    a_los(monkeypatch, db, 20.0)
    assert informar(cliente, sids[0], "read").status_code == 204

    a = cliente.get("/api/v3/alertas").json()[0]
    assert a["celular_s"] == 3.5 and a["ultimo_celular_s"] == 6.0
    assert a["celulares"] == "2/2"
    # alerta() trae ms_llama_confirm 2000, ms_radio 40 y ms_padre 3
    assert (a["deteccion_s"], a["radio_s"], a["padre_s"]) == (2.0, 0.04, 0.003)
    assert a["total_s"] == round(2.0 + 0.04 + 0.003 + 3.5, 2)
    e = db.query(EnvioWhatsApp).filter(EnvioWhatsApp.sid == sids[0]).one()
    db.refresh(e)
    assert e.estado == "read" and e.enviado_en and e.leido_en


def test_estados_desordenados_y_fallas(cliente, db, envios, monkeypatch):
    configurar(monkeypatch)
    # el estado llega antes de que el servidor registre el envío
    assert informar(cliente, "SMtemprano", "delivered").status_code == 204
    assert informar(cliente, "SMtemprano", "sent").status_code == 204
    red._registrar_envio(None, "+56911111111", "SMtemprano")
    e = db.query(EnvioWhatsApp).filter(EnvioWhatsApp.sid == "SMtemprano").one()
    assert e.estado == "delivered" and e.numero == "+56911111111"

    assert informar(cliente, "SMfalla", "failed", error="63016").status_code == 204
    assert informar(cliente, "SMfalla", "sent").status_code == 204
    e = db.query(EnvioWhatsApp).filter(EnvioWhatsApp.sid == "SMfalla").one()
    assert (e.estado, e.error) == ("failed", "63016")


def test_firma_invalida(cliente, db, monkeypatch):
    configurar(monkeypatch)
    assert informar(cliente, "SMx", "delivered", firma="falsa").status_code == 403
    monkeypatch.delenv("TWILIO_AUTH_TOKEN")
    assert informar(cliente, "SMx", "delivered").status_code == 403
    assert db.query(EnvioWhatsApp).count() == 0


def test_sin_estado_no_hay_segundos(cliente, db, envios):
    suscribir(db, "+56911111111")
    cliente.post("/api/v3/alerta", headers=CLAVE, json=alerta())
    a = cliente.get("/api/v3/alertas").json()[0]
    assert a["celular_s"] is None and a["total_s"] is None and a["celulares"] == "0/1"


def test_excel(cliente, db, envios, monkeypatch):
    configurar(monkeypatch)
    suscribir(db, "+56911111111")
    cliente.post("/api/v3/alerta", headers=CLAVE, json=alerta())
    sid = db.query(EnvioWhatsApp).one().sid
    a_los(monkeypatch, db, 2.75)
    informar(cliente, sid, "delivered")
    r = cliente.get("/api/v3/alertas.csv")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    texto = r.content.decode("utf-8")
    assert texto.startswith("﻿")
    encabezado, fila = texto.lstrip("﻿").splitlines()[:2]
    col = dict(zip(encabezado.split(";"), fila.split(";")))
    assert col["servidor_a_celular_s"] == "2,75"
    assert col["deteccion_s"] == "2,00" and col["celulares_que_recibieron"] == "1/1"
    assert col["total_s"] == "4,79"
