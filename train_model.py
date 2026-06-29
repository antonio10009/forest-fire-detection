"""
============================================================
PASO 14 - Entrenamiento del modelo de clasificación de incendios
Proyecto: Sistema de deteccion temprana de incendios forestales
============================================================

Uso:
    python backend/ml/train_model.py

Requiere:
    pip install scikit-learn pandas numpy joblib

El modelo entrenado se guarda en:
    backend/ml/modelo_incendio.pkl
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, accuracy_score
import joblib
import os
import warnings
warnings.filterwarnings('ignore')

# ── CONFIGURACIÓN ─────────────────────────────────────────────
CSV_PATH    = "lecturas.csv"  # exportado desde Neon
MODEL_PATH  = "backend/ml/modelo_incendio.pkl"
FEATURES    = ['temperatura', 'humo_ppm', 'humedad']

def cargar_y_limpiar(csv_path: str) -> pd.DataFrame:
    """Carga el CSV exportado de Neon y elimina lecturas con DHT22 fallido."""
    df = pd.read_csv(csv_path)
    df_limpio = df[~((df['temperatura'] == 0) & (df['humedad'] == 0))].copy()
    print(f"Lecturas totales:  {len(df)}")
    print(f"Lecturas válidas:  {len(df_limpio)}")
    print(f"Lecturas con DHT22 bad eliminadas: {len(df) - len(df_limpio)}")
    print(f"\nDistribución por nivel:")
    print(df_limpio['nivel_alerta'].value_counts().to_string())
    return df_limpio

def entrenar(df: pd.DataFrame):
    """Entrena el modelo RandomForest y lo evalúa."""
    X = df[FEATURES].values
    y = df['nivel_alerta'].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    modelo = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        min_samples_split=2,
        min_samples_leaf=1,
        random_state=42,
        class_weight='balanced'
    )
    modelo.fit(X_train, y_train)

    # Evaluación
    y_pred = modelo.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    cv_scores = cross_val_score(modelo, X, y, cv=5, scoring='accuracy')

    print(f"\n=== RESULTADOS ===")
    print(f"Accuracy:              {accuracy*100:.1f}%")
    print(f"Cross-val (5 folds):   {cv_scores.mean()*100:.1f}% ± {cv_scores.std()*100:.1f}%")
    print(f"\nReporte por clase:")
    print(classification_report(y_test, y_pred))
    print("Importancia de variables:")
    for feat, imp in zip(FEATURES, modelo.feature_importances_):
        print(f"  {feat}: {imp*100:.1f}%")

    return modelo

def guardar(modelo, path: str):
    """Guarda el modelo entrenado en disco."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    joblib.dump(modelo, path)
    print(f"\nModelo guardado en: {path}")

if __name__ == "__main__":
    print("=== Entrenando modelo de clasificación de incendios ===\n")
    df = cargar_y_limpiar(CSV_PATH)
    modelo = entrenar(df)
    guardar(modelo, MODEL_PATH)
    print("\nListo. Ahora ejecuta el servidor FastAPI para usar el modelo.")
