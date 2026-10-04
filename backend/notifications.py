# backend/notifications.py
# Reemplaza tu notifications.py existente

import os
from sqlalchemy.orm import Session
from twilio.rest import Client

# ── Credenciales Twilio (usa variables de entorno en Render) ──
ACCOUNT_SID       = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN        = os.getenv("TWILIO_AUTH_TOKEN")
MESSAGING_SVC_SID = os.getenv("TWILIO_MSG_SVC_SID")


def disparar_alerta_incendio(
    sensor_nombre: str,
    ubicacion:     str,
    temperatura:   float,
    humo_ppm:      float,
    db:            Session = None,   # ← recibe la sesión de sensors.py
    latitud:       float   = None,
    longitud:      float   = None,
):
    """
    Envía alerta WhatsApp a todos los suscriptores activos.
    Llamado desde sensors.py cuando nivel_alerta == 'ROJO'.
    """
    if db is None:
        print("[WhatsApp] Sin sesión de DB — no se enviaron mensajes")
        return

    # 1. Obtener suscriptores activos
    from backend.models.suscriptor import Suscriptor
    suscriptores = db.query(Suscriptor).filter(Suscriptor.activo == True).all()

    if not suscriptores:
        print("[WhatsApp] Sin suscriptores activos — alerta omitida")
        return

    # 2. Armar mensaje
    import datetime
    ahora     = datetime.datetime.now()
    hora_str  = ahora.strftime("%H:%M")
    fecha_str = ahora.strftime("%d/%m/%Y")

    alerta = (
        "🔴🔴 *ALERTA ROJA — INCENDIO FORESTAL* 🔴🔴\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📍 *Sensor:* {sensor_nombre}\n"
        f"🏘️ *Ubicación:* {ubicacion}\n"
        f"📅 {fecha_str}  🕐 {hora_str} hrs\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🔬 *Lecturas del sensor:*\n"
        f"   🌡️ Temperatura : *{temperatura} °C*\n"
        f"   💨 Humo (CO)   : *{humo_ppm} ppm*\n"
        "   🔥 Llama IR    : *DETECTADA* ⚠️\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🚒 Bomberos — notificado ✅\n"
        "🌲 CONAF — notificado ✅\n"
        "🏛️ SENAPRED — notificado ✅\n\n"
        "📡 *Forest Fire* — Sistema IoT de Detección Temprana"
    )

    # 3. Enviar a cada suscriptor
    client   = Client(ACCOUNT_SID, AUTH_TOKEN)
    enviados = 0

    for s in suscriptores:
        numero = f"whatsapp:{s.numero_wa}"
        try:
            # Mensaje principal de alerta
            client.messages.create(
                messaging_service_sid=MESSAGING_SVC_SID,
                to=numero,
                body=alerta
            )
            # Pin GPS si hay coordenadas
            if latitud and longitud:
                client.messages.create(
                    messaging_service_sid=MESSAGING_SVC_SID,
                    to=numero,
                    body=f"📍 Ubicación — {sensor_nombre}",
                    persistent_action=[f"geo:{latitud},{longitud}|🔴 Incendio — {sensor_nombre}"]
                )
            enviados += 1
            print(f"[WhatsApp] ✅ Enviado a {s.numero_wa}")
        except Exception as e:
            print(f"[WhatsApp] ❌ Error enviando a {s.numero_wa}: {e}")

    print(f"[WhatsApp] Alerta enviada a {enviados}/{len(suscriptores)} suscriptores")