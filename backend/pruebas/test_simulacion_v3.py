# Repite contra el servidor Python real todo lo que recibió el servidor de la simulación del firmware
# (los .ino reales armando el JSON). Primero corre: sh firmware/herramientas/simulacion_v3/ejecutar.sh
# Busca los archivos en FF_SIM_SERVIDOR o en $TMPDIR/ff_sim_v3/servidor.
import glob
import json
import os
import tempfile

import pytest

from conftest import suscribir

CARPETA = os.getenv("FF_SIM_SERVIDOR") or os.path.join(tempfile.gettempdir(), "ff_sim_v3", "servidor")
ARCHIVOS = sorted(glob.glob(os.path.join(CARPETA, "*.jsonl")))


@pytest.mark.skipif(not ARCHIVOS, reason=f"no hay salida de la simulación en {CARPETA}")
@pytest.mark.parametrize("archivo", ARCHIVOS, ids=[os.path.basename(a)[:-6] for a in ARCHIVOS])
def test_repetir_escenario(archivo, cliente, db, envios, monkeypatch):
    monkeypatch.setenv("DEVICE_API_KEY", "SIM_CLAVE_API")
    clave = {"X-Api-Key": "SIM_CLAVE_API"}
    suscribir(db, "+56911111111")
    vistos = set()
    for i, linea in enumerate(open(archivo, encoding="utf-8")):
        r = json.loads(linea)
        antes = envios.total()
        resp = cliente.post(r["ruta"], json=r["body"], headers=clave)
        assert resp.status_code == 200, f"línea {i + 1} {r['ruta']}: {resp.status_code} {resp.text[:300]}"
        avisó = envios.total() > antes
        if r["ruta"] == "/api/v3/latido":
            vistos.add(r["body"]["padre"])
            vistos.update(h["nodo"] for h in r["body"]["hijos"])
            assert not avisó
        else:
            vistos.add(r["body"]["nodo"])
            # el servidor real decide igual que el modelo de la simulación: avisar solo lo nuevo
            assert avisó == r["sim_notifico"], f"línea {i + 1}: real {avisó}, simulación {r['sim_notifico']}"
            assert resp.json()["duplicada"] == r["sim_duplicada"]
    nodos = {n["codigo"] for n in cliente.get("/api/v3/nodos").json()["nodos"]}
    assert nodos == vistos
