const API_CONFIG = "https://forest-fire-detection-044r.onrender.com";

async function cargarConfiguracion() {
  try {
    const res = await fetch(`${API_CONFIG}/api/config`);
    const c = await res.json();
    document.getElementById('cfg-temp-min').value    = c.temp_amarillo_min;
    document.getElementById('cfg-temp-max').value    = c.temp_rojo_min;
    document.getElementById('cfg-humo-min').value    = c.humo_amarillo_min;
    document.getElementById('cfg-humo-max').value    = c.humo_rojo_min;
    document.getElementById('cfg-hum-riesgo').value     = c.humedad_riesgo_max;
    document.getElementById('cfg-hum-normal-min').value = c.humedad_normal_min;
    document.getElementById('cfg-hum-normal-max').value = c.humedad_normal_max;
    const fecha = new Date(c.actualizado_en).toLocaleString('es-CL');
    document.getElementById('cfg-ultima-actualizacion').textContent = `Actualizado: ${fecha}`;
  } catch (err) { console.error('Error cargando configuración:', err); }
}

async function guardarConfiguracion() {
  const btn = document.getElementById('cfg-btn-guardar');
  const msg = document.getElementById('cfg-mensaje');
  const tempMin  = parseFloat(document.getElementById('cfg-temp-min').value);
  const tempMax  = parseFloat(document.getElementById('cfg-temp-max').value);
  const humoMin  = parseFloat(document.getElementById('cfg-humo-min').value);
  const humoMax  = parseFloat(document.getElementById('cfg-humo-max').value);
  const humRiesgo    = parseFloat(document.getElementById('cfg-hum-riesgo').value);
  const humNormalMin = parseFloat(document.getElementById('cfg-hum-normal-min').value);
  const humNormalMax = parseFloat(document.getElementById('cfg-hum-normal-max').value);

  if (tempMin >= tempMax) { mostrarMsg(msg,'⚠️ Temperatura mínima debe ser menor que máxima.','warn'); return; }
  if (humoMin >= humoMax) { mostrarMsg(msg,'⚠️ Humo mínimo debe ser menor que máximo.','warn'); return; }
  if (humNormalMin >= humNormalMax) { mostrarMsg(msg,'⚠️ Humedad normal mínima debe ser menor que máxima.','warn'); return; }
  if (humRiesgo >= humNormalMin) { mostrarMsg(msg,'⚠️ Umbral de riesgo debe ser menor que humedad normal mínima.','warn'); return; }

  btn.disabled = true;
  btn.textContent = 'Guardando...';
  mostrarMsg(msg,'','');

  try {
    const res = await fetch(`${API_CONFIG}/api/config`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        temp_amarillo_min: tempMin, temp_rojo_min: tempMax,
        humo_amarillo_min: humoMin, humo_rojo_min: humoMax,
        humedad_riesgo_max: humRiesgo, humedad_normal_min: humNormalMin,
        humedad_normal_max: humNormalMax
      })
    });
    if (res.ok) {
      const data = await res.json();
      const fecha = new Date(data.actualizado_en).toLocaleString('es-CL');
      mostrarMsg(msg,'✅ Configuración guardada correctamente.','ok');
      document.getElementById('cfg-ultima-actualizacion').textContent = `Actualizado: ${fecha}`;
    } else { mostrarMsg(msg,'❌ Error al guardar.','err'); }
  } catch(err) { mostrarMsg(msg,'❌ Error de conexión.','err'); console.error(err); }

  btn.disabled = false;
  btn.textContent = '💾 Guardar cambios';
}

function mostrarMsg(el, texto, tipo) {
  el.textContent = texto;
  el.style.color = tipo==='ok' ? 'var(--accent-green)' : tipo==='warn' ? 'var(--accent-yellow)' : tipo==='err' ? 'var(--accent-red)' : 'transparent';
}

function restaurarDefault() {
  document.getElementById('cfg-temp-min').value = 45;
  document.getElementById('cfg-temp-max').value = 55;
  document.getElementById('cfg-humo-min').value = 200;
  document.getElementById('cfg-humo-max').value = 500;
  document.getElementById('cfg-hum-riesgo').value = 30;
  document.getElementById('cfg-hum-normal-min').value = 40;
  document.getElementById('cfg-hum-normal-max').value = 70;
  mostrarMsg(document.getElementById('cfg-mensaje'),'Valores restaurados. Presiona Guardar para aplicar.','warn');
}

function togglePanelAjustes() {
  const panel   = document.getElementById('panel-ajustes');
  const overlay = document.getElementById('ajustes-overlay');
  const abierto = panel.classList.contains('panel-ajustes-visible');
  if (abierto) {
    panel.classList.remove('panel-ajustes-visible');
    overlay.classList.remove('overlay-visible');
    document.body.style.overflow = '';
  } else {
    panel.classList.add('panel-ajustes-visible');
    overlay.classList.add('overlay-visible');
    document.body.style.overflow = 'hidden';
    cargarConfiguracion();
  }
}

document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    const panel = document.getElementById('panel-ajustes');
    if (panel && panel.classList.contains('panel-ajustes-visible')) togglePanelAjustes();
  }
});

document.addEventListener('DOMContentLoaded', () => { cargarConfiguracion(); });