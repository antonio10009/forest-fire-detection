# backend/seguridad.py
# Claves de acceso:
#   X-Api-Key   = DEVICE_API_KEY  -> los padres (API_KEY_DISPOSITIVO en secrets.h)
#   X-Admin-Key = ADMIN_API_KEY   -> cambios desde la web (umbrales, suscriptores, nodos)
# Si la variable no está definida en Render, la ruta queda cerrada (503), nunca abierta.

import os
import secrets
from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

_clave_dispositivo = APIKeyHeader(name="X-Api-Key", auto_error=False, scheme_name="ClaveDispositivo")
_clave_admin       = APIKeyHeader(name="X-Admin-Key", auto_error=False, scheme_name="ClaveAdmin")


def _comparar(recibida, variable: str):
    esperada = os.getenv(variable, "").strip()
    if not esperada:
        raise HTTPException(status_code=503, detail=f"Falta la variable {variable} en el servidor")
    if not recibida or not secrets.compare_digest(recibida.strip().encode(), esperada.encode()):
        raise HTTPException(status_code=401, detail="Clave incorrecta")


def exigir_dispositivo(clave: str = Security(_clave_dispositivo)):
    _comparar(clave, "DEVICE_API_KEY")


def exigir_dispositivo_antiguo(clave: str = Security(_clave_dispositivo)):
    """Ruta vieja /api/sensors/lectura: abierta solo si PERMITIR_LECTURA_SIN_CLAVE=1 (nodos v2 aún en uso)."""
    if os.getenv("PERMITIR_LECTURA_SIN_CLAVE", "0").strip() == "1":
        return
    _comparar(clave, "DEVICE_API_KEY")


def exigir_admin(clave: str = Security(_clave_admin)):
    _comparar(clave, "ADMIN_API_KEY")
