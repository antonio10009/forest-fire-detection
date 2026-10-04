"""
Forest Fire - Simulación de Alerta de Incendio Forestal
Demo para reunión CONAF - 30 septiembre 2026

REQUISITOS:
  pip install twilio

CONFIGURAR CREDENCIALES (una sola vez):
  Windows PowerShell:
    $env:TWILIO_ACCOUNT_SID  = "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    $env:TWILIO_AUTH_TOKEN   = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    $env:TWILIO_MSG_SVC_SID  = "MGxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

  Mac / Linux:
    export TWILIO_ACCOUNT_SID="ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    export TWILIO_AUTH_TOKEN="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    export TWILIO_MSG_SVC_SID="MGxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

CORRER:
  python forest_fire_alerta_demo.py
"""

import os
import sys
import datetime
import time
from twilio.rest import Client

# ──────────────────────────────────────────────────────────────────────────────
# CREDENCIALES TWILIO — se leen desde variables de entorno
# ──────────────────────────────────────────────────────────────────────────────
ACCOUNT_SID       = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN        = os.getenv("TWILIO_AUTH_TOKEN")
MESSAGING_SVC_SID = os.getenv("TWILIO_MSG_SVC_SID")

if not all([ACCOUNT_SID, AUTH_TOKEN, MESSAGING_SVC_SID]):
    print("❌ ERROR: Faltan variables de entorno de Twilio.")
    print("   Configura TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN y TWILIO_MSG_SVC_SID")
    print("   Ver instrucciones al inicio de este archivo.")
    sys.exit(1)

TO_WA = "whatsapp:+56937247294"   # Número WhatsApp destino

# ──────────────────────────────────────────────────────────────────────────────
# DATOS DEL INCENDIO SIMULADO
# Cerros de Valparaíso, sector Placilla — zona real de alto riesgo
# ──────────────────────────────────────────────────────────────────────────────
LAT     = -33.0472
LON     = -71.6127
ZONA    = "Cerros de Valparaíso — Sector Placilla"
COMUNA  = "Valparaíso"
CUARTEL = "5.ª Compañía de Bomberos de Valparaíso"
REGION  = "Región de Valparaíso"
NODO_ID = "FSN-042"

# ──────────────────────────────────────────────────────────────────────────────

ahora     = datetime.datetime.now()
hora_str  = ahora.strftime("%H:%M")
fecha_str = ahora.strftime("%d/%m/%Y")

client = Client(ACCOUNT_SID, AUTH_TOKEN)

print("=" * 60)
print("  Forest Fire — Simulación de alerta de incendio forestal")
print("=" * 60)
print(f"  Destino : {TO_WA}")
print(f"  Zona    : {ZONA}")
print(f"  GPS     : {LAT}, {LON}")
print(f"  Hora    : {fecha_str} {hora_str}")
print("=" * 60)

# ─── MENSAJE 1: Alerta de emergencia ──────────────────────────────────────────
print("\n[1/2] Enviando alerta de emergencia...")

alerta = (
    "🔴🔴 *ALERTA ROJA — INCENDIO FORESTAL* 🔴🔴\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━\n"
    f"📍 *Zona afectada:* {ZONA}\n"
    f"🏘️ *Comuna:* {COMUNA}  ·  {REGION}\n"
    f"📅 {fecha_str}  🕐 {hora_str} hrs\n\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━\n"
    "🔬 *Lecturas del sensor Forest Fire:*\n"
    "   🔥 Llama infrarroja : *DETECTADA* ⚠️\n"
    "   💨 Gas MQ-135 (CO/Humo) : *NIVEL CRÍTICO* ⚠️\n"
    "   🌡️ Temperatura : *+38 °C*\n"
    "   💧 Humedad relativa : *12 %*\n"
    "   💨 Velocidad del viento : *32 km/h* (dirección NE)\n\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━\n"
    f"🚒 *{CUARTEL}* — notificado ✅\n"
    f"🌲 *CONAF {REGION}* — notificado ✅\n"
    f"🏛️ *SENAPRED {REGION}* — notificado ✅\n\n"
    "📌 *Ubicación GPS exacta en el siguiente mensaje →*\n\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━\n"
    f"📡 *Forest Fire*  ·  Nodo `{NODO_ID}`\n"
    "Sistema de Detección Temprana de Incendios Forestales"
)

msg1 = client.messages.create(
    messaging_service_sid=MESSAGING_SVC_SID,
    to=TO_WA,
    body=alerta
)
print(f"    ✅ Enviado — SID: {msg1.sid}")

# Pequeña pausa para que lleguen en orden
time.sleep(2)

# ─── MENSAJE 2: Pin GPS interactivo ───────────────────────────────────────────
print("\n[2/2] Enviando pin GPS interactivo...")

msg2 = client.messages.create(
    messaging_service_sid=MESSAGING_SVC_SID,
    to=TO_WA,
    body=f"📍 Ubicación del incendio en tiempo real\n🔴 {ZONA}\n\nToca el mapa para abrir en Google Maps",
    persistent_action=[f"geo:{LAT},{LON}|🔴 Incendio activo — {ZONA}"]
)
print(f"    ✅ GPS enviado — SID: {msg2.sid}")

print("\n" + "=" * 60)
print("  ¡Listo! Revisa tu WhatsApp ahora.")
print("  Deberías recibir 2 mensajes.")
print("  El segundo abre el mapa directamente al tocar.")
print("=" * 60)