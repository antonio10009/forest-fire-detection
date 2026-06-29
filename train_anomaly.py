"""
============================================================
PASO 15 - Entrenamiento del modelo de Anomaly Detection
Proyecto: Sistema de deteccion temprana de incendios forestales
============================================================

Diferencia clave con el paso 14:
  - Paso 14 (RandomForest): clasifica entre VERDE/AMARILLO/ROJO
  - Paso 15 (IsolationForest): detecta comportamientos inusuales
    aunque no superen los umbrales de alerta. Por ejemplo,
    una temperatura de 25°C es VERDE según las reglas, pero
    inusual para el sensor en condiciones normales (que opera
    a ~15°C). El anomaly detector lo marca como sospechoso.

Uso:
    python backend/ml/train_anomaly.py

El modelo se guarda en:
    backend/ml/modelo_anomalia.pkl
    backend/ml/scaler_anomalia.pkl
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import joblib
import os
import warnings
warnings.filterwarnings('ignore')

# ── CONFIGURACIÓN ─────────────────────────────────────────────
CSV_PATH     = "lecturas.csv"
MODEL_PATH   = "backend/ml/modelo_anomalia.pkl"
SCALER_PATH  = "backend/ml/scaler_anomalia.pkl"
FEATURES     = ['temperatura', 'humo_ppm', 'humedad']

def cargar_datos_normales(csv_path: str) -> pd.DataFrame:
    """
    Carga solo las lecturas VERDE con sensores funcionando.
    El Anomaly Detection aprende ÚNICAMENTE del comportamiento normal,
    no necesita ver ejemplos de anomalías para detectarlas.
    """
    df = pd.read_csv(csv_path)
    df_limpio = df[~((df['temperatura'] == 0) & (df['humedad'] == 0))].copy()
    df_normal = df_limpio[df_limpio['nivel_alerta'] == 'VERDE'].copy()

    print(f"Lecturas totales:           {len(df)}")
    print(f"Lecturas válidas:           {len(df_limpio)}")
    print(f"Lecturas VERDE (normales):  {len(df_normal)}")
    print(f"\nComportamiento normal aprendido:")
    print(df_normal[FEATURES].describe().round(2))
    return df_normal

def entrenar(df_normal: pd.DataFrame):
    """Entrena Isolation Forest y el scaler."""
    X = df_normal[FEATURES].values

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    modelo = IsolationForest(
        n_estimators=100,
        contamination=0.05,
        random_state=42
    )
    modelo.fit(X_scaled)

    print("\n=== VERIFICACIÓN DEL MODELO ===")
    casos = [
        [15.0, 80.0,  50.0, "Normal tipico"],
        [25.0, 150.0, 38.0, "Ligeramente elevado"],
        [55.0, 280.0, 22.0, "AMARILLO"],
        [82.0, 620.0,  8.0, "ROJO critico"],
    ]
    for caso in casos:
        temp, humo, hum, desc = caso
        X_test = scaler.transform([[temp, humo, hum]])
        pred = modelo.predict(X_test)[0]
        score = modelo.score_samples(X_test)[0]
        es_anomalia = pred == -1
        print(f"  {desc}: {'ANOMALIA ⚠️' if es_anomalia else 'Normal ✓'} (score: {score:.3f})")

    return modelo, scaler

def guardar(modelo, scaler, model_path, scaler_path):
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    joblib.dump(modelo, model_path)
    joblib.dump(scaler, scaler_path)
    print(f"\nModelo guardado en:  {model_path}")
    print(f"Scaler guardado en:  {scaler_path}")

if __name__ == "__main__":
    print("=== Entrenando modelo de Anomaly Detection ===\n")
    df_normal = cargar_datos_normales(CSV_PATH)
    modelo, scaler = entrenar(df_normal)
    guardar(modelo, scaler, MODEL_PATH, SCALER_PATH)
    print("\nListo.")
