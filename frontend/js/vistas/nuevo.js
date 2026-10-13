import { VISTAS, REGLAS, IMAGEN } from "../catalogos.js";
import { conexion, analizar } from "../api.js";
import { esc, icono, tamano, toast, errorArchivo, progresoEstimado, conCamara, botonesFoto } from "../ui.js";

const PASOS = ["Fotografías", "Confirmar"];
const nombreVista = id => VISTAS.find(v => v.id === id)?.nombre ?? id;

function leerDimensiones(url) {
  return new Promise((ok, falla) => {
    const img = new Image();
    img.onload = () => ok({ ancho: img.naturalWidth, alto: img.naturalHeight });
    img.onerror = () => falla(new Error("No se pudo leer la imagen"));
    img.src = url;
  });
}

export function vistaNuevo(raiz) {
  const estado = {
    paso: 0,
    fotos: new Map(), // vista -> { archivo, url, ancho, alto }  (en el orden de VISTAS al enviar)
    enviando: false,
  };

  // ---------- Plantillas ----------
  function stepper() {
    return `
      <ol class="stepper" aria-label="Progreso">
        ${PASOS.map((p, i) => `
          <li class="stepper__paso ${i < estado.paso ? "is-hecho" : ""} ${i === estado.paso ? "is-actual" : ""}"
              ${i === estado.paso ? 'aria-current="step"' : ""}>
            <span class="stepper__num">${i < estado.paso ? icono("i-check") : i + 1}</span>
            <span class="stepper__txt">${p}</span>
          </li>`).join("")}
      </ol>`;
  }

  function tarjetaFoto(v) {
    const f = estado.fotos.get(v.id);
    const baja = f && Math.min(f.ancho, f.alto) < IMAGEN.ladoMinimoRecomendado;
    if (f) {
      return `
        <div class="foto foto--cargada ${baja ? "foto--aviso" : ""}">
          <img src="${f.url}" alt="Vista ${esc(v.nombre)}">
          <div class="foto__info">
            <strong>${esc(v.nombre)}</strong>
            <small>${f.ancho}×${f.alto}px · ${tamano(f.archivo.size)}</small>
            ${baja ? `<small class="foto__alerta">${icono("i-alert")}Resolución baja para OCR</small>` : ""}
          </div>
          <div class="foto__acciones">
            <label class="btn-icono" title="Reemplazar">
              ${icono("i-camera")}<span class="sr-only">Reemplazar foto ${esc(v.nombre)}</span>
              <input type="file" accept="${IMAGEN.tiposPermitidos.join(",")}" data-vista="${v.id}" hidden>
            </label>
            <button type="button" class="btn-icono" data-quitar="${v.id}" aria-label="Quitar foto ${esc(v.nombre)}">${icono("i-x")}</button>
          </div>
        </div>`;
    }
    // En el celular la tarjeta muestra dos botones (cámara trasera / galería) en lugar de ser un solo botón.
    if (conCamara()) {
      return `
        <div class="foto foto--vacia foto--movil">
          <span class="foto__icono">${icono("i-camera")}</span>
          <strong>${esc(v.nombre)} ${v.recomendada ? '<span class="chip">Recomendada</span>' : ""}</strong>
          <small>${esc(v.ayuda)}</small>
          <div class="foto__opciones">${botonesFoto(`data-vista="${v.id}"`)}</div>
        </div>`;
    }
    return `
      <label class="foto foto--vacia" data-soltar="${v.id}">
        <input type="file" accept="${IMAGEN.tiposPermitidos.join(",")}" data-vista="${v.id}" class="sr-only">
        <span class="foto__icono">${icono("i-camera")}</span>
        <strong>${esc(v.nombre)} ${v.recomendada ? '<span class="chip">Recomendada</span>' : ""}</strong>
        <small>${esc(v.ayuda)}</small>
        <span class="foto__cta">${icono("i-upload")}Tomar o subir foto</span>
      </label>`;
  }

  function pasoFotos() {
    const faltan = VISTAS.filter(v => v.recomendada && !estado.fotos.has(v.id));
    return `
      <section class="tarjeta tarjeta--botella">
        <img class="tarjeta__botella" src="img/portada.webp" alt="" width="900" height="1200" loading="lazy">
        <header class="tarjeta__cabecera">
          <div>
            <h2>Fotografías de la botella</h2>
            <p class="texto-suave">Una foto por vista. Buena luz, sin flash directo y con el texto enfocado.</p>
          </div>
        </header>
        ${faltan.length
          ? `<div class="aviso aviso--info">${icono("i-info")}<span>Recomendadas pendientes: <strong>${faltan.map(v => v.nombre).join(", ")}</strong>.</span></div>`
          : `<div class="aviso aviso--ok">${icono("i-check")}<span>Tienes todas las vistas recomendadas.</span></div>`}
        <div class="rejilla-fotos">
          ${VISTAS.map(tarjetaFoto).join("")}
        </div>
        <p class="texto-suave texto-chico"><span class="contador">${estado.fotos.size} / ${VISTAS.length} vistas</span> ·
          JPG, PNG o WEBP · máximo ${tamano(IMAGEN.maxBytes)} por imagen · se recomienda ≥ ${IMAGEN.ladoMinimoRecomendado}px por lado.</p>
      </section>`;
  }

  function pasoConfirmar() {
    const tomadas = new Set(estado.fotos.keys());
    const cobertura = REGLAS.map(r => ({ ...r, ok: r.vistas.some(v => tomadas.has(v)) }));
    const sinCobertura = cobertura.filter(r => !r.ok);
    return `
      <section class="tarjeta">
        <header class="tarjeta__cabecera"><h2>Imágenes (${estado.fotos.size})</h2>
          <button type="button" class="btn btn--texto" data-ir="0">Editar</button></header>
        <div class="miniaturas">
          ${ordenadas().map(([vista, f], i) => `
            <figure><img src="${f.url}" alt=""><figcaption>${i + 1}. ${esc(nombreVista(vista))}</figcaption></figure>`).join("")}
        </div>
      </section>
      <section class="tarjeta">
        <header class="tarjeta__cabecera">
          <div><h2>Cobertura de requisitos</h2>
          <p class="texto-suave">Vista previa según las vistas cargadas, antes del OCR.</p></div>
        </header>
        ${sinCobertura.length
          ? `<div class="aviso aviso--alerta">${icono("i-alert")}<span>${sinCobertura.length} requisito(s) no tienen una vista donde suelen aparecer. Puedes continuar y agregar fotos después desde el reporte.</span></div>`
          : `<div class="aviso aviso--ok">${icono("i-check")}<span>Todos los requisitos evaluados tienen al menos una vista asociada.</span></div>`}
        <ul class="cobertura">
          ${cobertura.map(r => `<li class="${r.ok ? "is-ok" : "is-falta"}">${icono(r.ok ? "i-check" : "i-image-add")}
              <span class="codigo">${r.codigo}</span>${esc(r.requisito)}</li>`).join("")}
        </ul>
        ${!conexion.disponible ? `<div class="aviso aviso--alerta">${icono("i-alert")}<span>El backend no responde: enciéndelo antes de iniciar el análisis.</span></div>`
          : !conexion.ocrDisponible ? `<div class="aviso aviso--alerta">${icono("i-alert")}<span>El servidor no tiene Tesseract con idioma español: el análisis fallará. Revisa la pantalla de Configuración.</span></div>` : ""}
      </section>`;
  }

  function botonera() {
    const ultimo = estado.paso === PASOS.length - 1;
    return `
      <div class="botonera">
        ${estado.paso > 0
          ? `<button type="button" class="btn btn--secundario" data-accion="atras">${icono("i-arrow-left")}Atrás</button>`
          : `<a class="btn btn--secundario" href="#/">Cancelar</a>`}
        <button type="button" class="btn btn--primario" data-accion="${ultimo ? "enviar" : "siguiente"}" ${estado.enviando ? "disabled" : ""}>
          ${ultimo ? `${icono("i-check")}Analizar botella` : `Continuar${icono("i-arrow-right")}`}
        </button>
      </div>`;
  }

  function pintar() {
    const contenido = [pasoFotos, pasoConfirmar][estado.paso]();
    raiz.innerHTML = `
      <div class="encabezado-vista">
        <a href="#/" class="volver">${icono("i-arrow-left")}Inicio</a>
        <h1>Nuevo análisis</h1>
      </div>
      ${stepper()}
      <div class="paso">${contenido}</div>
      ${botonera()}`;
  }

  // Las fotos se envían en el orden de VISTAS (frontal primero), así "Fotografía 1" es la frontal.
  const ordenadas = () => VISTAS.filter(v => estado.fotos.has(v.id)).map(v => [v.id, estado.fotos.get(v.id)]);

  // ---------- Fotos ----------
  async function cargarFoto(vista, archivo) {
    if (!archivo) return;
    const error = errorArchivo(archivo);
    if (error) return toast(error, "error");
    const url = URL.createObjectURL(archivo);
    try {
      const dim = await leerDimensiones(url);
      const anterior = estado.fotos.get(vista);
      if (anterior) URL.revokeObjectURL(anterior.url);
      estado.fotos.set(vista, { archivo, url, ...dim });
      pintar();
    } catch (err) {
      URL.revokeObjectURL(url);
      toast(err.message, "error");
    }
  }

  function quitarFoto(vista) {
    const f = estado.fotos.get(vista);
    if (f) URL.revokeObjectURL(f.url);
    estado.fotos.delete(vista);
    pintar();
  }

  // ---------- Envío ----------
  async function enviar() {
    estado.enviando = true;
    pintar();
    const fotos = ordenadas();
    const detener = progresoEstimado(raiz, `Subiendo ${fotos.length} foto(s) y leyendo el texto con OCR…`,
                                     { segundos: 8 * fotos.length });
    try {
      const resultado = await analizar(fotos.map(([, f]) => f.archivo));
      detener();
      toast(`Análisis #${resultado.id_analisis} guardado`, "ok");
      location.hash = `#/analisis/${resultado.id_analisis}`;
    } catch (err) {
      detener();
      console.error(err);
      estado.enviando = false;
      pintar();
      toast(err.message || "No se pudo realizar el análisis.", "error");
    }
  }

  // ---------- Eventos ----------
  raiz.addEventListener("change", e => {
    if (e.target.matches('input[type="file"]')) cargarFoto(e.target.dataset.vista, e.target.files[0]);
  });

  raiz.addEventListener("click", e => {
    const quitar = e.target.closest("[data-quitar]");
    if (quitar) return quitarFoto(quitar.dataset.quitar);

    const ir = e.target.closest("[data-ir]");
    if (ir) { estado.paso = +ir.dataset.ir; return pintar(); }

    const accion = e.target.closest("[data-accion]")?.dataset.accion;
    if (accion === "atras") { estado.paso--; pintar(); }
    if (accion === "siguiente") {
      if (estado.fotos.size === 0) return toast("Agrega al menos una fotografía para continuar.", "error");
      estado.paso++;
      pintar();
    }
    if (accion === "enviar" && !estado.enviando) enviar();
  });

  // Arrastrar y soltar sobre una tarjeta de vista vacía (PC)
  raiz.addEventListener("dragover", e => {
    const zona = e.target.closest("[data-soltar]");
    if (!zona) return;
    e.preventDefault();
    zona.classList.add("is-arrastre");
  });
  raiz.addEventListener("dragleave", e => e.target.closest("[data-soltar]")?.classList.remove("is-arrastre"));
  raiz.addEventListener("drop", e => {
    const zona = e.target.closest("[data-soltar]");
    if (!zona) return;
    e.preventDefault();
    cargarFoto(zona.dataset.soltar, e.dataTransfer.files[0]);
  });

  pintar();

  // Al salir, liberar las URLs de las previsualizaciones.
  return () => estado.fotos.forEach(f => URL.revokeObjectURL(f.url));
}
