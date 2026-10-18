# backend/routers/red.py
# API de la red v3 (firmware nodo_padre_v3 / nodo_hijo_v3).
#
#   POST /api/v3/latido   (X-Api-Key)  cada 60 s cada padre manda su estado y el de todos sus hijos
#   POST /api/v3/alerta   (X-Api-Key)  aviso de incendio o de prueba; el servidor avisa por WhatsApp
#   GET  /api/v3/nodos                  estado de la red para la web
#   GET  /api/v3/alertas                últimos avisos
#   GET  /api/v3/revisar                revisa nodos sin señal (también corre solo cada minuto)
#   PUT/DELETE /api/v3/nodos/{codigo} (X-Admin-Key)  ubicación, coordenadas o borrar un nodo dado de baja
#
# Una misma alerta puede llegar varias veces (reintentos del padre, o por el padre principal y el de
# respaldo a la vez). Se reconoce por (nodo, arranque_id, alerta_id, tipo) y se avisa UNA sola vez.

import asyncio
import os
import threading
from datetime import timedelta
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from backend import avisos_v3
from backend.database import SessionLocal, get_db
from backend.horario import a_local, ahora_utc, iso_utc
from backend.models.red import AlertaRed, NodoRed
from backend.models.sensor import Alerta, Lectura, Sensor
from backend.seguridad import exigir_admin, exigir_dispositivo

router = APIRouter()

MIN_SIN_SENAL      = float(os.getenv("MINUTOS_SIN_SENAL", "10"))
MIN_RESPALDO       = 2          # en el respaldo al menos 2 min antes de avisar (evita avisos por un parpadeo)
LECTURA_CADA_MIN   = 5          # cada cuánto se guarda una fila en "lecturas" por nodo (o si cambia el nivel)
BATERIA_BAJA_MV    = int(os.getenv("BATERIA_BAJA_MV", "3400"))
PLAZO_AVISO_S      = 5.0        # el padre espera ~8 s la respuesta; si nada salió en 5 s, que avise él
VENTANA_DUPLICADOS = timedelta(hours=24)

_candado = threading.Lock()     # serializa las escrituras (un solo proceso uvicorn, como en el Procfile)


# ─── Lo que mandan los padres ─────────────────────────────────

class _Base(BaseModel):
    model_config = ConfigDict(extra="ignore")


class LocalIn(_Base):
    temperatura: Optional[float] = None
    humedad:     Optional[float] = None
    gas:         Optional[int] = None
    gas_base:    Optional[int] = None
    nivel:       Optional[str] = None
    riesgo:      Optional[str] = None
    llama:       bool = False
    calentando:  bool = False


class HijoIn(LocalIn):
    nodo:           str = Field(min_length=1, max_length=32)
    mac:            Optional[str] = Field(None, max_length=17)
    visto_hace_s:   int = Field(0, ge=0)
    rssi:           Optional[int] = None
    entrega_pct:    Optional[float] = None
    padre_respaldo: bool = False
    cambios_padre:  Optional[int] = None
    bateria_mv:     Optional[int] = None
    latitud:        Optional[float] = None
    longitud:       Optional[float] = None


class LatidoIn(_Base):
    padre:      str = Field(min_length=1, max_length=32)
    mac:        Optional[str] = Field(None, max_length=17)
    fw:         Optional[str] = Field(None, max_length=20)
    uptime_s:   Optional[int] = None
    wifi_rssi:  Optional[int] = None
    canal:      Optional[int] = None
    prueba:     bool = False
    bateria_mv: Optional[int] = None
    latitud:    Optional[float] = None
    longitud:   Optional[float] = None
    local:      Optional[LocalIn] = None
    hijos:      List[HijoIn] = Field(default_factory=list, max_length=40)


class AlertaIn(_Base):
    padre:            str = Field(min_length=1, max_length=32)
    nodo:             str = Field(min_length=1, max_length=32)
    mac:              Optional[str] = Field(None, max_length=17)
    tipo:             Literal["incendio", "prueba_enlace", "boton_padre"]
    prueba:           bool = False
    recordatorio:     bool = False
    arranque_id:      int
    alerta_id:        int
    temperatura:      Optional[float] = None
    humedad:          Optional[float] = None
    gas:              Optional[int] = None
    gas_base:         Optional[int] = None
    gas_umbral:       Optional[int] = None
    riesgo:           Optional[str] = None
    rssi:             Optional[int] = None
    padre_respaldo:   bool = False
    latitud:          Optional[float] = None
    longitud:         Optional[float] = None
    coord_del_padre:  bool = False
    bateria_mv:       Optional[int] = None
    ms_llama_confirm: Optional[int] = None
    ms_radio:         Optional[int] = None
    ms_padre:         Optional[int] = None
    hora_padre:       Optional[str] = Field(None, max_length=12)
    ya_notificado:    bool = False


class NodoEditar(_Base):
    ubicacion: Optional[str] = Field(None, max_length=200)
    latitud:   Optional[float] = None
    longitud:  Optional[float] = None
    sensor_id: Optional[int] = None


# ─── Utilidades ───────────────────────────────────────────────

def _coord_ok(lat, lon) -> bool:
    return lat is not None and lon is not None and not (lat == 0 and lon == 0)


def _nodo(db: Session, codigo: str, tipo: str, mac: Optional[str]) -> NodoRed:
    n = db.query(NodoRed).filter(NodoRed.codigo == codigo).first()
    if n is None:
        n = NodoRed(codigo=codigo, tipo=tipo, mac=mac, nivel="VERDE",
                    sin_senal=False, aviso_respaldo=False, bateria_baja=False, coord_manual=False)
        db.add(n)
        db.flush()
    elif mac and n.mac and n.mac != mac:
        print(f"[Red v3] ⚠ {codigo} llegó con otra MAC ({n.mac} -> {mac}): ¿dos equipos con el mismo NODO_ID?")
    n.tipo = tipo
    if mac:
        n.mac = mac
    return n


def _sensor_web(db: Session, n: NodoRed) -> Optional[Sensor]:
    """Fila en la tabla vieja "sensores", para que el mapa y los gráficos actuales muestren el nodo."""
    s = db.get(Sensor, n.sensor_id) if n.sensor_id else None
    if s is None:
        s = db.query(Sensor).filter(Sensor.nombre == n.codigo).first()
    if s is None:
        s = Sensor(nombre=n.codigo, ubicacion=n.ubicacion or "Sin ubicación",
                   latitud=0.0, longitud=0.0, activo=True, ultimo_nivel=n.nivel or "VERDE")
        db.add(s)
        db.flush()
    n.sensor_id = s.id
    if _coord_ok(n.latitud, n.longitud):
        s.latitud, s.longitud = n.latitud, n.longitud
    if n.ubicacion:
        s.ubicacion = n.ubicacion
    return s


def _aplicar_sensores(n: NodoRed, d: LocalIn):
    n.temperatura, n.humedad = d.temperatura, d.humedad
    n.gas, n.gas_base = d.gas, d.gas_base
    n.nivel = d.nivel or "VERDE"
    n.riesgo, n.llama, n.calentando = d.riesgo, d.llama, d.calentando


def _guardar_lectura(db: Session, n: NodoRed, ahora, nivel_antes):
    """Una fila en "lecturas" cada 5 min por nodo, o al cambiar el nivel. Sin DHT22 no se guarda
    (la tabla vieja y la web esperan temperatura y humedad)."""
    s = _sensor_web(db, n)
    if not n.sin_senal:
        s.ultimo_nivel = n.nivel or "VERDE"
    if n.temperatura is None or n.humedad is None:
        return
    reciente = n.ultima_lectura and ahora - n.ultima_lectura < timedelta(minutes=LECTURA_CADA_MIN)
    if reciente and n.nivel == nivel_antes:
        return
    db.add(Lectura(sensor_id=s.id, temperatura=n.temperatura, humo_ppm=float(n.gas or 0), humedad=n.humedad,
                   latitud=n.latitud if _coord_ok(n.latitud, n.longitud) else None,
                   longitud=n.longitud if _coord_ok(n.latitud, n.longitud) else None,
                   llama=bool(n.llama), nivel_alerta=n.nivel or "VERDE", registrado_en=ahora))
    n.ultima_lectura = ahora


def _nodo_json(n: NodoRed, ahora) -> dict:
    hace = int((ahora - n.ultimo_visto).total_seconds()) if n.ultimo_visto else None
    if hace is None:
        estado = "sin_datos"
    elif hace <= 150:
        estado = "en_linea"
    elif hace < MIN_SIN_SENAL * 60:
        estado = "atrasado"
    else:
        estado = "sin_senal"
    return {
        "codigo": n.codigo, "tipo": n.tipo, "mac": n.mac, "ubicacion": n.ubicacion, "sensor_id": n.sensor_id,
        "estado": estado, "visto_hace_s": hace, "ultimo_visto": iso_utc(n.ultimo_visto),
        "padre": n.padre, "en_respaldo": bool(n.en_respaldo), "cambios_padre": n.cambios_padre,
        "rssi": n.rssi, "entrega_pct": n.entrega_pct,
        "temperatura": n.temperatura, "humedad": n.humedad, "gas": n.gas, "gas_base": n.gas_base,
        "nivel": n.nivel, "riesgo": n.riesgo, "llama": bool(n.llama), "calentando": bool(n.calentando),
        "bateria_mv": n.bateria_mv, "latitud": n.latitud, "longitud": n.longitud,
        "fw": n.fw, "uptime_s": n.uptime_s, "wifi_rssi": n.wifi_rssi, "canal": n.canal,
        "modo_prueba": n.modo_prueba, "hijos": n.hijos,
    }


def _alerta_json(a: AlertaRed) -> dict:
    return {
        "id": a.id, "nodo": a.nodo, "padre": a.padre, "padres": a.padres, "tipo": a.tipo,
        "prueba": bool(a.prueba), "recordatorio": bool(a.recordatorio),
        "recibida_en": iso_utc(a.recibida_en), "veces": a.veces, "avisada": bool(a.avisada),
        "estado_aviso": a.estado_aviso, "temperatura": a.temperatura, "humedad": a.humedad,
        "gas": a.gas, "gas_base": a.gas_base, "gas_umbral": a.gas_umbral, "riesgo": a.riesgo,
        "rssi": a.rssi, "padre_respaldo": bool(a.padre_respaldo),
        "latitud": a.latitud, "longitud": a.longitud, "coord_del_padre": bool(a.coord_del_padre),
        "ms_llama_confirm": a.ms_llama_confirm, "ms_radio": a.ms_radio, "ms_padre": a.ms_padre,
    }


# ─── Latido ───────────────────────────────────────────────────

@router.post("/latido", dependencies=[Depends(exigir_dispositivo)])
def recibir_latido(d: LatidoIn, db: Session = Depends(get_db)):
    ahora = ahora_utc()
    with _candado:
        p = _nodo(db, d.padre, "padre", d.mac)
        nivel_antes = p.nivel
        p.ultimo_visto = ahora
        p.fw, p.uptime_s, p.wifi_rssi, p.canal = d.fw, d.uptime_s, d.wifi_rssi, d.canal
        p.modo_prueba, p.bateria_mv, p.hijos = d.prueba, d.bateria_mv, len(d.hijos)
        p.padre, p.en_respaldo, p.respaldo_desde = None, False, None
        if _coord_ok(d.latitud, d.longitud) and not p.coord_manual:
            p.latitud, p.longitud = d.latitud, d.longitud
        if d.local:
            _aplicar_sensores(p, d.local)
        _guardar_lectura(db, p, ahora, nivel_antes)

        for h in d.hijos:
            visto = ahora - timedelta(seconds=h.visto_hace_s)
            n = _nodo(db, h.nodo, "hijo", h.mac)
            # Tras pasarse al respaldo, el padre anterior lo sigue listando unos minutos con datos viejos:
            # manda el reporte más reciente.
            if n.ultimo_visto and visto < n.ultimo_visto - timedelta(seconds=2):
                continue
            nivel_antes = n.nivel
            n.ultimo_visto = visto
            n.padre = d.padre
            if h.padre_respaldo and not n.en_respaldo:
                n.respaldo_desde = ahora
            if not h.padre_respaldo:
                n.respaldo_desde = None
            n.en_respaldo = h.padre_respaldo
            n.rssi, n.entrega_pct, n.cambios_padre = h.rssi, h.entrega_pct, h.cambios_padre
            n.bateria_mv = h.bateria_mv
            if _coord_ok(h.latitud, h.longitud) and not n.coord_manual:
                n.latitud, n.longitud = h.latitud, h.longitud
            _aplicar_sensores(n, h)
            _guardar_lectura(db, n, ahora, nivel_antes)
        db.commit()
    return {"ok": True, "hijos": len(d.hijos)}


# ─── Alerta ───────────────────────────────────────────────────

def _registrar_resultado(alerta_id: int, resumen: str):
    db = SessionLocal()
    try:
        a = db.get(AlertaRed, alerta_id)
        if a:
            a.estado_aviso = (resumen or "")[:300]
            db.commit()
            print(f"[Red v3] aviso {a.nodo} n° {a.alerta_id}: {resumen}")
    finally:
        db.close()


def _alerta_web(db: Session, a: AlertaRed, n: NodoRed):
    """Alerta en la tabla vieja "alertas" para que la web actual se ponga roja y suene."""
    if a.tipo != "incendio":
        return
    s = _sensor_web(db, n)
    s.ultimo_nivel = "ROJO"
    hora = a_local(a.recibida_en).strftime("%H:%M")
    activa = db.query(Alerta).filter(Alerta.sensor_id == s.id, Alerta.activa == True).first()  # noqa: E712
    if activa and a.recordatorio:
        activa.mensaje = (activa.mensaje + f" · el fuego sigue {hora}")[:500]
        a.alerta_web_id = activa.id
        return
    gas = f", gas +{a.gas - a.gas_base}" if a.gas is not None and a.gas_base is not None else ""
    temp = f", {a.temperatura:.1f}°C" if a.temperatura is not None else ""
    nueva = Alerta(sensor_id=s.id, tipo="PRUEBA" if a.prueba else "INCENDIO", activa=True, creada_en=a.recibida_en,
                   mensaje=f"🔥 {a.nodo} {hora}: llama confirmada{gas}{temp}" + (f" (vía {a.padre})" if a.padre != a.nodo else ""))
    db.add(nueva)
    db.flush()
    a.alerta_web_id = nueva.id


@router.post("/alerta", dependencies=[Depends(exigir_dispositivo)])
def recibir_alerta(d: AlertaIn, db: Session = Depends(get_db)):
    ahora = ahora_utc()
    with _candado:
        a = (db.query(AlertaRed)
             .filter(AlertaRed.nodo == d.nodo, AlertaRed.arranque_id == d.arranque_id,
                     AlertaRed.alerta_id == d.alerta_id, AlertaRed.tipo == d.tipo,
                     AlertaRed.recibida_en >= ahora - VENTANA_DUPLICADOS)
             .order_by(AlertaRed.id.desc()).first())
        duplicada = a is not None
        n = _nodo(db, d.nodo, "padre" if d.nodo == d.padre else "hijo", d.mac)
        if n.ultimo_visto is None or n.ultimo_visto < ahora:
            n.ultimo_visto = ahora
        if a is None:
            datos = d.model_dump(exclude={"ya_notificado"})
            a = AlertaRed(**datos, recibida_en=ahora, veces=0, padres="", avisada=False, enviando=False)
            if not _coord_ok(a.latitud, a.longitud):
                a.latitud = a.longitud = None
            db.add(a)
            db.flush()
            _alerta_web(db, a, n)
            if d.tipo == "incendio":
                n.nivel = "ROJO"
        a.veces = (a.veces or 0) + 1
        if d.padre not in (a.padres or "").split(","):
            a.padres = ((a.padres + ",") if a.padres else "") + d.padre
        if d.ya_notificado and not a.avisada:
            a.avisada = True
            a.estado_aviso = f"avisó el padre {d.padre} directo"
        intentar = not a.avisada and not a.enviando
        if intentar:
            a.enviando = True
            clase = "incendio" if (d.tipo == "incendio" and not d.prueba) else "prueba"
            numeros = avisos_v3.destinos(db, clase)
            texto = avisos_v3.texto_alerta(a, n.ubicacion)
            variables = avisos_v3.variables_plantilla(a, n.ubicacion)
        db.commit()
        a_id, avisada = a.id, a.avisada

    if not intentar:
        return {"ok": True, "id": a_id, "duplicada": duplicada, "avisada": avisada}

    r = avisos_v3.enviar(numeros, texto, variables, avisos_v3.plantilla(clase), plazo_s=PLAZO_AVISO_S,
                         al_terminar=lambda resumen: _registrar_resultado(a_id, resumen))
    with _candado:
        a = db.get(AlertaRed, a_id)
        a.enviando = False
        a.avisada = a.avisada or r is not False   # un ya_notificado pudo llegar mientras tanto
        if r is None:
            a.estado_aviso = "enviando"
        db.commit()
    if r is False:
        # Que el padre avise directo (WhatsApp de su secrets.h). Cuando lo haga, manda
        # la misma alerta con ya_notificado=true y queda registrada.
        sin_destinos = not numeros
        return JSONResponse(status_code=503 if sin_destinos else 502, content={
            "ok": False, "id": a_id,
            "detail": "el servidor no tiene WhatsApp configurado o no hay a quién avisar" if sin_destinos
                      else "no salió ningún aviso desde el servidor"})
    return {"ok": True, "id": a_id, "duplicada": duplicada, "avisada": True}


# ─── Vigilancia: nodos sin señal, respaldo, batería ───────────

def _hora(dt) -> str:
    return a_local(dt).strftime("%d/%m %H:%M") if dt else "nunca"


def revisar_red(db: Session, ahora=None) -> dict:
    ahora = ahora or ahora_utc()
    limite = ahora - timedelta(minutes=MIN_SIN_SENAL)
    with _candado:
        nodos = db.query(NodoRed).all()
        mudos = [n for n in nodos if n.ultimo_visto and n.ultimo_visto < limite and not n.sin_senal]
        volvieron = [n for n in nodos if n.sin_senal and n.ultimo_visto and n.ultimo_visto >= limite]
        en_respaldo = [n for n in nodos if n.tipo == "hijo" and n.en_respaldo and not n.aviso_respaldo
                       and not n.sin_senal and n not in mudos and n.respaldo_desde
                       and n.respaldo_desde <= ahora - timedelta(minutes=MIN_RESPALDO)]
        sin_respaldo = [n for n in nodos if n.aviso_respaldo and not n.en_respaldo and n not in mudos]
        bat_baja = [n for n in nodos if n.bateria_mv and n.bateria_mv < BATERIA_BAJA_MV and not n.bateria_baja]
        bat_ok = [n for n in nodos if n.bateria_baja and n.bateria_mv and n.bateria_mv >= BATERIA_BAJA_MV + 150]

        mensajes = []
        if mudos:
            l = [f"⚠️ Forest Fire: sin señal hace más de {MIN_SIN_SENAL:g} min"]
            padres_mudos = {n.codigo for n in mudos if n.tipo == "padre"}
            for n in sorted(mudos, key=lambda x: (x.tipo != "padre", x.codigo)):
                if n.tipo == "padre":
                    hijos = sorted(h.codigo for h in mudos if h.tipo == "hijo" and h.padre == n.codigo)
                    l.append(f"• {n.codigo} (padre), visto {_hora(n.ultimo_visto)}"
                             + (f"; también sus hijos {', '.join(hijos)}" if hijos else ""))
                elif n.padre not in padres_mudos:
                    l.append(f"• {n.codigo} (hijo de {n.padre or '?'}), visto {_hora(n.ultimo_visto)}")
            if padres_mudos:
                l.append("Si un padre no reporta, revisa su energía y su internet: sin él, sus hijos tampoco aparecen.")
            mensajes.append("\n".join(l))
        if volvieron:
            mensajes.append("✅ Forest Fire: volvieron a reportar " + ", ".join(sorted(n.codigo for n in volvieron)))
        for n in en_respaldo:
            mensajes.append(f"↪️ {n.codigo} está usando su padre de respaldo {n.padre}: su padre principal no le confirma. "
                            "Revisa el padre principal.")
        for n in sin_respaldo:
            mensajes.append(f"↩️ {n.codigo} volvió a su padre principal {n.padre}.")
        for n in bat_baja:
            mensajes.append(f"🔋 Batería baja en {n.codigo}: {n.bateria_mv / 1000:.2f} V")

        for n in mudos:
            n.sin_senal = True
            if n.sensor_id and (s := db.get(Sensor, n.sensor_id)):
                s.ultimo_nivel = "SIN_SENAL"
        for n in volvieron:
            n.sin_senal = False
            if n.sensor_id and (s := db.get(Sensor, n.sensor_id)):
                s.ultimo_nivel = n.nivel or "VERDE"
        for n in en_respaldo:
            n.aviso_respaldo = True
        for n in sin_respaldo:
            n.aviso_respaldo = False
        for n in bat_baja:
            n.bateria_baja = True
        for n in bat_ok:
            n.bateria_baja = False
        db.commit()
        numeros = avisos_v3.destinos(db, "tecnico") if mensajes else []

    for m in mensajes:
        print("[Red v3] " + m.replace("\n", " | "))
        avisos_v3.enviar(numeros, m, avisos_v3.variables_tecnico(m), avisos_v3.plantilla("tecnico"), plazo_s=0)
    return {"revisado": iso_utc(ahora), "nodos": len(nodos), "avisos": mensajes}


def revisar_con_sesion():
    db = SessionLocal()
    try:
        return revisar_red(db)
    finally:
        db.close()


async def vigilar():
    """Corre dentro del servidor (main.py la arranca): revisa la red cada minuto."""
    periodo = float(os.getenv("VIGILANCIA_SEGUNDOS", "60"))
    while True:
        await asyncio.sleep(periodo)
        try:
            await asyncio.to_thread(revisar_con_sesion)
        except Exception as e:
            print(f"[Red v3] error en la vigilancia: {e}")


# ─── Consultas para la web ────────────────────────────────────

@router.get("/nodos")
def listar_nodos(db: Session = Depends(get_db)):
    ahora = ahora_utc()
    nodos = db.query(NodoRed).order_by(NodoRed.tipo.desc(), NodoRed.codigo).all()
    return {"ahora": iso_utc(ahora), "minutos_sin_senal": MIN_SIN_SENAL,
            "nodos": [_nodo_json(n, ahora) for n in nodos]}


@router.get("/alertas")
def listar_alertas(limite: int = Query(20, ge=1, le=200), db: Session = Depends(get_db)):
    filas = db.query(AlertaRed).order_by(AlertaRed.id.desc()).limit(limite).all()
    return [_alerta_json(a) for a in filas]


@router.get("/revisar")
def revisar_ahora():
    """Para un monitor externo (UptimeRobot, cron-job.org) que mantenga despierto el servidor."""
    return revisar_con_sesion()


@router.put("/nodos/{codigo}", dependencies=[Depends(exigir_admin)])
def editar_nodo(codigo: str, d: NodoEditar, db: Session = Depends(get_db)):
    with _candado:
        n = db.query(NodoRed).filter(NodoRed.codigo == codigo).first()
        if n is None:
            raise HTTPException(status_code=404, detail="Nodo no encontrado")
        campos = d.model_dump(exclude_unset=True)
        if "ubicacion" in campos:
            n.ubicacion = d.ubicacion
        if "latitud" in campos or "longitud" in campos:
            if _coord_ok(d.latitud, d.longitud):
                n.latitud, n.longitud, n.coord_manual = d.latitud, d.longitud, True
            else:
                n.coord_manual = False          # null = volver a usar las del config.h
        if "sensor_id" in campos and d.sensor_id is not None:
            if db.get(Sensor, d.sensor_id) is None:
                raise HTTPException(status_code=404, detail="Ese sensor_id no existe")
            n.sensor_id = d.sensor_id
        _sensor_web(db, n)
        db.commit()
        return _nodo_json(n, ahora_utc())


@router.delete("/nodos/{codigo}", dependencies=[Depends(exigir_admin)])
def borrar_nodo(codigo: str, db: Session = Depends(get_db)):
    with _candado:
        n = db.query(NodoRed).filter(NodoRed.codigo == codigo).first()
        if n is None:
            raise HTTPException(status_code=404, detail="Nodo no encontrado")
        if n.sensor_id and (s := db.get(Sensor, n.sensor_id)):
            s.activo = False
        db.delete(n)
        db.commit()
    return {"ok": True, "borrado": codigo}
