import os
import sys
import requests
import random
import time
from datetime import datetime

API_URL = "https://forest-fire-detection-044r.onrender.com"
SENSOR_ID = 1
INTERVALO = 5  # segundos entre lecturas
# Misma clave que DEVICE_API_KEY en Render. En PowerShell: $env:DEVICE_API_KEY = "..."
API_KEY = os.getenv("DEVICE_API_KEY", "")

def generar_lectura(modo="normal"):
    if modo == "normal":
        return {
            "sensor_id":   SENSOR_ID,
            "temperatura": round(random.uniform(18, 35), 2),
            "humo_ppm":    round(random.uniform(10, 80), 2),
            "humedad":     round(random.uniform(40, 80), 2)
        }
    elif modo == "riesgo":
        return {
            "sensor_id":   SENSOR_ID,
            "temperatura": round(random.uniform(45, 65), 2),
            "humo_ppm":    round(random.uniform(150, 300), 2),
            "humedad":     round(random.uniform(15, 35), 2)
        }
    elif modo == "incendio":
        return {
            "sensor_id":   SENSOR_ID,
            "temperatura": round(random.uniform(75, 95), 2),
            "humo_ppm":    round(random.uniform(550, 800), 2),
            "humedad":     round(random.uniform(5, 15), 2)
        }

def enviar_lectura(datos):
    # Datos simulados: el servidor registra la lectura y la alerta en la web,
    # pero no manda WhatsApp a los suscriptores.
    datos["notificado_por_dispositivo"] = True
    try:
        res = requests.post(f"{API_URL}/api/sensors/lectura", json=datos,
                            headers={"X-Api-Key": API_KEY}, timeout=30)
        if res.status_code != 200:
            print(f"❌ Servidor respondió {res.status_code}: {res.text[:200]}")
            return None
        return res.json()
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def simular():
    if not API_KEY:
        print("❌ Falta la variable de entorno DEVICE_API_KEY (la misma de Render).")
        sys.exit(1)
    print("🔥 Simulador ESP32 iniciado (sin WhatsApp a suscriptores)")
    print("─" * 40)

    ciclo = 0
    while True:
        ciclo += 1
        hora  = datetime.now().strftime("%H:%M:%S")

        # Cada 10 lecturas simula un ciclo completo
        if ciclo % 10 < 6:
            modo = "normal"
        elif ciclo % 10 < 9:
            modo = "riesgo"
        else:
            modo = "incendio"

        datos     = generar_lectura(modo)
        resultado = enviar_lectura(datos)

        if resultado:
            nivel = resultado.get("nivel_alerta", "?")
            emoji = {"VERDE": "🟢", "AMARILLO": "🟡", "ROJO": "🔴"}.get(nivel, "⚪")
            print(
                f"[{hora}] {emoji} {nivel} | "
                f"Temp: {datos['temperatura']}°C | "
                f"Humo: {datos['humo_ppm']} PPM | "
                f"Humedad: {datos['humedad']}%"
            )

        time.sleep(INTERVALO)

if __name__ == "__main__":
    simular()