// ─── GRÁFICOS CHART.JS ─────────────────

const labels = Array.from({length: 10}, (_, i) => `T-${9-i}`);

// Gráfico Temperatura
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

// Gráfico Humo
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

// Actualizar gráficos con lecturas reales
async function actualizarGraficos() {
  try {
    const res  = await fetch('http://127.0.0.1:8000/api/sensors/1/lecturas');
    const data = await res.json();

    const ultimas = data.slice(-10);
    const temps   = ultimas.map(l => l.temperatura);
    const humos   = ultimas.map(l => l.humo_ppm);
    const times   = ultimas.map(l =>
      new Date(l.registrado_en).toLocaleTimeString('es-CL')
    );

    tempChart.data.labels          = times;
    tempChart.data.datasets[0].data = temps;
    tempChart.update();

    smokeChart.data.labels          = times;
    smokeChart.data.datasets[0].data = humos;
    smokeChart.update();

    // Stats lecturas
    document.getElementById('total-readings').textContent = data.length;

  } catch (err) {
    console.error('Error actualizando gráficos:', err);
  }
}

actualizarGraficos();
setInterval(actualizarGraficos, 10000);

// ─── ESTADÍSTICAS DETALLADAS ───────────
async function cargarEstadisticas() {
  try {
    const [resumen, niveles, tempProm, zonaCritica, alertasDia] =
      await Promise.all([
        fetch('http://127.0.0.1:8000/api/stats/resumen').then(r => r.json()),
        fetch('http://127.0.0.1:8000/api/stats/niveles').then(r => r.json()),
        fetch('http://127.0.0.1:8000/api/stats/temperatura-promedio').then(r => r.json()),
        fetch('http://127.0.0.1:8000/api/stats/zona-critica').then(r => r.json()),
        fetch('http://127.0.0.1:8000/api/stats/alertas-por-dia').then(r => r.json()),
      ]);

    // Resumen
    document.getElementById('alertas-hoy').textContent    = resumen.alertas_hoy;
    document.getElementById('total-lecturas').textContent = resumen.total_lecturas;

    // Temperatura promedio
    if (tempProm.length > 0) {
      document.getElementById('temp-promedio').textContent =
        tempProm[0].temp_promedio + '°C';
      document.getElementById('temp-max').textContent =
        tempProm[0].temp_max + '°C';
      document.getElementById('humo-promedio').textContent =
        tempProm[0].humo_promedio + ' PPM';
    }

    // Zona crítica
    if (zonaCritica.nombre) {
      document.getElementById('zona-critica').textContent = zonaCritica.nombre;
    }

    // Gráfico alertas por día
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

cargarEstadisticas();
setInterval(cargarEstadisticas, 30000);