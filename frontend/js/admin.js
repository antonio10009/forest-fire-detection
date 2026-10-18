// ─── CLAVE DE ADMINISTRADOR ────────────
// Las acciones que cambian datos (umbrales, marcar alerta atendida) piden la clave
// ADMIN_API_KEY del servidor. Se pide una vez y queda guardada en este navegador.
const CLAVE_ADMIN_LS = 'ff-admin-key';

function claveAdmin(pedirDeNuevo) {
  let clave = null;
  try { clave = localStorage.getItem(CLAVE_ADMIN_LS); } catch (e) {}
  if (!clave || pedirDeNuevo) {
    clave = prompt(pedirDeNuevo ? 'Clave incorrecta. Escribe la clave de administrador:'
                                : 'Clave de administrador (ADMIN_API_KEY del servidor):');
    if (!clave) return null;
    try { localStorage.setItem(CLAVE_ADMIN_LS, clave.trim()); } catch (e) {}
  }
  return clave.trim();
}

// fetch con la clave; si el servidor la rechaza, la pide otra vez (una vez).
async function fetchAdmin(url, opciones = {}) {
  for (let intento = 0; intento < 2; intento++) {
    const clave = claveAdmin(intento > 0);
    if (!clave) return null;
    const headers = Object.assign({}, opciones.headers || {}, { 'X-Admin-Key': clave });
    const res = await fetch(url, Object.assign({}, opciones, { headers }));
    if (res.status !== 401) return res;
    try { localStorage.removeItem(CLAVE_ADMIN_LS); } catch (e) {}
  }
  return null;
}
