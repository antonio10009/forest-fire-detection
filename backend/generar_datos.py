import requests

url = "http://127.0.0.1:8000/api/sensors/lectura"

# 50 lecturas AMARILLO
for i in range(50):
    requests.post(url, json={"sensor_id": 1, "temperatura": 58.0, "humo_ppm": 280.0, "humedad": 22.0})
    print(f"AMARILLO {i+1}/50")

# 50 lecturas ROJO
for i in range(50):
    requests.post(url, json={"sensor_id": 1, "temperatura": 82.0, "humo_ppm": 620.0, "humedad": 8.0})
    print(f"ROJO {i+1}/50")

print("Listo, 100 lecturas sintéticas generadas")