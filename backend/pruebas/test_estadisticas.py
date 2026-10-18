from datetime import timedelta

from backend.horario import inicio_de_hoy_utc
from backend.models.sensor import Lectura, Sensor


def test_lecturas_hoy_cuenta_solo_desde_medianoche_de_chile(cliente, db):
    db.add(Sensor(id=1, nombre="S1", ubicacion="Banco", latitud=-33.0, longitud=-71.6))
    hoy = inicio_de_hoy_utc()
    for registrado in (hoy - timedelta(minutes=1), hoy, hoy + timedelta(hours=3)):
        db.add(Lectura(sensor_id=1, temperatura=20, humo_ppm=50, humedad=60, registrado_en=registrado))
    db.commit()

    r = cliente.get("/api/stats/resumen").json()
    assert r["lecturas_hoy"] == 2
    assert r["total_lecturas"] == 3
