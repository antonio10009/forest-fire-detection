# Pruebas de /api/v3: latidos, alertas sin duplicar, vigilancia y claves.
import threading
from datetime import timedelta

from backend.horario import ahora_utc
from backend.routers import red
from conftest import ADMIN, CLAVE, suscribir


def latido(padre="FSN-A Padre", hijos=(), **extra):
    j = {"padre": padre, "mac": "24:6F:28:AA:00:01", "fw": "padre-3.0", "uptime_s": 100, "wifi_rssi": -60,
         "canal": 6, "prueba": False, "bateria_mv": None, "latitud": -33.1, "longitud": -71.6,
         "local": {"temperatura": 21.5, "humedad": 55, "gas": 1200, "gas_base": 1190, "nivel": "VERDE",
                   "riesgo": "NORMAL", "llama": False, "calentando": False},
         "hijos": list(hijos)}
    j.update(extra)
    return j


def hijo(nodo="FSN-H1", visto=3, respaldo=False, **extra):
    j = {"nodo": nodo, "mac": "34:85:18:00:02:C9", "visto_hace_s": visto, "rssi": -72, "entrega_pct": 99.0,
         "padre_respaldo": respaldo, "cambios_padre": 0, "temperatura": 20.0, "humedad": 60, "gas": 1100,
         "gas_base": 1100, "nivel": "VERDE", "riesgo": "NORMAL", "llama": False, "calentando": False,
         "bateria_mv": None, "latitud": -33.0995, "longitud": -71.601}
    j.update(extra)
    return j


def alerta(nodo="FSN-H1", padre="FSN-A Padre", alerta_id=1, **extra):
    j = {"padre": padre, "nodo": nodo, "mac": "34:85:18:00:02:C9", "tipo": "incendio", "prueba": False,
         "recordatorio": False, "arranque_id": 4242, "alerta_id": alerta_id, "temperatura": 31.0, "humedad": 25,
         "gas": 1450, "gas_base": 1199, "gas_umbral": 30, "riesgo": "ALTO", "rssi": -78, "padre_respaldo": False,
         "latitud": -33.0995, "longitud": -71.601, "coord_del_padre": False, "bateria_mv": None,
         "ms_llama_confirm": 2000, "ms_radio": 40, "ms_padre": 3, "hora_padre": "14:05:00", "ya_notificado": False}
    j.update(extra)
    return j


# ─── Claves ───────────────────────────────────────────────────

def test_claves(cliente, monkeypatch):
    assert cliente.post("/api/v3/latido", json=latido()).status_code == 401
    assert cliente.post("/api/v3/latido", json=latido(), headers={"X-Api-Key": "otra"}).status_code == 401
    assert cliente.post("/api/v3/latido", json=latido(), headers=CLAVE).status_code == 200
    cfg = cliente.get("/api/config/").json()
    datos = {k: cfg[k] for k in ("temp_amarillo_min", "temp_rojo_min", "humo_amarillo_min", "humo_rojo_min",
                                 "humedad_riesgo_max", "humedad_normal_min", "humedad_normal_max")}
    assert cliente.put("/api/config/", json=datos).status_code == 401
    assert cliente.put("/api/config/", json=datos, headers=ADMIN).status_code == 200
    assert cliente.get("/api/suscriptores/").status_code == 401
    assert cliente.get("/api/suscriptores/", headers=ADMIN).status_code == 200
    assert cliente.get("/api/suscriptores/agregar?numero=+56900000000").status_code == 401
    assert cliente.put("/api/alerts/1/desactivar").status_code == 401
    assert cliente.post("/api/sensors/", json={"nombre": "x", "ubicacion": "y", "latitud": 1, "longitud": 1}).status_code == 401
    vieja = {"sensor_id": 1, "temperatura": 20, "humo_ppm": 10, "humedad": 50}
    assert cliente.post("/api/sensors/lectura", json=vieja).status_code == 401
    assert cliente.post("/api/sensors/lectura", json=vieja, headers=CLAVE).status_code == 200
    monkeypatch.setenv("PERMITIR_LECTURA_SIN_CLAVE", "1")
    assert cliente.post("/api/sensors/lectura", json=vieja).status_code == 200
    monkeypatch.delenv("DEVICE_API_KEY")
    assert cliente.post("/api/v3/latido", json=latido(), headers=CLAVE).status_code == 503   # cerrada, no abierta


# ─── Latido ───────────────────────────────────────────────────

def test_latido_crea_nodos_y_los_muestra(cliente):
    r = cliente.post("/api/v3/latido", headers=CLAVE,
                     json=latido(hijos=[hijo(), hijo("FSN-H2", latitud=None, longitud=None, temperatura=None)]))
    assert r.status_code == 200 and r.json()["hijos"] == 2
    nodos = {n["codigo"]: n for n in cliente.get("/api/v3/nodos").json()["nodos"]}
    assert set(nodos) == {"FSN-A Padre", "FSN-H1", "FSN-H2"}
    assert nodos["FSN-A Padre"]["tipo"] == "padre" and nodos["FSN-A Padre"]["hijos"] == 2
    assert nodos["FSN-H1"]["estado"] == "en_linea" and nodos["FSN-H1"]["padre"] == "FSN-A Padre"
    assert nodos["FSN-H2"]["latitud"] is None
    # la web vieja: un sensor por nodo y lecturas de los que tienen DHT22
    sensores = {s["nombre"]: s for s in cliente.get("/api/sensors/").json()}
    assert set(sensores) == {"FSN-A Padre", "FSN-H1", "FSN-H2"}
    assert sensores["FSN-H1"]["latitud"] == -33.0995
    assert len(cliente.get(f"/api/sensors/{sensores['FSN-H1']['id']}/lecturas").json()) == 1
    assert len(cliente.get(f"/api/sensors/{sensores['FSN-H2']['id']}/lecturas").json()) == 0
    # un segundo latido enseguida no agrega otra lectura (una cada 5 min o si cambia el nivel)
    cliente.post("/api/v3/latido", headers=CLAVE, json=latido(hijos=[hijo()]))
    assert len(cliente.get(f"/api/sensors/{sensores['FSN-H1']['id']}/lecturas").json()) == 1
    cliente.post("/api/v3/latido", headers=CLAVE, json=latido(hijos=[hijo(nivel="AMARILLO")]))
    assert len(cliente.get(f"/api/sensors/{sensores['FSN-H1']['id']}/lecturas").json()) == 2


def test_reporte_viejo_del_padre_anterior_no_pisa(cliente):
    cliente.post("/api/v3/latido", headers=CLAVE, json=latido("FSN-B Padre", hijos=[hijo(respaldo=True, visto=2)]))
    # el padre A todavía lo lista, con datos de hace 5 min
    cliente.post("/api/v3/latido", headers=CLAVE, json=latido("FSN-A Padre", hijos=[hijo(visto=300)]))
    h1 = next(n for n in cliente.get("/api/v3/nodos").json()["nodos"] if n["codigo"] == "FSN-H1")
    assert h1["padre"] == "FSN-B Padre" and h1["en_respaldo"] is True


# ─── Alertas ──────────────────────────────────────────────────

def test_alerta_avisa_una_sola_vez(cliente, db, envios):
    suscribir(db, "+56911111111", "+56922222222")
    r = cliente.post("/api/v3/alerta", headers=CLAVE, json=alerta())
    assert r.status_code == 200 and r.json()["duplicada"] is False
    assert sorted(w[0] for w in envios.wa) == ["+56911111111", "+56922222222"]
    texto = envios.wa[0][1]
    assert texto.startswith("🔥 ALERTA ROJA") and "FSN-H1" in texto and "maps.google.com/?q=-33.099500,-71.601000" in texto
    # reintento del mismo padre y la misma alerta por el padre de respaldo
    assert cliente.post("/api/v3/alerta", headers=CLAVE, json=alerta()).json()["duplicada"] is True
    r = cliente.post("/api/v3/alerta", headers=CLAVE, json=alerta(padre="FSN-B Padre", padre_respaldo=True))
    assert r.status_code == 200 and r.json()["duplicada"] is True
    assert envios.total() == 2
    a = cliente.get("/api/v3/alertas").json()
    assert len(a) == 1 and a[0]["veces"] == 3 and a[0]["padres"] == "FSN-A Padre,FSN-B Padre"
    # la web vieja: una alerta activa
    activas = cliente.get("/api/alerts/").json()
    assert len(activas) == 1 and activas[0]["tipo"] == "INCENDIO"


def test_reinicio_del_hijo_es_alerta_nueva(cliente, db, envios):
    suscribir(db, "+56911111111")
    cliente.post("/api/v3/alerta", headers=CLAVE, json=alerta())
    cliente.post("/api/v3/alerta", headers=CLAVE, json=alerta(arranque_id=999))   # mismo n° 1, otro arranque
    assert len(envios.wa) == 2


def test_padre_ya_aviso_directo(cliente, db, envios):
    suscribir(db, "+56911111111")
    r = cliente.post("/api/v3/alerta", headers=CLAVE, json=alerta(ya_notificado=True))
    assert r.status_code == 200 and envios.total() == 0
    # llega tarde el mismo aviso sin la marca (servidor dormido): no se repite
    assert cliente.post("/api/v3/alerta", headers=CLAVE, json=alerta()).json()["duplicada"] is True
    assert envios.total() == 0
    a = cliente.get("/api/v3/alertas").json()[0]
    assert a["avisada"] is True and "directo" in a["estado_aviso"]


def test_si_nada_sale_el_padre_avisa_directo(cliente, db, envios):
    suscribir(db, "+56911111111")
    envios.wa_ok = False
    assert cliente.post("/api/v3/alerta", headers=CLAVE, json=alerta()).status_code == 502
    # el padre reintenta más tarde (su aviso directo también falló): el servidor lo intenta de nuevo
    envios.wa_ok = True
    assert cliente.post("/api/v3/alerta", headers=CLAVE, json=alerta()).status_code == 200
    assert len(envios.wa) == 2


def test_sin_canales_responde_503(cliente):
    r = cliente.post("/api/v3/alerta", headers=CLAVE, json=alerta())
    assert r.status_code == 503       # el padre avisa directo
    r = cliente.post("/api/v3/alerta", headers=CLAVE, json=alerta(ya_notificado=True))
    assert r.status_code == 200       # y después queda registrada


def test_pruebas_van_a_los_tecnicos(cliente, db, envios, monkeypatch):
    suscribir(db, "+56911111111", "+56922222222")
    cliente.post("/api/v3/alerta", headers=CLAVE, json=alerta(tipo="prueba_enlace", prueba=True))
    assert len(envios.wa) == 2 and envios.wa[0][1].startswith("🧪 PRUEBA DE ENLACE")   # sin lista técnica: a todos
    monkeypatch.setenv("AVISOS_TECNICOS_WA", "+56933333333")
    cliente.post("/api/v3/alerta", headers=CLAVE, json=alerta(alerta_id=2, prueba=True))
    assert envios.wa[-1][0] == "+56933333333" and len(envios.wa) == 3
    assert envios.wa[-1][1].startswith("🧪 PRUEBA — 🔥 ALERTA ROJA")
    assert cliente.get("/api/alerts/").json()[0]["tipo"] == "PRUEBA"
    # un incendio real sí va a todos los suscriptores
    cliente.post("/api/v3/alerta", headers=CLAVE, json=alerta(nodo="FSN-H2", alerta_id=1))
    assert len(envios.wa) == 5


def test_plantilla_aprobada(cliente, db, envios, monkeypatch):
    suscribir(db, "+56911111111")
    monkeypatch.setenv("TWILIO_CONTENT_SID", "HXincendio")
    cliente.post("/api/v3/alerta", headers=CLAVE, json=alerta(padre="FSN-B Padre", padre_respaldo=True))
    numero, texto, variables, sid = envios.wa[0]
    assert sid == "HXincendio" and sorted(variables) == ["1", "2", "3", "4", "5"]
    assert all("\n" not in v for v in variables.values())          # WhatsApp no acepta saltos en las variables
    assert variables["1"] == "🔥 ALERTA ROJA - INCENDIO FORESTAL"
    assert variables["2"] == "FSN-H1 vía FSN-B Padre (padre de respaldo)"
    assert variables["4"] == "https://maps.google.com/?q=-33.099500,-71.601000"
    assert variables["5"].startswith("llama detectada, gas +251")


def test_avisos_tecnicos_nunca_al_publico(cliente, db, envios):
    suscribir(db, "+56911111111")
    cliente.post("/api/v3/latido", headers=CLAVE, json=latido(hijos=[hijo(bateria_mv=3300)]))
    assert red.revisar_red(db)["avisos"]                # hay aviso, pero sin AVISOS_TECNICOS_WA no sale
    assert not envios.esperar(1, segundos=0.3)


def test_recordatorio_el_fuego_sigue(cliente, db, envios):
    suscribir(db, "+56911111111")
    cliente.post("/api/v3/alerta", headers=CLAVE, json=alerta())
    cliente.post("/api/v3/alerta", headers=CLAVE, json=alerta(alerta_id=2, recordatorio=True))
    assert len(envios.wa) == 2 and "(el fuego sigue)" in envios.wa[1][1]
    activas = cliente.get("/api/alerts/").json()
    assert len(activas) == 1 and "el fuego sigue" in activas[0]["mensaje"]


def test_dos_padres_a_la_vez(cliente, db, envios):
    suscribir(db, "+56911111111")
    codigos = []

    def mandar(padre):
        codigos.append(cliente.post("/api/v3/alerta", headers=CLAVE, json=alerta(padre=padre)).status_code)

    hilos = [threading.Thread(target=mandar, args=(p,)) for p in ("FSN-A Padre", "FSN-B Padre") * 3]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()
    assert codigos == [200] * 6 and len(envios.wa) == 1


# ─── Vigilancia ───────────────────────────────────────────────

def test_sin_senal_y_vuelta(cliente, db, envios, monkeypatch):
    suscribir(db, "+56911111111")
    monkeypatch.setenv("AVISOS_TECNICOS_WA", "+56900000001")
    t0 = ahora_utc()
    monkeypatch.setattr(red, "ahora_utc", lambda: t0)
    cliente.post("/api/v3/latido", headers=CLAVE, json=latido(hijos=[hijo(), hijo("FSN-H2")]))
    cliente.post("/api/v3/latido", headers=CLAVE, json=latido("FSN-B Padre", hijos=[hijo("FSN-H3")]))
    assert red.revisar_red(db, t0 + timedelta(minutes=5))["avisos"] == []
    # B sigue vivo, A y sus hijos callan
    monkeypatch.setattr(red, "ahora_utc", lambda: t0 + timedelta(minutes=9))
    cliente.post("/api/v3/latido", headers=CLAVE, json=latido("FSN-B Padre", hijos=[hijo("FSN-H3")]))
    avisos = red.revisar_red(db, t0 + timedelta(minutes=11))["avisos"]
    assert len(avisos) == 1
    assert "FSN-A Padre (padre)" in avisos[0] and "también sus hijos FSN-H1, FSN-H2" in avisos[0]
    assert "FSN-B" not in avisos[0] and "FSN-H3" not in avisos[0]
    assert envios.esperar(1) and [w[0] for w in envios.wa] == ["+56900000001"]     # al técnico, no al público
    assert red.revisar_red(db, t0 + timedelta(minutes=12))["avisos"] == []        # no se repite
    assert cliente.get("/api/sensors/").json()[0]["ultimo_nivel"] == "SIN_SENAL"
    monkeypatch.setattr(red, "ahora_utc", lambda: t0 + timedelta(minutes=20))
    cliente.post("/api/v3/latido", headers=CLAVE, json=latido(hijos=[hijo(), hijo("FSN-H2")]))
    cliente.post("/api/v3/latido", headers=CLAVE, json=latido("FSN-B Padre", hijos=[hijo("FSN-H3")]))
    avisos = red.revisar_red(db, t0 + timedelta(minutes=20))["avisos"]
    assert avisos == ["✅ Forest Fire: volvieron a reportar FSN-A Padre, FSN-H1, FSN-H2"]


def test_hijo_en_respaldo(cliente, db, envios, monkeypatch):
    monkeypatch.setenv("AVISOS_TECNICOS_WA", "+56900000001, +56900000002")
    monkeypatch.setenv("TWILIO_CONTENT_SID_TECNICO", "HXtecnico")
    t0 = ahora_utc()
    monkeypatch.setattr(red, "ahora_utc", lambda: t0)
    cliente.post("/api/v3/latido", headers=CLAVE, json=latido("FSN-B Padre", hijos=[hijo(respaldo=True)]))
    assert red.revisar_red(db, t0 + timedelta(minutes=1))["avisos"] == []          # un parpadeo no avisa
    avisos = red.revisar_red(db, t0 + timedelta(minutes=3))["avisos"]
    assert len(avisos) == 1 and avisos[0].startswith("↪️ FSN-H1 está usando su padre de respaldo FSN-B Padre")
    assert envios.esperar(2) and sorted(w[0] for w in envios.wa) == ["+56900000001", "+56900000002"]
    numero, texto, variables, sid = envios.wa[0]
    assert sid == "HXtecnico" and "\n" not in variables["1"] and variables["1"].startswith("↪️ FSN-H1")
    monkeypatch.setattr(red, "ahora_utc", lambda: t0 + timedelta(minutes=6))
    cliente.post("/api/v3/latido", headers=CLAVE, json=latido("FSN-A Padre", hijos=[hijo()]))
    assert red.revisar_red(db, t0 + timedelta(minutes=6))["avisos"] == ["↩️ FSN-H1 volvió a su padre principal FSN-A Padre."]


def test_bateria_baja(cliente, db, envios):
    cliente.post("/api/v3/latido", headers=CLAVE, json=latido(hijos=[hijo(bateria_mv=3300)]))
    avisos = red.revisar_red(db)["avisos"]
    assert avisos == ["🔋 Batería baja en FSN-H1: 3.30 V"]
    assert red.revisar_red(db)["avisos"] == []


# ─── Web ──────────────────────────────────────────────────────

def test_editar_y_borrar_nodo(cliente):
    cliente.post("/api/v3/latido", headers=CLAVE, json=latido(hijos=[hijo("FSN-H2", latitud=None, longitud=None)]))
    assert cliente.put("/api/v3/nodos/FSN-H2", json={"ubicacion": "Quebrada norte"}).status_code == 401
    r = cliente.put("/api/v3/nodos/FSN-H2", headers=ADMIN,
                    json={"ubicacion": "Quebrada norte", "latitud": -33.2, "longitud": -71.7})
    assert r.status_code == 200 and r.json()["latitud"] == -33.2
    cliente.post("/api/v3/latido", headers=CLAVE, json=latido(hijos=[hijo("FSN-H2", latitud=-1.0, longitud=-1.0)]))
    h2 = next(n for n in cliente.get("/api/v3/nodos").json()["nodos"] if n["codigo"] == "FSN-H2")
    assert h2["latitud"] == -33.2 and h2["ubicacion"] == "Quebrada norte"        # lo puesto a mano no se pisa
    s = next(s for s in cliente.get("/api/sensors/").json() if s["nombre"] == "FSN-H2")
    assert s["ubicacion"] == "Quebrada norte" and s["latitud"] == -33.2
    assert cliente.delete("/api/v3/nodos/FSN-H2", headers=ADMIN).status_code == 200
    assert "FSN-H2" not in [n["codigo"] for n in cliente.get("/api/v3/nodos").json()["nodos"]]


def test_lecturas_limitadas(cliente):
    for t in range(5):
        cliente.post("/api/sensors/lectura", headers=CLAVE, json={"sensor_id": 7, "temperatura": 20 + t, "humo_ppm": 1, "humedad": 50})
    r = cliente.get("/api/sensors/7/lecturas?limite=3").json()
    assert [x["temperatura"] for x in r] == [22, 23, 24]
    assert len(cliente.get("/api/sensors/7/lecturas").json()) == 5
