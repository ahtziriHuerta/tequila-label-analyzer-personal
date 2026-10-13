import { salud, conexion } from "./api.js";
import { vistaInicio } from "./vistas/inicio.js";
import { vistaNuevo } from "./vistas/nuevo.js";
import { vistaResultado } from "./vistas/resultado.js";
import { vistaConfiguracion } from "./vistas/configuracion.js";

// Navegación por hash: #/, #/nuevo, #/configuracion, #/analisis/12 (o #/analisis/EJEMPLO).
const RUTAS = [
  { patron: /^#?\/?$/,                 nav: "inicio", render: vistaInicio },
  { patron: /^#\/nuevo$/,              nav: "nuevo",  render: vistaNuevo },
  { patron: /^#\/configuracion$/,      nav: "config", render: vistaConfiguracion },
  { patron: /^#\/analisis\/(\w+)$/,    nav: null,     render: vistaResultado },
];

const contenedor = document.getElementById("vista");
let limpiarVista = null;

function enrutar() {
  const hash = location.hash || "#/";
  const ruta = RUTAS.find(r => r.patron.test(hash)) ?? RUTAS[0];
  const params = hash.match(ruta.patron)?.slice(1) ?? [];

  // Cada vista recibe un nodo nuevo para que sus listeners no se acumulen.
  limpiarVista?.();
  const raiz = document.createElement("div");
  raiz.className = "vista";
  contenedor.replaceChildren(raiz);
  limpiarVista = ruta.render(raiz, ...params) ?? null;

  document.querySelectorAll(".topnav a").forEach(a =>
    a.toggleAttribute("aria-current", a.dataset.ruta === ruta.nav));
  window.scrollTo({ top: 0 });
  contenedor.focus({ preventScroll: true });
}

async function verificarApi() {
  const pill = document.getElementById("estado-api");
  conexion.disponible = await salud();
  const sinOcr = conexion.disponible && !conexion.ocrDisponible;
  pill.dataset.estado = !conexion.disponible || sinOcr ? "off" : "ok";
  pill.querySelector(".api-pill__txt").textContent =
    !conexion.disponible ? "Sin servidor" : sinOcr ? "Sin OCR" : "API conectada";
  pill.title = !conexion.disponible
    ? "No se pudo contactar al backend (uvicorn en el puerto 8000)"
    : sinOcr
      ? "El backend responde, pero falta Tesseract con idioma español en el servidor (ver Configuración)"
      : `Backend y Tesseract ${conexion.ocrVersion ?? ""} disponibles`;
}

// ---------- PWA ----------
// El service worker solo funciona en https o localhost; en http por IP la app sigue funcionando sin él.
if ("serviceWorker" in navigator && window.isSecureContext) {
  navigator.serviceWorker.register("sw.js").catch(err => console.warn("Service worker no registrado", err));
}

// Chrome/Edge en Android y escritorio avisan cuando la app es instalable; iOS se instala desde
// "Compartir → Agregar a inicio" y no dispara este evento.
const botonInstalar = document.getElementById("instalar");
let avisoInstalacion = null;
window.addEventListener("beforeinstallprompt", e => {
  e.preventDefault();
  avisoInstalacion = e;
  botonInstalar.hidden = false;
});
botonInstalar.addEventListener("click", async () => {
  botonInstalar.hidden = true;
  avisoInstalacion?.prompt();
  avisoInstalacion = null;
});
window.addEventListener("appinstalled", () => { botonInstalar.hidden = true; });

window.addEventListener("hashchange", enrutar);
verificarApi();
setInterval(verificarApi, 30000);
enrutar();
