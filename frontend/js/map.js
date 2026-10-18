// ─── MAPA LEAFLET ──────────────────────
const API = "https://forest-fire-detection-044r.onrender.com";

const map = L.map('map').setView([-33.2067, -70.6850], 15);

L.tileLayer(
  'https://maps.geoapify.com/v1/tile/osm-bright/{z}/{x}/{y}.png?apiKey=be9b6285024d4f8d8d4213188ec971e4',
  {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://www.geoapify.com/">Geoapify</a>',
    maxZoom: 20
  }
).addTo(map);

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

const iconSinSenal = L.divIcon({
  className: '',
  html: `<div style="
    width:16px; height:16px; border-radius:50%;
    background:#6b7280; border:2px solid #fff;
    box-shadow:0 0 8px rgba(107,114,128,0.8);
  "></div>`,
  iconSize: [16, 16]
});

function getIcon(nivel) {
  if (nivel === 'ROJO')      return iconRojo;
  if (nivel === 'AMARILLO')  return iconAmarillo;
  if (nivel === 'SIN_SENAL') return iconSinSenal;
  return iconVerde;
}

function textoNivel(nivel) {
  return nivel === 'SIN_SENAL' ? 'SIN SEÑAL' : nivel;
}

// Sin coordenadas (0,0 o vacías) el nodo no va al mapa: quedaría en el mar frente a África.
function tieneCoordenadas(s) {
  return s.latitud != null && s.longitud != null && !(s.latitud === 0 && s.longitud === 0);
}

const markers = {};
let mapaCentrado = false;

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
      const popup = `
          <div style="font-family:monospace; font-size:12px;">
            <b>📡 ${sensor.nombre}</b><br>
            📍 ${sensor.ubicacion || 'Sin ubicación'}<br>
            🟢 Estado: ${textoNivel(nivel)}<br>
            📌 Lat: ${sensor.latitud?.toFixed(6)}<br>
            📌 Lng: ${sensor.longitud?.toFixed(6)}
          </div>
        `;
      if (!tieneCoordenadas(sensor)) {
        if (markers[sensor.id]) { map.removeLayer(markers[sensor.id]); delete markers[sensor.id]; }
      } else if (markers[sensor.id]) {
        markers[sensor.id].setLatLng([sensor.latitud, sensor.longitud]);
        markers[sensor.id].setIcon(getIcon(nivel));
        markers[sensor.id].setPopupContent(popup);
      } else {
        markers[sensor.id] = L.marker(
          [sensor.latitud, sensor.longitud],
          { icon: getIcon(nivel) }
        )
        .bindPopup(popup)
        .addTo(map);
      }

      const item = document.createElement('div');
      item.className = 'sensor-item';
      item.innerHTML = `
        <div class="sensor-dot ${nivel.toLowerCase()}"></div>
        <div class="sensor-info">
          <div class="sensor-name">${sensor.nombre}${nivel === 'SIN_SENAL' ? ' · SIN SEÑAL' : ''}</div>
          <div class="sensor-location">${sensor.ubicacion || 'Sin ubicación'}</div>
        </div>
      `;
      lista.appendChild(item);
    });

    // Centrar el mapa una sola vez (después el usuario puede moverlo) en el primer sensor con posición
    const primero = data.find(tieneCoordenadas);
    if (!mapaCentrado && primero) {
      map.setView([primero.latitud, primero.longitud], 16);
      mapaCentrado = true;
    }

  } catch (err) {
    console.error('Error cargando sensores:', err);
  }
}

cargarSensores();
setInterval(cargarSensores, 10000);