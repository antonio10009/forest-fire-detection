# backend/horario.py
# La base guarda fechas en UTC sin zona (como el resto del proyecto); los mensajes usan la hora de Chile.

import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

ZONA = ZoneInfo(os.getenv("ZONA_HORARIA", "America/Santiago"))


def ahora_utc() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def a_local(dt: datetime) -> datetime:
    return dt.replace(tzinfo=timezone.utc).astimezone(ZONA)


def inicio_de_hoy_utc() -> datetime:
    """Medianoche de hoy en Chile, en UTC sin zona, para comparar con las fechas de la base."""
    medianoche = a_local(ahora_utc()).replace(hour=0, minute=0, second=0, microsecond=0)
    return medianoche.astimezone(timezone.utc).replace(tzinfo=None)


def iso_utc(dt):
    """Para el JSON de la web: con 'Z' para que el navegador lo lea como UTC."""
    return dt.isoformat(timespec="seconds") + "Z" if dt else None
