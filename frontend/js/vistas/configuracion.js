import { REGLAS, TOTAL_REGLAS_ET, IMAGEN } from "../catalogos.js";
import { API_URL, conexion, salud } from "../api.js";
import { esc, icono, tamano, toast } from "../ui.js";

// Pantalla informativa: cómo está configurada la instalación, prueba de conexión
// y cómo instalar la app en el celular.
export function vistaConfiguracion(raiz) {
  function pintar() {
    const ok = conexion.disponible;
    raiz.innerHTML = `
      <div class="encabezado-vista">
        <a href="#/" class="volver">${icono("i-arrow-left")}Inicio</a>
        <h1>Configuración</h1>
        <p class="texto-suave">Estado del servidor, del motor OCR y de los requisitos evaluados.</p>
      </div>

      <section class="tarjeta">
        <header class="tarjeta__cabecera"><h2>Servidor</h2></header>
        <dl class="datos">
          <div><dt>Conexión</dt><dd>${ok ? "API conectada" : "Sin conexión"}</dd></div>
          <div><dt>Dirección de la API</dt><dd><code>${esc(API_URL)}</code></dd></div>
          <div><dt>Motor OCR</dt><dd>${!ok ? "—"
            : conexion.ocrDisponible ? `Tesseract ${esc(conexion.ocrVersion ?? "")}`
            : conexion.ocrVersion ? `Tesseract ${esc(conexion.ocrVersion)} sin idioma español` : "Tesseract no instalado"}</dd></div>
        </dl>
        ${ok && !conexion.ocrDisponible ? `
          <div class="aviso aviso--alerta" style="margin-top:14px">${icono("i-alert")}<span>El backend responde, pero el OCR no está listo:
            hace falta Tesseract con los idiomas español (<code>spa</code>) e inglés (<code>eng</code>) en la computadora
            que corre el servidor. Consulta el README y vuelve a probar.</span></div>` : ""}
        <div class="acciones" style="margin-top:14px">
          <button type="button" class="btn btn--secundario" data-accion="probar">${icono("i-check")}Probar conexión</button>
        </div>
      </section>

      <section class="tarjeta">
        <header class="tarjeta__cabecera"><h2>Fotografías</h2></header>
        <dl class="datos">
          <div><dt>Formatos</dt><dd>JPG, PNG, WebP</dd></div>
          <div><dt>Tamaño máximo</dt><dd>${tamano(IMAGEN.maxBytes)}</dd></div>
          <div><dt>Lado mínimo recomendado</dt><dd>${IMAGEN.ladoMinimoRecomendado} px</dd></div>
        </dl>
      </section>

      <section class="tarjeta">
        <header class="tarjeta__cabecera"><h2>Requisitos evaluados (${REGLAS.length} de ${TOTAL_REGLAS_ET})</h2></header>
        <ul class="lista-simple">
          ${REGLAS.map(r => `<li><span class="codigo">${esc(r.codigo)}</span> ${esc(r.requisito)}</li>`).join("")}
        </ul>
        <p class="nota">Las demás reglas de la matriz ET se agregan en <code>backend/app/services/reglas.py</code>.</p>
      </section>

      <section class="tarjeta">
        <header class="tarjeta__cabecera"><h2>Instalar en el celular</h2></header>
        <ul class="lista-simple">
          <li>${icono("i-info")}<span>Abre la app desde una dirección <strong>https</strong> (por ejemplo, un túnel de Cloudflare); en <code>http</code> por IP el navegador no permite instalarla.</span></li>
          <li>${icono("i-download")}<span><strong>Android (Chrome):</strong> botón «Instalar app» arriba, o menú ⋮ → «Instalar aplicación».</span></li>
          <li>${icono("i-download")}<span><strong>iPhone (Safari):</strong> Compartir → «Agregar a pantalla de inicio».</span></li>
        </ul>
      </section>`;
  }

  raiz.addEventListener("click", async e => {
    if (e.target.closest("[data-accion]")?.dataset.accion !== "probar") return;
    conexion.disponible = await salud();
    toast(!conexion.disponible ? "No se pudo contactar al servidor."
          : conexion.ocrDisponible ? "Servidor y OCR funcionando." : "El servidor responde, pero falta Tesseract.",
          conexion.disponible && conexion.ocrDisponible ? "ok" : "error");
    if (raiz.isConnected) pintar();
  });

  pintar();
  // El estado del OCR solo se conoce tras consultar /salud; se refresca al abrir la pantalla.
  salud().then(ok => { conexion.disponible = ok; if (raiz.isConnected) pintar(); });
}
