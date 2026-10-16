import { FINALIZADO } from "../catalogos.js";
import { listarAnalisis } from "../api.js";
import { icono } from "../ui.js";
import { filaAnalisis } from "./historial.js";

// Portada: una sola acción principal y, solo si los hay, los análisis sin finalizar
// para retomarlos. El historial completo, con el resumen y la opción de eliminar,
// está en #/historial.
const MAX_PENDIENTES = 3;

export function vistaInicio(raiz) {
  // null = todavía consultando.
  let lista = null;
  let servidorCaido = false;

  // Sin pendientes (o mientras carga) la sección no se muestra: la portada queda limpia.
  function pendientes() {
    if (servidorCaido) {
      return `<div class="aviso aviso--alerta">${icono("i-alert")}<span>No se pudo consultar el servidor. Verifica que el backend esté encendido.</span></div>`;
    }
    const abiertos = (lista ?? []).filter(a => a.estado !== FINALIZADO);
    if (!abiertos.length) return "";
    return `
      <section class="tarjeta">
        <header class="tarjeta__cabecera">
          <div>
            <h2>Pendientes (${abiertos.length})</h2>
            <p class="texto-suave">Análisis sin finalizar para retomar.</p>
          </div>
          <a class="btn btn--texto" href="#/historial">Ver todo${icono("i-chevron")}</a>
        </header>
        <ul class="lista">${abiertos.slice(0, MAX_PENDIENTES).map(a => filaAnalisis(a)).join("")}</ul>
      </section>`;
  }

  function pintar() {
    raiz.innerHTML = `
      <section class="hero hero--portada">
        <img class="hero__foto" src="img/portada.webp" alt="" width="900" height="1200" fetchpriority="high">
        <img class="hero__logo" src="img/logo-crt.png" alt="Consejo Regulador del Tequila" width="520" height="368">
        <div class="hero__texto">
          <p class="eyebrow">Sistema de apoyo · NOM-006-SCFI-2012</p>
          <h1>Análisis de <strong>etiquetado</strong> de tequila</h1>
          <p class="hero__lead">Fotografía la botella y revisa qué requisitos del etiquetado se detectan.</p>
          <div class="acciones">
            <a class="btn btn--primario btn--grande" href="#/nuevo">${icono("i-plus")}Nuevo análisis</a>
          </div>
          <a class="hero__ejemplo" href="#/analisis/EJEMPLO">${icono("i-file")}Ver un reporte de ejemplo</a>
        </div>
      </section>

      <div class="zona-agave">${pendientes()}</div>`;
  }

  async function cargar() {
    try {
      lista = await listarAnalisis();
      servidorCaido = false;
    } catch {
      lista = [];
      servidorCaido = true;
    }
    if (raiz.isConnected) pintar();
  }

  pintar();
  cargar();
}
