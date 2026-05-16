// ─── ALERTAS EN TIEMPO REAL ────────────
const API_ALERTS = "https://forest-fire-detection-044r.onrender.com";

async function cargarAlertas() {
  try {
    const res  = await fetch(`${API_ALERTS}/api/alerts/`);
    const data = await res.json();

    document.getElementById('active-alerts').textContent = data.length;

    const lista = document.getElementById('alerts-list');

    if (data.length === 0) {
      lista.innerHTML = `
        <div class="no-alerts">
          <span>✅ Sin alertas activas</span>
        </div>`;
      document.body.classList.remove('alerta-activa');
      return;
    }

    document.body.classList.add('alerta-activa');

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
        <button class="btn-desactivar" onclick="desactivarAlerta(${alerta.id})">
          ✓ Marcar atendida
        </button>
      `;
      lista.appendChild(item);
    });

  } catch (err) {
    console.error('Error cargando alertas:', err);
  }
}

async function desactivarAlerta(id) {
  try {
    await fetch(`${API_ALERTS}/api/alerts/${id}/desactivar`, {
      method: 'PUT'
    });
    cargarAlertas();
  } catch (err) {
    console.error('Error desactivando alerta:', err);
  }
}

async function cargarHistorial() {
  try {
    const res  = await fetch(`${API_ALERTS}/api/sensors/1/lecturas`);
    const data = await res.json();

    const tbody = document.getElementById('history-body');
    tbody.innerHTML = '';

    const ultimas = data.slice(-20).reverse();
    ultimas.forEach(item => {
      const fecha      = new Date(item.registrado_en).toLocaleString('es-CL');
      const nivel      = item.nivel_alerta || 'VERDE';
      const badgeClass = `badge-${nivel.toLowerCase()}`;
      const tr         = document.createElement('tr');
      tr.innerHTML = `
        <td>${fecha}</td>
        <td>Sensor #${item.sensor_id}</td>
        <td>${item.temperatura}°C</td>
        <td>${item.humo_ppm} PPM</td>
        <td><span class="badge ${badgeClass}">${nivel}</span></td>
      `;
      tbody.appendChild(tr);
    });

    document.getElementById('total-readings').textContent = data.length;

  } catch (err) {
    console.error('Error cargando historial:', err);
  }
}

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
setInterval(actualizarReloj,  1000);
cargarAlertas();
cargarHistorial();
setInterval(cargarAlertas,    8000);
setInterval(cargarHistorial, 10000);