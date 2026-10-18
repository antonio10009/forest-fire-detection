// ─── RED v3: PADRES E HIJOS ────────────
// Estado de cada nodo (lo mandan los padres cada 60 s) y los últimos avisos.
const API_RED = "https://forest-fire-detection-044r.onrender.com";

function esc(t) {
  return String(t ?? '').replace(/[&<>"']/g, c =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

function haceTexto(s) {
  if (s == null) return '—';
  if (s < 60)    return `${s} s`;
  if (s < 3600)  return `${Math.round(s / 60)} min`;
  if (s < 86400) return `${Math.round(s / 3600)} h`;
  return `${Math.round(s / 86400)} d`;
}

const ESTADOS_RED = {
  en_linea:  ['En línea', 'verde'],
  atrasado:  ['Atrasado', 'amarillo'],
  sin_senal: ['SIN SEÑAL', 'sin_senal'],
  sin_datos: ['Sin datos', 'sin_senal'],
};

function filaNodo(n) {
  const [estado, clase] = ESTADOS_RED[n.estado] || ['—', 'sin_senal'];
  const nivel = n.nivel || 'VERDE';
  let enlace, senal;
  if (n.tipo === 'padre') {
    enlace = `WiFi ${n.wifi_rssi ?? '—'} dBm<div class="red-sub">canal ${n.canal ?? '—'}${n.modo_prueba ? ' · modo prueba' : ''}</div>`;
    senal  = `${n.hijos ?? 0} ${n.hijos === 1 ? 'hijo' : 'hijos'}<div class="red-sub">${esc(n.fw || '')}</div>`;
  } else {
    enlace = esc(n.padre || '—') + (n.en_respaldo ? '<div class="red-sub"><span class="badge badge-amarillo">RESPALDO</span></div>' : '');
    senal  = `${n.rssi ?? '—'} dBm<div class="red-sub">entrega ${n.entrega_pct != null ? n.entrega_pct.toFixed(1) + ' %' : '—'}</div>`;
  }
  const gas = n.gas == null ? '—'
            : n.gas_base ? `${n.gas} (${n.gas - n.gas_base >= 0 ? '+' : ''}${n.gas - n.gas_base})` : `${n.gas}`;
  return `
    <tr>
      <td><b>${esc(n.codigo)}</b><div class="red-sub">${n.tipo === 'padre' ? 'Padre' : 'Hijo'}${n.ubicacion ? ' · ' + esc(n.ubicacion) : ''}</div></td>
      <td><span class="badge badge-${clase}">${estado}</span>${n.calentando ? '<div class="red-sub">calentando</div>' : ''}</td>
      <td><span class="badge badge-${nivel.toLowerCase()}">${esc(nivel)}</span>${n.llama ? ' 🔥' : ''}</td>
      <td>${enlace}</td>
      <td>${senal}</td>
      <td>${n.temperatura != null ? n.temperatura.toFixed(1) + ' °C' : '—'} · ${n.humedad != null ? Math.round(n.humedad) + ' %' : '—'}</td>
      <td>${gas}</td>
      <td>${n.bateria_mv ? (n.bateria_mv / 1000).toFixed(2) + ' V' : '—'}</td>
      <td>${haceTexto(n.visto_hace_s)}</td>
    </tr>`;
}

function filaAviso(a) {
  const icono = a.tipo === 'incendio' && !a.prueba ? '🔥' : '🧪';
  const tipo  = a.tipo === 'incendio' ? (a.prueba ? 'Incendio (prueba)' : 'INCENDIO')
              : a.tipo === 'prueba_enlace' ? 'Prueba de enlace' : 'Botón del padre';
  const fecha = new Date(a.recibida_en).toLocaleString('es-CL');
  const extra = [
    a.recordatorio ? 'el fuego sigue' : '',
    a.padres ? 'vía ' + esc(a.padres) : '',
    a.estado_aviso ? esc(a.estado_aviso) : '',
    a.veces > 1 ? `llegó ${a.veces} veces` : '',
  ].filter(Boolean).join(' · ');
  return `<div class="red-aviso"><div>${icono} <b>${esc(a.nodo)}</b> · ${tipo}</div><div class="red-sub">${fecha}${extra ? ' · ' + extra : ''}</div></div>`;
}

async function cargarRed() {
  try {
    const [red, avisos] = await Promise.all([
      fetch(`${API_RED}/api/v3/nodos`).then(r => r.json()),
      fetch(`${API_RED}/api/v3/alertas?limite=8`).then(r => r.json()),
    ]);
    const nodos = red.nodos || [];
    document.getElementById('red-body').innerHTML = nodos.length
      ? nodos.map(filaNodo).join('')
      : '<tr><td colspan="9" class="red-vacio">Todavía no reporta ningún padre v3.</td></tr>';
    const enLinea = nodos.filter(n => n.estado === 'en_linea').length;
    const mudos   = nodos.filter(n => n.estado === 'sin_senal').length;
    document.getElementById('red-resumen').textContent =
      `${enLinea} de ${nodos.length} en línea` + (mudos ? ` · ${mudos} sin señal` : '');
    document.getElementById('red-avisos').innerHTML = avisos.length
      ? avisos.map(filaAviso).join('')
      : '<div class="red-vacio">Sin avisos todavía.</div>';
  } catch (err) {
    console.error('Error cargando la red v3:', err);
  }
}

cargarRed();
setInterval(cargarRed, 15000);
