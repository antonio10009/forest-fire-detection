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