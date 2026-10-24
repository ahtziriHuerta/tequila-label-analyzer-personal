import { ESTADOS, IMAGEN } from "./catalogos.js";

// Escapa texto (del usuario o del OCR) antes de insertarlo en plantillas HTML.
export function esc(valor) {
  return String(valor ?? "").replace(/[&<>"']/g, c => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
  ));
}

export function icono(nombre, extra = "") {
  return `<svg class="icon ${extra}" aria-hidden="true"><use href="#${nombre}"/></svg>`;
}

export function badgeEstado(estado) {
  const e = ESTADOS[estado] ?? ESTADOS["Revisión manual"];
  return `<span class="badge badge--${e.clase}">${icono(e.icono)}${esc(estado)}</span>`;
}

export function fecha(iso) {
  if (!iso) return "Fecha no disponible";
  return new Date(iso).toLocaleString("es-MX", { dateStyle: "medium", timeStyle: "short" });
}

export function tamano(bytes) {
  return bytes < 1024 * 1024 ? `${Math.round(bytes / 1024)} KB` : `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export function toast(mensaje, tipo = "info") {
  const cont = document.getElementById("toasts");
  const el = document.createElement("div");
  el.className = `toast toast--${tipo}`;
  el.innerHTML = `${icono(tipo === "error" ? "i-alert" : tipo === "ok" ? "i-check" : "i-info")}<span>${esc(mensaje)}</span>`;
  cont.append(el);
  setTimeout(() => el.classList.add("toast--salida"), 3800);
  setTimeout(() => el.remove(), 4200);
}

// Celular o tableta (pantalla táctil): además de la galería se ofrece la cámara trasera directa.
export const conCamara = () => window.matchMedia("(pointer: coarse)").matches;

// Botones "Cámara" y "Galería" (en la PC, uno solo que abre el selector de archivos).
// `atributos` va en cada <input type="file">, p. ej. data-vista="frontal".
export function botonesFoto(atributos, { textoPc = "Subir foto" } = {}) {
  const input = extra => `<input type="file" accept="${IMAGEN.tiposPermitidos.join(",")}" ${atributos} ${extra} class="sr-only">`;
  if (!conCamara()) {
    return `<label class="btn btn--secundario">${icono("i-upload")}${textoPc}${input("")}</label>`;
  }
  return `
    <label class="btn btn--primario">${icono("i-camera")}Cámara${input('capture="environment"')}</label>
    <label class="btn btn--secundario">${icono("i-upload")}Galería${input("")}</label>`;
}

export function errorArchivo(archivo) {
  if (!IMAGEN.tiposPermitidos.includes(archivo.type)) {
    return `Formato no admitido (${archivo.type || "desconocido"}). Usa JPG, PNG o WEBP.`;
  }
  if (archivo.size > IMAGEN.maxBytes) {
    return `La imagen pesa ${tamano(archivo.size)}; el máximo es ${tamano(IMAGEN.maxBytes)}.`;
  }
  return null;
}

// Capa de progreso sobre la vista mientras se sube/lee/evalúa. Se quita al volver a pintar la vista.
export function procesando(raiz, texto, progreso) {
  let el = raiz.querySelector(".procesando");
  if (!el) {
    el = document.createElement("div");
    el.className = "procesando";
    el.setAttribute("role", "status");
    el.innerHTML = `<div class="procesando__caja"><div class="spinner"></div><p></p><div class="barra"><span></span></div></div>`;
    raiz.append(el);
  }
  el.querySelector("p").textContent = texto;
  el.querySelector(".barra span").style.width = `${progreso}%`;
}

// El OCR no informa su avance: la barra crece sola hacia `tope` mientras llega la respuesta.
export function progresoEstimado(raiz, texto, { desde = 10, tope = 90, segundos = 20 } = {}) {
  let actual = desde;
  procesando(raiz, texto, actual);
  const t = setInterval(() => {
    actual += (tope - actual) / (segundos * 2);
    raiz.querySelector(".procesando .barra span")?.style.setProperty("width", `${actual}%`);
  }, 500);
  return () => clearInterval(t);
}

export function confirmar(mensaje) {
  return window.confirm(mensaje);
}
