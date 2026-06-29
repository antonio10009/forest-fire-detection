// ═══════════════════════════════════════════════════════════════
// beep_alerta.js — Sonido de alerta en el navegador (v2)
// ═══════════════════════════════════════════════════════════════

let audioCtx = null;
let intervalBeep = null;

function getCtx() {
  if (!audioCtx || audioCtx.state === 'closed') {
    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  }
  if (audioCtx.state === 'suspended') {
    audioCtx.resume();
  }
  return audioCtx;
}

function pitido(frecuencia, inicio, duracion) {
  const ctx = getCtx();
  const osc = ctx.createOscillator();
  const gan = ctx.createGain();
  osc.connect(gan);
  gan.connect(ctx.destination);
  osc.type = 'square';
  osc.frequency.value = frecuencia;
  gan.gain.setValueAtTime(0, inicio);
  gan.gain.linearRampToValueAtTime(0.3, inicio + 0.01);
  gan.gain.linearRampToValueAtTime(0, inicio + duracion - 0.01);
  osc.start(inicio);
  osc.stop(inicio + duracion);
}

function tocarSirena() {
  try {
    const ctx = getCtx();
    const t = ctx.currentTime;
    pitido(880,  t + 0.0,  0.1);
    pitido(880,  t + 0.2,  0.1);
    pitido(880,  t + 0.4,  0.1);
    pitido(1100, t + 0.6,  0.5);
  } catch(e) {
    console.warn('Audio error:', e);
  }
}

function iniciarBeep() {
  if (intervalBeep) return;
  tocarSirena();
  let repeticiones = 1;
  intervalBeep = setInterval(() => {
    if (repeticiones >= 3) {
      detenerBeep();
      return;
    }
    tocarSirena();
    repeticiones++;
  }, 2000);
}

function detenerBeep() {
  if (intervalBeep) {
    clearInterval(intervalBeep);
    intervalBeep = null;
  }
}

// Activar AudioContext en primer clic
document.addEventListener('click', () => {
  try { getCtx(); } catch(e) {}
});

// Esperar a que todo esté cargado antes de reemplazar
window.addEventListener('load', () => {
  const _original = window.cargarAlertas;

  window.cargarAlertas = async function() {
    await _original();
    try {
      const res = await fetch(`${API_ALERTS}/api/alerts/`);
      const data = await res.json();
      if (data.length > 0) {
        iniciarBeep();
      } else {
        detenerBeep();
      }
    } catch(e) {}
  };

  // Ejecutar inmediatamente al cargar para verificar estado actual
  window.cargarAlertas();
});

// Accesibles globalmente para pruebas en consola
window.tocarBeepEmergencia = tocarSirena;
window.iniciarBeep = iniciarBeep;
window.detenerBeep = detenerBeep;