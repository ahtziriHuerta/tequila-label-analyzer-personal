import { salud, conexion, sesion, yo, salir } from "./api.js";
import { establecerSesion, olvidarSesion, configurarMenu } from "./sesion.js";
import { icono, toast } from "./ui.js";
import { vistaAcceso, vistaCambioObligatorio } from "./vistas/acceso.js";
import { vistaInicio } from "./vistas/inicio.js";
import { vistaNuevo } from "./vistas/nuevo.js";
import { vistaResultado } from "./vistas/resultado.js";
import { vistaConfiguracion } from "./vistas/configuracion.js";
import { vistaHistorial } from "./vistas/historial.js";

// Navegación por hash: #/, #/nuevo, #/historial, #/configuracion, #/analisis/12 (o #/analisis/EJEMPLO).
const RUTAS = [
  { patron: /^#?\/?$/,                 nav: "inicio", render: vistaInicio },
  { patron: /^#\/nuevo$/,              nav: "nuevo",  render: vistaNuevo },
  { patron: /^#\/historial$/,          nav: "historial", render: vistaHistorial },
  { patron: /^#\/configuracion$/,      nav: "config", render: vistaConfiguracion },
  { patron: /^#\/analisis\/(\w+)$/,    nav: null,     render: vistaResultado },
];

const contenedor = document.getElementById("vista");
let limpiarVista = null;

// Pinta una pantalla en un nodo nuevo, para que los listeners de la anterior no se acumulen.
function montar(render, ...params) {
  limpiarVista?.();
  const raiz = document.createElement("div");
  raiz.className = "vista";
  contenedor.replaceChildren(raiz);
  limpiarVista = render(raiz, ...params) ?? null;
  window.scrollTo({ top: 0 });
  return raiz;
}

// ---------- Sesión ----------
// data-sesion en <body>: "verificando" | "no" (pantallas de acceso, sin barra) | "si".

function estadoSesion(valor) {
  document.body.dataset.sesion = valor;
}

// Al abrir la app: con sesión → la pantalla pedida (el hash no se toca, así un enlace
// a un análisis lleva a ese análisis después de entrar); sin sesión → iniciar sesión.
async function arrancar() {
  estadoSesion("verificando");
  let datos;
  try {
    datos = await yo();
  } catch {
    return mostrarSinConexion();
  }
  return datos ? continuarCon(datos) : mostrarAcceso();
}

// contrasena: la recién escrita al iniciar sesión (solo en memoria), para no pedir dos veces la temporal.
function continuarCon(datos, contrasena = null) {
  establecerSesion(datos);
  if (datos.usuario.debe_cambiar_contrasena) {
    estadoSesion("no");
    montar(vistaCambioObligatorio, {
      usuario: datos.usuario,
      contrasenaTemporal: contrasena,
      alGuardar: nuevos => { toast("Contraseña guardada", "ok"); continuarCon(nuevos); },
      alSalir: cerrarSesion,
    });
    return;
  }
  estadoSesion("si");
  enrutar();
}

function mostrarAcceso() {
  olvidarSesion();
  estadoSesion("no");
  montar(vistaAcceso, { alEntrar: continuarCon });
}

// Sin conexión no se manda al login (la sesión puede seguir vigente).
function mostrarSinConexion() {
  estadoSesion("no");
  const raiz = montar(r => {
    r.innerHTML = `
      <div class="tarjeta vacio sin-conexion">
        ${icono("i-alert", "vacio__icono")}
        <h1>Sin conexión con el servidor</h1>
        <p>Revisa tu conexión a internet o que el servidor esté encendido.</p>
        <button type="button" class="btn btn--primario" data-reintentar>Reintentar</button>
      </div>`;
  });
  raiz.querySelector("[data-reintentar]").addEventListener("click", arrancar);
}

async function cerrarSesion() {
  try { await salir(); } catch { /* aunque falle la red, la sesión local se cierra */ }
  // Volver a la portada para que la siguiente persona no caiga en una pantalla ajena.
  history.replaceState(null, "", "#/");
  mostrarAcceso();
  toast("Sesión cerrada", "ok");
}

configurarMenu({ cerrarSesion });

// ---------- Navegación ----------

function enrutar() {
  if (!sesion.usuario || sesion.usuario.debe_cambiar_contrasena) return;
  const hash = location.hash || "#/";
  const ruta = RUTAS.find(r => r.patron.test(hash)) ?? RUTAS[0];
  const params = hash.match(ruta.patron)?.slice(1) ?? [];

  montar(ruta.render, ...params);

  document.querySelectorAll(".topnav a").forEach(a =>
    a.toggleAttribute("aria-current", a.dataset.ruta === ruta.nav));
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
      ? "El backend responde, pero no hay ningún motor de lectura disponible (ver Configuración)"
      : `Backend conectado · lectura con ${conexion.ocrVersion ?? "OCR"}`;
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
arrancar();
