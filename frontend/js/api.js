// Cliente de la API FastAPI (backend/app).
// El backend sirve esta interfaz en http://127.0.0.1:8000/app/ → la API está en el mismo origen
// (también funciona así desde el celular o un túnel HTTPS). Si se abre con Live Server (:5500),
// se habla con uvicorn en el puerto 8000 del mismo equipo.
export const API_URL = location.port === "5500"
  ? `${location.protocol}//${location.hostname}:8000`
  : location.origin;

// Estado de conexión con el backend; app.js lo actualiza periódicamente con /salud.
export const conexion = { disponible: false, ocr: null, ocrDisponible: false, ocrVersion: null };

// Usuario de la sesión; lo llena sesion.js con /auth/yo o al iniciar sesión.
export const sesion = { usuario: null, pruebasActivas: false };
export const esAdmin = () => sesion.usuario?.rol === "administrador";

// El OCR prueba varias versiones de cada foto: con varias imágenes puede tardar bastante.
const TIEMPO_OCR = 5 * 60 * 1000;

// sesion.js registra aquí cómo pedir la contraseña cuando la sesión vence (401).
let reautenticar = null;
export function alVencerSesion(fn) { reautenticar = fn; }

// `reintentar: false` = no abrir la ventana de sesión vencida ante un 401 (rutas de /auth).
async function pedir(ruta, opciones = {}, timeoutMs = 10000) {
  const { reintentar = true, ...fetchOpciones } = opciones;
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), timeoutMs);
  let r;
  try {
    // credentials: "include" envía la cookie de sesión también desde Live Server (:5500).
    r = await fetch(`${API_URL}${ruta}`, { credentials: "include", ...fetchOpciones, signal: ctrl.signal });
  } catch (err) {
    if (err.name === "AbortError") throw new Error("El servidor tardó demasiado en responder.");
    throw Object.assign(new Error("No se pudo conectar con el servidor."), { sinConexion: true });
  } finally {
    clearTimeout(t);
  }

  // Sesión vencida: se pide la contraseña encima de la pantalla actual y se repite
  // la petición, sin perder lo que el usuario estaba haciendo (p. ej. sus fotos).
  if (r.status === 401 && reintentar && reautenticar) {
    await reautenticar();
    return pedir(ruta, { ...opciones, reintentar: false }, timeoutMs);
  }

  if (!r.ok) {
    // FastAPI devuelve {"detail": "..."}; se muestra tal cual al usuario.
    const detalle = await r.json().then(d => d.detail, () => null);
    throw Object.assign(new Error(typeof detalle === "string" ? detalle : `Error ${r.status} en ${ruta}`),
                        { status: r.status });
  }
  return r.status === 204 ? null : r.json();
}

// ---------- Sesión ----------

export function entrar(correo, contrasena) {
  return pedir("/auth/entrar", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ correo, contrasena }),
    reintentar: false,
  });
}

export function salir() {
  return pedir("/auth/salir", { method: "POST", reintentar: false });
}

// Devuelve { usuario, pruebas_activas } o null si no hay sesión.
// Sin conexión lanza un error con `sinConexion`.
export async function yo() {
  try {
    return await pedir("/auth/yo", { reintentar: false });
  } catch (err) {
    if (err.status === 401) return null;
    throw err;
  }
}

export function cambiarContrasena(actual, nueva) {
  return pedir("/auth/cambiar-contrasena", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ actual, nueva }),
    reintentar: false,
  });
}

export async function salud() {
  try {
    const d = await pedir("/salud", {}, 4000);
    Object.assign(conexion, { ocr: d.ocr ?? null, ocrDisponible: !!d.ocr_disponible, ocrVersion: d.ocr_version ?? null });
    return d.estado === "ok";
  } catch {
    return false;
  }
}

function formulario(archivos) {
  const form = new FormData();
  archivos.forEach(a => form.append("archivos", a));
  return form;
}

// Crea el análisis: sube las fotos, ejecuta OCR + reglas y lo guarda en SQLite.
// esPrueba: lo guarda en el bloque de pruebas del equipo.
export function analizar(archivos, { esPrueba = false } = {}) {
  const form = formulario(archivos);
  if (esPrueba) form.append("es_prueba", "true");
  return pedir("/analisis/imagenes", { method: "POST", body: form }, TIEMPO_OCR);
}

// CU-06: agrega fotos a un análisis existente; solo se leen las nuevas y se reevalúan las reglas.
export function agregarEvidencia(idAnalisis, archivos) {
  return pedir(`/analisis/${idAnalisis}/imagenes`, { method: "POST", body: formulario(archivos) }, TIEMPO_OCR);
}

// Análisis propios (sin las pruebas).
export function listarAnalisis() {
  return consultarHistorial().then(d => d.analisis);
}

// ambito: "mios" | "pruebas" | "todos" (solo administrador, con filtro opcional por usuario).
export function consultarHistorial({ ambito = "mios", usuarioId = null } = {}) {
  const params = new URLSearchParams({ ambito });
  if (usuarioId) params.set("usuario_id", usuarioId);
  return pedir(`/analisis/historial?${params}`)
    .then(d => ({ analisis: d.analisis ?? [], usuarios: d.usuarios ?? [] }));
}

export function obtenerAnalisis(idAnalisis) {
  return pedir(`/analisis/${idAnalisis}`);
}

export function eliminarAnalisis(idAnalisis) {
  return pedir(`/analisis/${idAnalisis}`, { method: "DELETE" });
}

// Cierra el análisis: queda en solo lectura (sin fotos nuevas ni revisiones).
export function finalizarAnalisis(idAnalisis) {
  return pedir(`/analisis/${idAnalisis}/finalizar`, { method: "POST" });
}

export function listarRevisiones(idAnalisis) {
  return pedir(`/analisis/${idAnalisis}/revisiones`).then(d => d.revisiones ?? []);
}

export function guardarRevision(idAnalisis, revision) {
  return pedir(`/analisis/${idAnalisis}/revisiones`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(revision),
  });
}

export const urlImagen = idImagen => `${API_URL}/imagenes/${idImagen}`;

// SQLite guarda CURRENT_TIMESTAMP en UTC como "AAAA-MM-DD HH:MM:SS"; sin la "Z" se leería como hora local.
export const fechaServidor = f => (f ? `${f.replace(" ", "T")}Z` : null);

// Convierte la respuesta de GET /analisis/{id} al formato que usan las vistas.
export function desdeServidor({ analisis, imagenes, detecciones, evidencias = [] }) {
  const numero = new Map(imagenes.map((img, i) => [img.id, i + 1]));
  return {
    id: analisis.id,
    estado: analisis.estado,
    autor: analisis.usuario,
    esPrueba: !!analisis.es_prueba,
    finalizado: analisis.estado === "Finalizado",
    fecha: fechaServidor(analisis.fecha_creacion),
    imagenes: imagenes.map((img, i) => ({
      id: img.id,
      numero: i + 1,
      url: urlImagen(img.id),
      confianza: img.confianza_ocr,
      texto: img.texto_ocr ?? "",
    })),
    evidencias: evidencias.map(e => ({
      id: e.id,
      deteccionId: e.deteccion_id,
      imagenId: e.imagen_id,
      numeroImagen: numero.get(e.imagen_id) ?? null,
      codigo: e.codigo_regla,
      valor: e.valor_detectado,
      estado: e.estado,
    })),
    resultados: detecciones.map(d => ({
      codigo: d.codigo_regla,
      requisito: d.requisito,
      valor: d.valor,
      estado: d.estado,
      imagenId: d.imagen_id,
      numeroImagen: numero.get(d.imagen_id) ?? null,
    })),
  };
}
