// ═══════════════════════════════════════════════════════════════
// ia.js — PASO 17: Insights IA + Chatbot + Propagación
// Sistema de Detección Temprana de Incendios Forestales
// ═══════════════════════════════════════════════════════════════

const API_IA = "https://forest-fire-detection-044r.onrender.com";

// ─── HISTORIAL DEL CHATBOT ─────────────────────────────────────
const historialChat = [];

// ─── INSIGHTS AUTOMÁTICOS ─────────────────────────────────────
async function generarInsights() {
  const panel = document.getElementById('ia-insights-content');
  if (!panel) return;

  try {
    // 1. Obtener última lectura del sensor
    const resLecturas = await fetch(`${API_IA}/api/sensors/1/lecturas`);
    const lecturas = await resLecturas.json();
    if (!lecturas || lecturas.length === 0) {
      panel.innerHTML = '<span class="ia-insight-loading">Sin datos disponibles.</span>';
      return;
    }

    const ultima = lecturas[lecturas.length - 1];
    const { temperatura, humo_ppm, humedad, nivel_alerta, registrado_en } = ultima;

    // Ignorar lecturas con DHT22 fallido
    const dht22_ok = !(temperatura === 0 && humedad === 0);

    // 2. Clasificación IA
    let nivelIA = nivel_alerta;
    let confianzaIA = 0;
    let probabilidades = {};
    if (dht22_ok) {
      try {
        const resIA = await fetch(`${API_IA}/api/ml/predecir`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ temperatura, humo_ppm, humedad })
        });
        const dataIA = await resIA.json();
        nivelIA       = dataIA.nivel_predicho;
        confianzaIA   = dataIA.confianza_porcentaje;
        probabilidades = dataIA.probabilidades || {};
      } catch (_) {}
    }

    // 3. Anomaly Detection
    let esAnomalia = false;
    let nivelAnomalia = 'NORMAL';
    if (dht22_ok) {
      try {
        const resAnom = await fetch(`${API_IA}/api/ml/anomalia`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ temperatura, humo_ppm, humedad })
        });
        const dataAnom = await resAnom.json();
        esAnomalia   = dataAnom.es_anomalia;
        nivelAnomalia = dataAnom.nivel_riesgo;
      } catch (_) {}
    }

    // 4. Estadísticas rápidas
    let totalLecturas = lecturas.length;
    let alertasActivas = 0;
    try {
      const resAlerts = await fetch(`${API_IA}/api/alerts/`);
      const alertas = await resAlerts.json();
      alertasActivas = alertas.length;
    } catch (_) {}

    // 5. Generar texto de insights en lenguaje natural
    const hora = new Date(registrado_en).toLocaleTimeString('es-CL');
    const colorNivel = { VERDE: '#00ff88', AMARILLO: '#ffd426', ROJO: '#ff3d3d' };
    const emojiNivel = { VERDE: '🟢', AMARILLO: '🟡', ROJO: '🔴' };

    // Análisis de tendencia (últimas 5 lecturas)
    const ultimas5 = lecturas.slice(-5);
    const tendenciaTemp = ultimas5.length >= 2
      ? ultimas5[ultimas5.length - 1].temperatura - ultimas5[0].temperatura
      : 0;
    const tendenciaHumo = ultimas5.length >= 2
      ? ultimas5[ultimas5.length - 1].humo_ppm - ultimas5[0].humo_ppm
      : 0;

    const textoTendenciaTemp = tendenciaTemp > 2 ? '↑ en aumento' :
                               tendenciaTemp < -2 ? '↓ en descenso' : '→ estable';
    const textoTendenciaHumo = tendenciaHumo > 20 ? '↑ en aumento' :
                               tendenciaHumo < -20 ? '↓ en descenso' : '→ estable';

    // Mensaje principal según nivel
    let mensajePrincipal = '';
    let classMensaje = '';
    if (nivelIA === 'VERDE') {
      mensajePrincipal = dht22_ok
        ? `Sistema operando en condiciones normales. No se detectan riesgos de incendio en este momento.`
        : `Sensor DHT22 sin lectura. Sistema parcialmente operativo. El MQ-2 reporta humo ${humo_ppm} ppm.`;
      classMensaje = 'ia-status-verde';
    } else if (nivelIA === 'AMARILLO') {
      mensajePrincipal = `⚠️ Precaución. El modelo IA detecta condiciones anómalas. Se recomienda monitoreo intensificado y verificación en terreno.`;
      classMensaje = 'ia-status-amarillo';
    } else if (nivelIA === 'ROJO') {
      mensajePrincipal = `🔥 ALERTA CRÍTICA. Alta probabilidad de incendio forestal confirmada por IA. Activar protocolo de emergencia inmediatamente.`;
      classMensaje = 'ia-status-rojo';
    } else {
      mensajePrincipal = `Sensor en proceso de inicialización. Datos insuficientes para análisis completo.`;
      classMensaje = '';
    }

    // Renderizar
    panel.innerHTML = `
      <div class="ia-status-badge ${classMensaje}">
        ${emojiNivel[nivelIA] || '⚪'} IA: ${nivelIA}
        ${confianzaIA > 0 ? `<span class="ia-confianza">${confianzaIA}% confianza</span>` : ''}
      </div>

      <p class="ia-mensaje-principal">${mensajePrincipal}</p>

      <div class="ia-metrics-row">
        ${dht22_ok ? `
        <div class="ia-metric">
          <span class="ia-metric-label">TEMPERATURA</span>
          <span class="ia-metric-value" style="color:${temperatura > 50 ? '#ff6b2b' : '#00aaff'}">${temperatura}°C</span>
          <span class="ia-metric-trend">${textoTendenciaTemp}</span>
        </div>
        <div class="ia-metric">
          <span class="ia-metric-label">HUMEDAD</span>
          <span class="ia-metric-value" style="color:${humedad < 20 ? '#ff3d3d' : '#00ff88'}">${humedad}%</span>
          <span class="ia-metric-trend">→ estable</span>
        </div>
        ` : `
        <div class="ia-metric">
          <span class="ia-metric-label">DHT22</span>
          <span class="ia-metric-value" style="color:#ff3d3d">Sin lectura</span>
          <span class="ia-metric-trend">— error sensor</span>
        </div>
        `}
        <div class="ia-metric">
          <span class="ia-metric-label">HUMO PPM</span>
          <span class="ia-metric-value" style="color:${humo_ppm > 300 ? '#ff3d3d' : humo_ppm > 150 ? '#ffd426' : '#00ff88'}">${humo_ppm}</span>
          <span class="ia-metric-trend">${textoTendenciaHumo}</span>
        </div>
      </div>

      <div class="ia-anomalia-row">
        <div class="ia-anomalia-badge ${esAnomalia ? 'anomalia-activa' : 'anomalia-ok'}">
          ${esAnomalia ? '⚠️ ANOMALÍA DETECTADA' : '✓ Comportamiento normal'}
          <span class="ia-anomalia-nivel">${nivelAnomalia}</span>
        </div>
        <div class="ia-stats-mini">
          <span>📊 ${totalLecturas} lecturas</span>
          ${alertasActivas > 0
            ? `<span style="color:#ff3d3d">🚨 ${alertasActivas} alerta${alertasActivas > 1 ? 's' : ''}</span>`
            : `<span style="color:#00ff88">✅ Sin alertas</span>`
          }
          <span style="color:#4a5568">🕐 ${hora}</span>
        </div>
      </div>

      ${Object.keys(probabilidades).length > 0 ? `
      <div class="ia-probabilidades">
        <span class="ia-prob-label">PROBABILIDADES</span>
        <div class="ia-prob-bars">
          ${Object.entries(probabilidades).map(([nivel, prob]) => `
            <div class="ia-prob-item">
              <span class="ia-prob-nombre">${nivel}</span>
              <div class="ia-prob-barra-fondo">
                <div class="ia-prob-barra" style="width:${prob}%; background:${colorNivel[nivel] || '#8a9bb0'}"></div>
              </div>
              <span class="ia-prob-valor">${prob}%</span>
            </div>
          `).join('')}
        </div>
      </div>
      ` : ''}
    `;

  } catch (err) {
    console.error('Error generando insights:', err);
    panel.innerHTML = '<span class="ia-insight-loading">Error conectando con el sistema IA.</span>';
  }
}

// ─── CHATBOT ───────────────────────────────────────────────────
async function procesarPregunta(pregunta) {
  const texto = pregunta.toLowerCase().trim();

  // Detectar intención y consultar endpoints relevantes
  try {

    // TEMPERATURA
    if (/temperatura|calor|grados|°c|frío|frio/i.test(texto)) {
      const res = await fetch(`${API_IA}/api/stats/temperatura-promedio`);
      const data = await res.json();
      if (data && data.length > 0) {
        const d = data[0];
        return `🌡️ **Temperatura del sensor:**\n• Promedio: ${d.temp_promedio}°C\n• Máxima: ${d.temp_max}°C\n• Mínima: ${d.temp_min || '—'}°C\n\nEl umbral de alerta AMARILLO es 50°C y ROJO es 70°C.`;
      }
      return '🌡️ No hay datos de temperatura disponibles aún.';
    }

    // HUMO / GAS
    if (/humo|ppm|gas|gases|monóxido|co|aire/i.test(texto)) {
      const res = await fetch(`${API_IA}/api/sensors/1/lecturas`);
      const data = await res.json();
      if (data && data.length > 0) {
        const ultimas = data.slice(-5);
        const promedioHumo = (ultimas.reduce((s, l) => s + l.humo_ppm, 0) / ultimas.length).toFixed(1);
        const maxHumo = Math.max(...ultimas.map(l => l.humo_ppm));
        return `💨 **Nivel de humo (últimas 5 lecturas):**\n• Promedio: ${promedioHumo} ppm\n• Máximo: ${maxHumo} ppm\n\nEl umbral AMARILLO es 200 ppm y ROJO es 500 ppm. Valores normales están entre 70-150 ppm.`;
      }
      return '💨 No hay datos de humo disponibles aún.';
    }

    // ALERTA / INCENDIO / EMERGENCIA
    if (/alerta|incendio|emergencia|fuego|rojo|crítico|critico/i.test(texto)) {
      const resAlerts = await fetch(`${API_IA}/api/alerts/`);
      const alertas = await resAlerts.json();
      const resHist = await fetch(`${API_IA}/api/alerts/historial`);
      const historial = await resHist.json();
      if (alertas.length === 0) {
        return `✅ **Sin alertas activas en este momento.**\n\n📋 Historial total: ${historial.length} alertas registradas.\n\nEl sistema monitorea continuamente los sensores y enviará una alerta WhatsApp automática si se detecta nivel ROJO.`;
      }
      return `🔥 **${alertas.length} alerta(s) activa(s):**\n${alertas.map(a => `• ${a.tipo}: ${a.mensaje}`).join('\n')}\n\n⚠️ Se enviaron notificaciones WhatsApp automáticamente.`;
    }

    // ESTADÍSTICAS / RESUMEN
    if (/estadística|estadistica|resumen|total|cuántos|cuantos|datos|lecturas/i.test(texto)) {
      const res = await fetch(`${API_IA}/api/stats/resumen`);
      const data = await res.json();
      return `📊 **Resumen del sistema:**\n• Total lecturas: ${data.total_lecturas}\n• Alertas hoy: ${data.alertas_hoy}\n• Sensores activos: ${data.sensores_activos || 1}\n• Lecturas hoy: ${data.lecturas_hoy || '—'}\n\nEl sistema lleva registrando datos desde junio 2026.`;
    }

    // PREDICCIÓN / PROPAGACIÓN
    if (/propagación|propagacion|viento|extiende|avanza|área|area|hectárea|hectarea/i.test(texto)) {
      const res = await fetch(`${API_IA}/api/ml/propagacion`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          latitud: -33.0472, longitud: -71.6127,
          temperatura: 35.0, humedad: 15.0,
          viento_velocidad: 40.0, viento_direccion: 225.0,
          minutos: 30
        })
      });
      const data = await res.json();
      return `🔥 **Simulación de propagación (condiciones típicas Valparaíso):**\n• Área estimada en 30 min: ${data.area_hectareas} hectáreas\n• Nivel de peligro: ${data.peligro}\n• Velocidad de propagación: ${data.ros_m_por_min} m/min\n• ${data.mensaje}\n\n⚠️ Simulación basada en 35°C, 15% humedad, viento 40 km/h del suroeste.`;
    }

    // ANOMALÍA
    if (/anomalía|anomalia|inusual|anormal|extraño|extrano|detección|deteccion/i.test(texto)) {
      const resLect = await fetch(`${API_IA}/api/sensors/1/lecturas`);
      const lecturas = await resLect.json();
      if (lecturas && lecturas.length > 0) {
        const ult = lecturas[lecturas.length - 1];
        const res = await fetch(`${API_IA}/api/ml/anomalia`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            temperatura: ult.temperatura,
            humo_ppm: ult.humo_ppm,
            humedad: ult.humedad
          })
        });
        const data = await res.json();
        return `🔍 **Análisis de anomalías (última lectura):**\n• Temperatura: ${ult.temperatura}°C\n• Humo: ${ult.humo_ppm} ppm\n• Humedad: ${ult.humedad}%\n\n${data.es_anomalia ? `⚠️ ANOMALÍA DETECTADA\n• Nivel: ${data.nivel_riesgo}\n• ${data.mensaje}` : `✅ Comportamiento normal\n• Nivel: ${data.nivel_riesgo}\n• ${data.mensaje}`}`;
      }
      return '🔍 No hay lecturas disponibles para analizar anomalías.';
    }

    // SENSOR / GPS / UBICACIÓN
    if (/sensor|gps|ubicación|ubicacion|coordenada|dónde|donde|cerro/i.test(texto)) {
      const res = await fetch(`${API_IA}/api/sensors/`);
      const data = await res.json();
      if (data && data.length > 0) {
        const s = data[0];
        return `📡 **Sensor registrado:**\n• Nombre: ${s.nombre}\n• Ubicación: ${s.ubicacion}\n• Coordenadas GPS: ${s.latitud}, ${s.longitud}\n• Estado: ${s.activo ? 'Activo ✓' : 'Inactivo ✗'}\n\nEl sensor envía datos cada 5 minutos usando deep sleep para conservar batería solar.`;
      }
      return '📡 No se encontraron sensores registrados.';
    }

    // BATERÍA / ENERGÍA / SOLAR
    if (/batería|bateria|solar|energía|energia|panel|carga/i.test(texto)) {
      return `⚡ **Sistema de energía:**\n• Panel solar: 6V 3.3W\n• Batería: 18650 Li-Ion 2600mAh\n• Cargador: TP4056\n• Autonomía sin sol: ~24-48 horas\n• Modo ahorro: Deep Sleep entre lecturas (5 min)\n• Consumo activo: ~240mA | Consumo dormido: <0.01mA\n\nEl sistema es completamente autónomo una vez instalado.`;
    }

    // MODELO IA
    if (/modelo|ia|inteligencia|artificial|clasificación|clasificacion|random|forest|isolation/i.test(texto)) {
      const res = await fetch(`${API_IA}/api/ml/info`);
      const data = await res.json();
      return `🤖 **Modelos de IA activos:**\n\n1. **${data.tipo}** (Clasificación)\n   • Clases: ${data.clases.join(', ')}\n   • Variables: ${data.features.join(', ')}\n   • Estimadores: ${data.n_estimadores}\n\n2. **Isolation Forest** (Anomaly Detection)\n   • Detecta comportamientos inusuales\n   • Entrenado con datos normales reales\n\n3. **McArthur FFDI** (Propagación)\n   • Modelo físico de elipse de Huygens\n   • Genera polígono GeoJSON en tiempo real`;
    }

    // AYUDA / QUÉ PUEDO PREGUNTAR
    if (/ayuda|help|qué puedes|que puedes|comandos|preguntar|funciones/i.test(texto)) {
      return `🤖 **Puedo responder preguntas sobre:**\n\n🌡️ Temperatura → "¿Cuál es la temperatura actual?"\n💨 Humo → "¿Cuánto humo detecta el sensor?"\n🚨 Alertas → "¿Hay alertas de incendio activas?"\n📊 Estadísticas → "¿Cuántas lecturas hay registradas?"\n🔍 Anomalías → "¿Hay anomalías detectadas?"\n🔥 Propagación → "¿Cómo se propagaría un incendio?"\n📡 Sensor → "¿Dónde está el sensor?"\n⚡ Energía → "¿Cómo funciona la batería solar?"\n🤖 Modelo IA → "¿Qué modelos de IA usa el sistema?"`;
    }

    // SALUDO
    if (/hola|buenos|buenas|saludos|hey|hi/i.test(texto)) {
      return `👋 Hola. Soy el asistente de análisis del sistema Forest Fire Detection.\n\nPuedo consultarte datos en tiempo real sobre temperatura, humo, alertas, anomalías y propagación de incendios en Valparaíso.\n\nEscribe **ayuda** para ver qué puedo responder.`;
    }

    // RESPUESTA POR DEFECTO
    return `🤔 No entendí bien la consulta. Intenta preguntar sobre:\n• temperatura, humo, alertas, estadísticas\n• anomalías, propagación, sensor, batería\n\nEscribe **ayuda** para ver todos los temas disponibles.`;

  } catch (err) {
    console.error('Error en chatbot:', err);
    return '⚠️ Error al consultar el sistema. Verifica que el servidor esté activo e intenta nuevamente.';
  }
}

function agregarMensaje(texto, tipo) {
  const container = document.getElementById('chat-messages');
  if (!container) return;

  const msg = document.createElement('div');
  msg.className = `chat-msg chat-msg-${tipo}`;

  // Formatear markdown básico: **negrita**, bullet points, saltos de línea
  const formateado = texto
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>');

  msg.innerHTML = `
    <div class="chat-msg-avatar">${tipo === 'user' ? '👤' : '🤖'}</div>
    <div class="chat-msg-content">${formateado}</div>
  `;
  container.appendChild(msg);
  container.scrollTop = container.scrollHeight;
}

async function enviarMensaje() {
  const input = document.getElementById('chat-input');
  if (!input) return;

  const texto = input.value.trim();
  if (!texto) return;

  input.value = '';
  input.disabled = true;

  const btnEnviar = document.getElementById('chat-btn-enviar');
  if (btnEnviar) btnEnviar.disabled = true;

  // Mostrar mensaje del usuario
  agregarMensaje(texto, 'user');

  // Indicador de carga
  const container = document.getElementById('chat-messages');
  const loadingMsg = document.createElement('div');
  loadingMsg.className = 'chat-msg chat-msg-bot';
  loadingMsg.id = 'chat-loading';
  loadingMsg.innerHTML = `
    <div class="chat-msg-avatar">🤖</div>
    <div class="chat-msg-content"><span class="chat-typing">Analizando datos<span class="dots">...</span></span></div>
  `;
  if (container) container.appendChild(loadingMsg);
  if (container) container.scrollTop = container.scrollHeight;

  // Procesar
  const respuesta = await procesarPregunta(texto);

  // Eliminar loading y mostrar respuesta
  const loading = document.getElementById('chat-loading');
  if (loading) loading.remove();
  agregarMensaje(respuesta, 'bot');

  input.disabled = false;
  if (btnEnviar) btnEnviar.disabled = false;
  input.focus();
}

// ─── SIMULACIÓN DE PROPAGACIÓN EN EL MAPA ──────────────────────
let propagacionLayer = null;
let simulacionActiva = false;

async function simularPropagacion() {
  const btnSimular = document.getElementById('btn-simular-prop');
  const panel = document.getElementById('panel-simulacion');

  if (!simulacionActiva) {
    // Mostrar panel de parámetros
    if (panel) panel.classList.add('panel-visible');
    simulacionActiva = true;
    if (btnSimular) {
      btnSimular.textContent = '✕ CERRAR SIM';
      btnSimular.classList.add('btn-activo');
    }
  } else {
    // Cerrar y limpiar
    if (panel) panel.classList.remove('panel-visible');
    simulacionActiva = false;
    if (btnSimular) {
      btnSimular.textContent = '🔥 SIMULAR';
      btnSimular.classList.remove('btn-activo');
    }
    if (propagacionLayer && typeof map !== 'undefined') {
      map.removeLayer(propagacionLayer);
      propagacionLayer = null;
    }
  }
}

async function ejecutarSimulacion() {
  const velocidad  = parseFloat(document.getElementById('sim-velocidad')?.value || 30);
  const direccion  = parseFloat(document.getElementById('sim-direccion')?.value || 225);
  const minutos    = parseInt(document.getElementById('sim-minutos')?.value || 30);
  const temperatura = parseFloat(document.getElementById('sim-temperatura')?.value || 35);
  const humedad    = parseFloat(document.getElementById('sim-humedad')?.value || 15);

  const resultDiv = document.getElementById('sim-resultado');
  if (resultDiv) resultDiv.innerHTML = '<span style="color:#ffd426">Calculando...</span>';

  try {
    // Obtener coordenadas del sensor desde la API
    const resSensor = await fetch(`${API_IA}/api/sensors/1`);
    const sensor = await resSensor.json();

    const res = await fetch(`${API_IA}/api/ml/propagacion`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        latitud: sensor.latitud,
        longitud: sensor.longitud,
        temperatura, humedad,
        viento_velocidad: velocidad,
        viento_direccion: direccion,
        minutos
      })
    });

    const data = await res.json();
    const colorPeligro = {
      BAJO: '#ffd426', MODERADO: '#ff6b2b', ALTO: '#ff4500', EXTREMO: '#cc0000'
    };

    // Eliminar polígono anterior
    if (propagacionLayer && typeof map !== 'undefined') {
      map.removeLayer(propagacionLayer);
    }

    // Dibujar nuevo polígono en el mapa
    if (typeof map !== 'undefined' && data.zona_riesgo) {
      propagacionLayer = L.geoJSON(data.zona_riesgo, {
        style: {
          color: colorPeligro[data.peligro] || '#ff6b2b',
          fillColor: colorPeligro[data.peligro] || '#ff6b2b',
          fillOpacity: 0.25,
          weight: 2,
          dashArray: '6 4'
        }
      })
      .bindPopup(`
        <div style="font-family:monospace;font-size:12px;min-width:200px;">
          <b style="color:${colorPeligro[data.peligro]}">🔥 ZONA DE RIESGO — ${data.peligro}</b><br>
          ⏱ En ${minutos} minutos<br>
          📐 Área: ${data.area_hectareas} hectáreas<br>
          💨 Viento: ${velocidad} km/h dir. ${direccion}°<br>
          🌡️ Temp: ${temperatura}°C | Hum: ${humedad}%<br>
          <br><em>${data.mensaje}</em>
        </div>
      `)
      .addTo(map);

      // Centrar mapa en la zona
      map.fitBounds(propagacionLayer.getBounds(), { padding: [20, 20] });
      propagacionLayer.openPopup();
    }

    // Mostrar resultado en el panel
    if (resultDiv) {
      resultDiv.innerHTML = `
        <div class="sim-result-item">
          <span class="sim-result-label">PELIGRO</span>
          <span class="sim-result-val" style="color:${colorPeligro[data.peligro]}">${data.peligro}</span>
        </div>
        <div class="sim-result-item">
          <span class="sim-result-label">ÁREA</span>
          <span class="sim-result-val">${data.area_hectareas} ha</span>
        </div>
        <div class="sim-result-item">
          <span class="sim-result-label">VELOCIDAD</span>
          <span class="sim-result-val">${data.ros_m_por_min} m/min</span>
        </div>
      `;
    }

  } catch (err) {
    console.error('Error simulando propagación:', err);
    if (resultDiv) resultDiv.innerHTML = '<span style="color:#ff3d3d">Error al calcular</span>';
  }
}

// ─── INICIALIZACIÓN ────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  // Insights automáticos
  generarInsights();
  setInterval(generarInsights, 30000);

  // Enter en el chat
  const chatInput = document.getElementById('chat-input');
  if (chatInput) {
    chatInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        enviarMensaje();
      }
    });
  }

  // Mensaje de bienvenida en el chat
  setTimeout(() => {
    agregarMensaje('Hola. Soy el asistente de análisis del sistema Forest Fire Detection. Escribe **ayuda** para ver qué puedo responder.', 'bot');
  }, 500);
});