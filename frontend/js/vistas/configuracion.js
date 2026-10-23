import { REGLAS, SECCIONES, IMAGEN, MOTORES_OCR } from "../catalogos.js";
import { API_URL, conexion, salud, sesion } from "../api.js";
import { esc, icono, tamano, toast } from "../ui.js";
import { nombreRol, establecerSesion, navegacion } from "../sesion.js";
import { formularioCambio, activarCambio } from "./acceso.js";

// Pantalla informativa: la cuenta del usuario, cómo está configurada la instalación,
// prueba de conexión y cómo instalar la app en el celular.
export function vistaConfiguracion(raiz) {
  const u = sesion.usuario;

  // La cuenta se pinta una sola vez: refrescar el estado del servidor no borra lo que
  // el usuario esté escribiendo en el formulario de contraseña.
  raiz.innerHTML = `
    <div class="encabezado-vista">
      <a href="#/" class="volver">${icono("i-arrow-left")}Inicio</a>
      <h1>Configuración</h1>
      <p class="texto-suave">Tu cuenta, el estado del servidor y los requisitos evaluados.</p>
    </div>

    <section class="tarjeta" id="cuenta" tabindex="-1" aria-labelledby="cuenta-titulo">
      <header class="tarjeta__cabecera"><h2 id="cuenta-titulo">Tu cuenta</h2></header>
      <dl class="datos">
        <div><dt>Nombre</dt><dd>${esc(u.nombre)}</dd></div>
        <div><dt>Correo</dt><dd>${esc(u.correo)}</dd></div>
        <div><dt>Rol</dt><dd>${nombreRol(u.rol)}</dd></div>
      </dl>
      <h3 class="subtitulo">Cambiar contraseña</h3>
      <p class="texto-suave texto-chico">Al cambiarla se cierran tus sesiones en otros equipos.</p>
      ${formularioCambio({ correo: u.correo, obligatorio: false })}
    </section>

    <div data-estado></div>`;

  activarCambio(raiz, {
    alGuardar: datos => {
      establecerSesion(datos);
      toast("Contraseña cambiada. Se cerraron tus otras sesiones.", "ok");
    },
  });

  if (navegacion.irACuenta) {
    navegacion.irACuenta = false;
    const cuenta = raiz.querySelector("#cuenta");
    cuenta.scrollIntoView({ block: "start" });
    cuenta.focus({ preventScroll: true });
  }

  const zonaEstado = raiz.querySelector("[data-estado]");

  function pintar() {
    const ok = conexion.disponible;
    zonaEstado.innerHTML = `
      <section class="tarjeta">
        <header class="tarjeta__cabecera"><h2>Servidor</h2></header>
        <dl class="datos">
          <div><dt>Conexión</dt><dd>${ok ? "API conectada" : "Sin conexión"}</dd></div>
          <div><dt>Dirección de la API</dt><dd><code>${esc(API_URL)}</code></dd></div>
          <div><dt>Lectura de fotos</dt><dd>${!ok ? "—"
            : conexion.ocrDisponible ? esc(conexion.ocrVersion ?? "") : "Ningún motor disponible"}</dd></div>
          ${ok && conexion.ocrRespaldo.length ? `<div><dt>Respaldo</dt><dd>${conexion.ocrRespaldo.map(m => esc(MOTORES_OCR[m === "paddle" ? "paddleocr" : m] ?? m)).join(", ")}</dd></div>` : ""}
        </dl>
        ${ok && !conexion.ocrDisponible ? `
          <div class="aviso aviso--alerta" style="margin-top:14px">${icono("i-alert")}<span>El backend responde, pero el OCR no está listo:
            configura <code>GEMINI_API_KEY</code> en <code>backend/.env</code>, o instala PaddleOCR o Tesseract
            (con español <code>spa</code>) en la computadora que corre el servidor. Consulta el README.</span></div>` : ""}
        ${ok && conexion.ocr === "gemini" ? `
          <div class="aviso aviso--info" style="margin-top:14px">${icono("i-info")}<span>Las fotos se envían a Google (Gemini) para leerlas.
            No uses etiquetas confidenciales con una clave de nivel gratuito.</span></div>` : ""}
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
        <header class="tarjeta__cabecera"><h2>Requisitos evaluados (${REGLAS.length})</h2></header>
        <p class="texto-suave texto-chico">Formato del CRT «Requisitos de etiquetado para la NOM-006-SCFI-2012» (MO-RV/20).</p>
        ${Object.entries(SECCIONES).map(([id, titulo]) => `
          <h3 class="subtitulo">${esc(titulo)}</h3>
          <ul class="lista-simple">
            ${REGLAS.filter(r => r.seccion === id).map(r => `<li><span class="codigo">${esc(r.codigo)}</span> ${esc(r.requisito)}</li>`).join("")}
          </ul>`).join("")}
        <p class="nota">Las reglas están en <code>backend/app/services/reglas.py</code>.</p>
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
          : conexion.ocrDisponible ? "Servidor y lectura de fotos funcionando." : "El servidor responde, pero no hay motor de lectura.",
          conexion.disponible && conexion.ocrDisponible ? "ok" : "error");
    if (raiz.isConnected) pintar();
  });

  pintar();
  // El estado del OCR solo se conoce tras consultar /salud; se refresca al abrir la pantalla.
  salud().then(ok => { conexion.disponible = ok; if (raiz.isConnected) pintar(); });
}
