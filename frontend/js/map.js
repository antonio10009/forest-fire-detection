// ─── MAPA LEAFLET ──────────────────────
const map = L.map('map').setView([-33.0472, -71.6127], 13);

L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
  attribution: '© OpenStreetMap © CARTO',
  maxZoom: 19
}).addTo(map);

// Iconos personalizados
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
    animation:pulse 1s infinite;
  "></div>`,
  iconSize: [20, 20]
});

function getIcon(nivel) {
  if (nivel === 'ROJO')     return iconRojo;
  if (nivel === 'AMARILLO') return iconAmarillo;
  return iconVerde;
}

// Marcadores activos
const markers = {};

async function cargarSensores() {
  try {
    const res  = await fetch('http://127.0.0.1:8000/api/sensors/');
    const data = await res.json();

    // Stats bar
    document.getElementById('total-sensors').textContent = data.length;
    document.getElementById('zones-safe').textContent =
      data.filter(s => s.activo).length;

    // Lista de nodos
    const lista = document.getElementById('sensors-list');
    lista.innerHTML = '';

    data.forEach(sensor => {
      // Marcador en mapa
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
            🟢 Estado: ${nivel}
          </div>
        `)
        .addTo(map);
      }

      // Item en lista de nodos
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

  } catch (err) {
    console.error('Error cargando sensores:', err);
  }
}

cargarSensores();
setInterval(cargarSensores, 10000);