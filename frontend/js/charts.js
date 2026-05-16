// ─── GRÁFICOS CHART.JS ─────────────────
const API_CHARTS = "https://forest-fire-detection-044r.onrender.com";

const labels = Array.from({length: 10}, (_, i) => `T-${9-i}`);

const tempCtx = document.getElementById('tempChart').getContext('2d');
const tempChart = new Chart(tempCtx, {
  type: 'line',
  data: {
    labels,
    datasets: [{
      label: 'Temperatura °C',
      data: Array(10).fill(0),
      borderColor: '#ff6b2b',
      backgroundColor: 'rgba(255,107,43,0.1)',
      borderWidth: 2,
      pointBackgroundColor: '#ff6b2b',
      pointRadius: 3,
      tension: 0.4,
      fill: true
    }]
  },
  options: {
    responsive: true,
    plugins: { legend: { labels: { color: '#8a9bb0', font: { family: 'Share Tech Mono' } } } },
    scales: {
      x: { ticks: { color: '#4a5568' }, grid: { color: '#1e2530' } },
      y: { ticks: { color: '#4a5568' }, grid: { color: '#1e2530' },
           suggestedMin: 0, suggestedMax: 100 }
    }
  }
});

const smokeCtx = document.getElementById('smokeChart').getContext('2d');
const smokeChart = new Chart(smokeCtx, {
  type: 'line',
  data: {
    labels,
    datasets: [{
      label: 'Humo PPM',
      data: Array(10).fill(0),
      borderColor: '#ffd426',
      backgroundColor: 'rgba(255,212,38,0.1)',
      borderWidth: 2,
      pointBackgroundColor: '#ffd426',
      pointRadius: 3,
      tension: 0.4,
      fill: true
    }]
  },
  options: {
    responsive: true,
    plugins: { legend: { labels: { color: '#8a9bb0', font: { family: 'Share Tech Mono' } } } },
    scales: {
      x: { ticks: { color: '#4a5568' }, grid: { color: '#1e2530' } },
      y: { ticks: { color: '#4a5568' }, grid: { color: '#1e2530' },
           suggestedMin: 0, suggestedMax: 700 }
    }
  }
});

async function actualizarGraficos() {
  try {
    const res  = await fetch(`${API_CHARTS}/api/sensors/1/lecturas`);
    const data = await res.json();

    const ultimas = data.slice(-10);
    const temps   = ultimas.map(l => l.temperatura);
    const humos   = ultimas.map(l => l.humo_ppm);
    const times   = ultimas.map(l =>
      new Date(l.registrado_en).toLocaleTimeString('es-CL')
    );

    tempChart.data.labels           = times;
    tempChart.data.datasets[0].data = temps;
    tempChart.update();

    smokeChart.data.labels           = times;
    smokeChart.data.datasets[0].data = humos;
    smokeChart.update();

    document.getElementById('total-readings').textContent = data.length;

  } catch (err) {
    console.error('Error actualizando gráficos:', err);
  }
}

async function cargarEstadisticas() {
  try {
    const [resumen, tempProm, zonaCritica, alertasDia] =
      await Promise.all([
        fetch(`${API_CHARTS}/api/stats/resumen`).then(r => r.json()),
        fetch(`${API_CHARTS}/api/stats/temperatura-promedio`).then(r => r.json()),
        fetch(`${API_CHARTS}/api/stats/zona-critica`).then(r => r.json()),
        fetch(`${API_CHARTS}/api/stats/alertas-por-dia`).then(r => r.json()),
      ]);

    document.getElementById('alertas-hoy').textContent    = resumen.alertas_hoy;
    document.getElementById('total-lecturas').textContent = resumen.total_lecturas;

    if (tempProm.length > 0) {
      document.getElementById('temp-promedio').textContent =
        tempProm[0].temp_promedio + '°C';
      document.getElementById('temp-max').textContent =
        tempProm[0].temp_max + '°C';
      document.getElementById('humo-promedio').textContent =
        tempProm[0].humo_promedio + ' PPM';
    }

    if (zonaCritica.nombre) {
      document.getElementById('zona-critica').textContent = zonaCritica.nombre;
    }

    if (alertasDia.length > 0) {
      const ctx = document.getElementById('alertasDiaChart').getContext('2d');
      new Chart(ctx, {
        type: 'bar',
        data: {
          labels: alertasDia.map(a => a.fecha),
          datasets: [{
            label: 'Alertas por día',
            data: alertasDia.map(a => a.total),
            backgroundColor: 'rgba(255,61,61,0.4)',
            borderColor: '#ff3d3d',
            borderWidth: 1,
            borderRadius: 2,
          }]
        },
        options: {
          responsive: true,
          plugins: {
            legend: {
              labels: { color: '#8a9bb0', font: { family: 'Share Tech Mono' } }
            }
          },
          scales: {
            x: { ticks: { color: '#4a5568' }, grid: { color: '#1e2530' } },
            y: { ticks: { color: '#4a5568' }, grid: { color: '#1e2530' },
                 beginAtZero: true }
          }
        }
      });
    }

  } catch (err) {
    console.error('Error cargando estadísticas:', err);
  }
}

actualizarGraficos();
cargarEstadisticas();
setInterval(actualizarGraficos,  10000);
setInterval(cargarEstadisticas,  30000);