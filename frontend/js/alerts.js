// ─── ALERTAS EN TIEMPO REAL ────────────

async function cargarAlertas() {
  try {
    const res  = await fetch('http://127.0.0.1:8000/api/alerts/');
    const data = await res.json();

    // Stats
    document.getElementById('active-alerts').textContent = data.length;

    const lista = document.getElementById('alerts-list');

    if (data.length === 0) {
      lista.innerHTML = `
        <div class="no-alerts">
          <span>✅ Sin alertas activas</span>
        </div>`;
      return;
    }

    lista.innerHTML = '';
    data.forEach(alerta => {
      const fecha = new Date(alerta.creada_en).toLocaleString('es-CL');
      const item  = document.createElement('div');
      item.className = 'alert-item';
      item.innerHTML = `
        <div class="alert-item-title">🔥 ${alerta.tipo}</div>
        <div class="alert-item-detail">${alerta.mensaje}</div>
        <div class="alert-item-detail" style="margin-top:4px; color:#4a5568;">
          📅 ${fecha}
        </div>
      `;
      lista.appendChild(item);
    });

  } catch (err) {
    console.error('Error cargando alertas:', err);
  }
}

async function cargarHistorial() {
  try {
    const res  = await fetch('http://127.0.0.1:8000/api/alerts/historial');
    const data = await res.json();

    const tbody = document.getElementById('history-body');
    tbody.innerHTML = '';

    // Últimas 20 lecturas
    data.slice(0, 20).forEach(item => {
      const fecha = new Date(item.creada_en).toLocaleString('es-CL');
      const tr    = document.createElement('tr');
      tr.innerHTML = `
        <td>${fecha}</td>
        <td>Sensor #${item.sensor_id}</td>
        <td>—</td>
        <td>—</td>
        <td><span class="badge badge-rojo">ROJO</span></td>
      `;
      tbody.appendChild(tr);
    });

  } catch (err) {
    console.error('Error cargando historial:', err);
  }
}

// Reloj
function actualizarReloj() {
  const ahora = new Date();
  document.getElementById('clock').textContent =
    ahora.toLocaleString('es-CL', {
      weekday: 'short',
      year:    'numeric',
      month:   '2-digit',
      day:     '2-digit',
      hour:    '2-digit',
      minute:  '2-digit',
      second:  '2-digit'
    }).toUpperCase();
}

actualizarReloj();
setInterval(actualizarReloj, 1000);
cargarAlertas();
cargarHistorial();
setInterval(cargarAlertas,  8000);
setInterval(cargarHistorial, 15000);