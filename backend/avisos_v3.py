# backend/avisos_v3.py
# Avisos de la red v3 por WhatsApp (Twilio). No se usa Telegram.
#
# A quién va cada aviso:
#   Incendio real               -> todos los suscriptores activos
#   Prueba (MODO_PRUEBA, botón) -> AVISOS_TECNICOS_WA (o todos los suscriptores si está vacío)
#   Técnico (sin señal, respaldo, batería) -> solo AVISOS_TECNICOS_WA
#
# Plantillas aprobadas (llegan aunque la persona no haya escrito al número en 24 h):
#   TWILIO_CONTENT_SID          incendios y pruebas, 5 variables (ver variables_plantilla)
#   TWILIO_CONTENT_SID_TECNICO  avisos técnicos, 1 variable con el texto
# Sin plantilla se manda el texto libre.
#
# Los envíos van en paralelo. enviar() espera hasta `plazo_s`: así el servidor solo le responde OK al
# padre cuando al menos un WhatsApp salió; si todos fallan, el padre avisa directo.

import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED

from backend.horario import a_local

_pool = ThreadPoolExecutor(max_workers=16, thread_name_prefix="aviso")
_twilio = None
_twilio_lock = threading.Lock()


def _env(nombre: str) -> str:
    return os.getenv(nombre, "").strip()


def _numeros(texto: str):
    return [n.strip().replace("whatsapp:", "") for n in texto.split(",") if n.strip()]


# ─── WhatsApp ─────────────────────────────────────────────────

def _cliente_twilio():
    global _twilio
    sid, token = _env("TWILIO_ACCOUNT_SID"), _env("TWILIO_AUTH_TOKEN")
    if not sid or not token or not (_env("TWILIO_MSG_SVC_SID") or _env("TWILIO_FROM_WA")):
        return None
    with _twilio_lock:
        if _twilio is None:
            from twilio.rest import Client
            from twilio.http.http_client import TwilioHttpClient
            _twilio = Client(sid, token, http_client=TwilioHttpClient(timeout=10))
    return _twilio


def whatsapp_configurado() -> bool:
    return _cliente_twilio() is not None


def plantilla(clase: str) -> str:
    """SID de la plantilla aprobada para esta clase de aviso ("" = texto libre)."""
    return _env("TWILIO_CONTENT_SID_TECNICO" if clase == "tecnico" else "TWILIO_CONTENT_SID")


def _enviar_whatsapp(numero: str, texto: str, variables=None, content_sid="") -> bool:
    cliente = _cliente_twilio()
    if cliente is None:
        return False
    kw = {"to": f"whatsapp:{numero}"}
    if _env("TWILIO_MSG_SVC_SID"):
        kw["messaging_service_sid"] = _env("TWILIO_MSG_SVC_SID")
    else:
        desde = _env("TWILIO_FROM_WA")
        kw["from_"] = desde if desde.startswith("whatsapp:") else f"whatsapp:{desde}"
    if content_sid and variables is not None:
        kw["content_sid"] = content_sid
        kw["content_variables"] = json.dumps(variables, ensure_ascii=False)
    else:
        kw["body"] = texto
    try:
        cliente.messages.create(**kw)
        return True
    except Exception as e:
        print(f"[WhatsApp v3] ❌ {numero}: {e}")
        return False


def destinos(db, clase: str):
    """clase: 'incendio' | 'prueba' | 'tecnico'. Devuelve la lista de números de WhatsApp."""
    from backend.models.suscriptor import Suscriptor
    if not whatsapp_configurado():
        return []
    tecnicos = _numeros(_env("AVISOS_TECNICOS_WA"))
    if clase == "incendio" or (clase == "prueba" and not tecnicos):
        numeros = [s.numero_wa for s in db.query(Suscriptor).filter(Suscriptor.activo == True).all()]  # noqa: E712
    else:
        numeros = tecnicos
    return sorted(set(numeros))


# ─── Envío con plazo ──────────────────────────────────────────

def enviar(numeros, texto, variables=None, content_sid="", plazo_s=5.0, al_terminar=None):
    """
    Manda a todos los números en paralelo y espera hasta plazo_s.
    Devuelve True (al menos uno salió), None (siguen en curso) o False (nada salió / no hay números).
    al_terminar(resumen) se llama cuando terminan todos, con un texto tipo "WhatsApp 3/3".
    """
    tareas = [_pool.submit(_enviar_whatsapp, n, texto, variables, content_sid) for n in numeros]
    if not tareas:
        if al_terminar:
            al_terminar("sin destinos (WhatsApp no configurado o sin números)")
        return False

    def esperar_todo():
        hechas, _ = wait(tareas)
        if al_terminar:
            try:
                al_terminar(f"WhatsApp {sum(1 for f in hechas if f.result())}/{len(tareas)}"
                            + (" con plantilla" if content_sid and variables is not None else ""))
            except Exception as e:
                print(f"[Avisos v3] no pude guardar el resultado: {e}")

    threading.Thread(target=esperar_todo, daemon=True).start()

    pendientes = set(tareas)
    limite = time.monotonic() + plazo_s
    while pendientes:
        resto = limite - time.monotonic()
        if resto <= 0:
            return None
        hechas, pendientes = wait(pendientes, timeout=resto, return_when=FIRST_COMPLETED)
        if any(f.result() for f in hechas):
            return True
    return False


# ─── Textos ───────────────────────────────────────────────────

_RIESGO = {
    "ALTO": "ALTO (humedad ≤ 30 %)", "MEDIO": "MEDIO (humedad 30-40 %)",
    "NORMAL": "NORMAL (humedad 40-70 %)", "BAJO": "BAJO (humedad > 70 %)",
}


def titulo_alerta(a) -> str:
    if a.tipo == "prueba_enlace":
        return "🧪 PRUEBA DE ENLACE - NO ES UN INCENDIO"
    if a.tipo == "boton_padre":
        return "🧪 PRUEBA (botón del padre) - NO ES UN INCENDIO"
    t = "🔥 ALERTA ROJA - INCENDIO FORESTAL"
    if a.recordatorio:
        t += " (el fuego sigue)"
    return ("🧪 PRUEBA — " + t) if a.prueba else t


def _num(v, dec=1, unidad=""):
    return "sin dato" if v is None else f"{v:.{dec}f}{unidad}"


def texto_alerta(a, ubicacion=None) -> str:
    hora = a_local(a.recibida_en).strftime("%d/%m/%Y %H:%M:%S")
    l = [titulo_alerta(a)]
    l.append(f"Nodo: {a.nodo}" + (f" — {ubicacion}" if ubicacion else ""))
    if a.padre and a.padre != a.nodo:
        l.append(f"Vía: {a.padre}" + (" (padre de respaldo)" if a.padre_respaldo else ""))
    l.append(f"🕐 {hora}")
    l.append("")
    if a.latitud is not None and a.longitud is not None:
        l.append(f"📍 {a.latitud:.6f},{a.longitud:.6f}" + (" (posición del padre)" if a.coord_del_padre else ""))
        l.append(f"https://maps.google.com/?q={a.latitud:.6f},{a.longitud:.6f}")
    else:
        l.append("📍 Sin coordenadas")
    l.append("")
    if a.tipo == "incendio":
        l.append("🔥 Llama IR: DETECTADA")
        if a.gas is not None:
            sube = (a.gas - a.gas_base) if a.gas_base is not None else None
            l.append(f"💨 Gas/humo: {a.gas}" + (f" (base {a.gas_base}, +{sube}, umbral +{a.gas_umbral})" if sube is not None else ""))
    l.append(f"🌡️ Temp: {_num(a.temperatura, 1, ' °C')} | 💧 Humedad: {_num(a.humedad, 0, ' %')}")
    l.append(f"Riesgo ambiental: {_RIESGO.get(a.riesgo or '', 'sin dato')}")
    if a.rssi is not None:
        l.append(f"📶 Señal hijo→padre: {a.rssi} dBm")
    if a.bateria_mv:
        l.append(f"🔋 Batería: {a.bateria_mv / 1000:.2f} V")
    if a.tipo == "incendio":
        l.append("")
        l.append("📞 Si confirmas fuego: Bomberos 132 · CONAF 130")
    l.append("📡 Forest Fire — Sistema IoT de Detección Temprana")
    return "\n".join(l)


def variables_plantilla(a, ubicacion=None) -> dict:
    """Variables de la plantilla de WhatsApp (TWILIO_CONTENT_SID). Una sola línea cada una: WhatsApp no acepta saltos."""
    hora = a_local(a.recibida_en).strftime("%d/%m %H:%M")
    if a.latitud is not None and a.longitud is not None:
        mapa = f"https://maps.google.com/?q={a.latitud:.6f},{a.longitud:.6f}"
    else:
        mapa = "sin coordenadas"
    sensores = f"temp {_num(a.temperatura, 1, ' °C')}, humedad {_num(a.humedad, 0, ' %')}"
    if a.tipo == "incendio" and a.gas is not None and a.gas_base is not None:
        sensores = f"llama detectada, gas +{a.gas - a.gas_base} sobre la base, " + sensores
    nodo = a.nodo + (f" ({ubicacion})" if ubicacion else "")
    if a.padre and a.padre != a.nodo:
        nodo += f" vía {a.padre}" + (" (padre de respaldo)" if a.padre_respaldo else "")
    return {
        "1": titulo_alerta(a),
        "2": nodo,
        "3": hora,
        "4": mapa,
        "5": sensores,
    }


def variables_tecnico(texto: str) -> dict:
    """Variable de la plantilla técnica: el aviso en una sola línea (WhatsApp no acepta saltos de línea)."""
    linea = " · ".join(p.strip().lstrip("•").strip() for p in texto.splitlines() if p.strip())
    return {"1": linea[:900]}
