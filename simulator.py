import requests
import random
import time
from datetime import datetime

API_URL = "https://forest-fire-detection-044r.onrender.com"
SENSOR_ID = 1
INTERVALO = 5  # segundos entre lecturas

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
    try:
        res = requests.post(f"{API_URL}/api/sensors/lectura", json=datos)
        return res.json()
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def simular():
    print("🔥 Simulador ESP32 iniciado")
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