// ═══════════════════════════════════════════════════════════════
// beep_alerta.js — Sonido de alerta en el navegador
// Añadir al final de frontend/js/alerts.js
// ═══════════════════════════════════════════════════════════════

// ─── MOTOR DE AUDIO WEB API ───────────────────────────────────
let audioCtx = null;
let ultimasAlertasIds = new Set();
let beepActivo = false;

function getAudioCtx() {
  if (!audioCtx) {
    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  }
  return audioCtx;
}

function tocarBeepEmergencia() {
  if (beepActivo) return;
  beepActivo = true;

  try {
    const ctx = getAudioCtx();

    // Secuencia de 3 pitidos cortos + 1 largo (sirena de emergencia)
    const secuencia = [
      { freq: 880, duracion: 0.12, pausa: 0.08 },
      { freq: 880, duracion: 0.12, pausa: 0.08 },
      { freq: 880, duracion: 0.12, pausa: 0.08 },
      { freq: 1100, duracion: 0.5,  pausa: 0.1  },
      { freq: 880, duracion: 0.12, pausa: 0.08 },
      { freq: 880, duracion: 0.12, pausa: 0.08 },
      { freq: 1100, duracion: 0.5,  pausa: 0.0  },
    ];

    let tiempoAcumulado = ctx.currentTime + 0.05;

    secuencia.forEach(nota => {
      const oscilador = ctx.createOscillator();
      const ganancia  = ctx.createGain();

      oscilador.connect(ganancia);
      ganancia.connect(ctx.destination);

      oscilador.type      = 'square';
      oscilador.frequency.setValueAtTime(nota.freq, tiempoAcumulado);

      // Envolvente: ataque rápido, caída suave
      ganancia.gain.setValueAtTime(0, tiempoAcumulado);
      ganancia.gain.linearRampToValueAtTime(0.35, tiempoAcumulado + 0.01);
      ganancia.gain.linearRampToValueAtTime(0, tiempoAcumulado + nota.duracion);

      oscilador.start(tiempoAcumulado);
      oscilador.stop(tiempoAcumulado + nota.duracion);

      tiempoAcumulado += nota.duracion + nota.pausa;
    });

    // Repetir 2 veces más con pausa entre repeticiones
    setTimeout(() => tocarBeepEmergencia(), (tiempoAcumulado - ctx.currentTime + 0.4) * 1000);
    setTimeout(() => { beepActivo = false; }, 8000); // detener después de 8s

  } catch (err) {
    console.warn('Audio no disponible:', err);
    beepActivo = false;
  }
}

function detenerBeep() {
  beepActivo = false;
  if (audioCtx) {
    audioCtx.close();
    audioCtx = null;
  }
}

// ─── INTEGRAR CON cargarAlertas() ─────────────────────────────
// Reemplaza la función cargarAlertas existente en alerts.js con esta versión
// que detecta nuevas alertas ROJO y dispara el beep automáticamente

async function cargarAlertasConBeep() {
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
      ultimasAlertasIds.clear();
      detenerBeep();
      return;
    }

    document.body.classList.add('alerta-activa');

    // Detectar si hay alertas NUEVAS que no estaban antes
    const idsActuales = new Set(data.map(a => a.id));
    const hayNuevas = data.some(a => !ultimasAlertasIds.has(a.id));

    if (hayNuevas && data.length > 0) {
      tocarBeepEmergencia();
    }

    ultimasAlertasIds = idsActuales;

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

// Sobrescribir la función original
window.cargarAlertas = cargarAlertasConBeep;

// Activar audio en el primer clic del usuario (requerido por navegadores modernos)
document.addEventListener('click', () => {
  if (!audioCtx) {
    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  }
}, { once: true });