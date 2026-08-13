// ─── MAPA LEAFLET ──────────────────────
const API = "https://forest-fire-detection-044r.onrender.com";

const map = L.map('map').setView([-33.2067, -70.6850], 15);

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  maxZoom: 19
}).addTo(map);

const iconVerde = L.divIcon({
  className: '',
  html: `<div style="
    width:16px; height:16px; border-radius:50%;
    background:#00ff88; border:2px solid #fff;
    box-shadow:0 0 12px rgba(0,255,136,0.8);
  "></div>`,
  iconSize: [16, 16]
});

const iconAmarillo = L.divIcon({
  className: '',
  html: `<div style="
    width:16px; height:16px; border-radius:50%;
    background:#ffd426; border:2px solid #fff;
    box-shadow:0 0 12px rgba(255,212,38,0.8);
  "></div>`,
  iconSize: [16, 16]
});

const iconRojo = L.divIcon({
  className: '',
  html: `<div style="
    width:20px; height:20px; border-radius:50%;
    background:#ff3d3d; border:2px solid #fff;
    box-shadow:0 0 20px rgba(255,61,61,0.9);
  "></div>`,
  iconSize: [20, 20]
});

function getIcon(nivel) {
  if (nivel === 'ROJO')     return iconRojo;
  if (nivel === 'AMARILLO') return iconAmarillo;
  return iconVerde;
}

const markers = {};

async function cargarSensores() {
  try {
    const res  = await fetch(`${API}/api/sensors/`);
    const data = await res.json();

    document.getElementById('total-sensors').textContent = data.length;
    document.getElementById('zones-safe').textContent =
      data.filter(s => s.activo).length;

    const lista = document.getElementById('sensors-list');
    lista.innerHTML = '';

    data.forEach(sensor => {
      const nivel = sensor.ultimo_nivel || 'VERDE';
      if (markers[sensor.id]) {
        markers[sensor.id].setLatLng([sensor.latitud, sensor.longitud]);
      } else {
        markers[sensor.id] = L.marker(
          [sensor.latitud, sensor.longitud],
          { icon: getIcon(nivel) }
        )
        .bindPopup(`
          <div style="font-family:monospace; font-size:12px;">
            <b>📡 ${sensor.nombre}</b><br>
            📍 ${sensor.ubicacion}<br>
            🟢 Estado: ${nivel}<br>
            📌 Lat: ${sensor.latitud?.toFixed(6)}<br>
            📌 Lng: ${sensor.longitud?.toFixed(6)}
          </div>
        `)
        .addTo(map);
      }

      const item = document.createElement('div');
      item.className = 'sensor-item';
      item.innerHTML = `
        <div class="sensor-dot ${nivel.toLowerCase()}"></div>
        <div class="sensor-info">
          <div class="sensor-name">${sensor.nombre}</div>
          <div class="sensor-location">${sensor.ubicacion}</div>
        </div>
      `;
      lista.appendChild(item);
    });

    // Centrar mapa automáticamente en el primer sensor con GPS válido
    if (data.length > 0 && data[0].latitud) {
      map.setView([data[0].latitud, data[0].longitud], 16);
    }

  } catch (err) {
    console.error('Error cargando sensores:', err);
  }
}

cargarSensores();
setInterval(cargarSensores, 10000);