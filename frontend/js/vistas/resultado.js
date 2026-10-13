import { ESTADOS, RESULTADOS_REVISION } from "../catalogos.js";
import { analisisEjemplo } from "../ejemplo.js";
import {
  obtenerAnalisis, desdeServidor, listarRevisiones, guardarRevision,
  agregarEvidencia, finalizarAnalisis, fechaServidor,
} from "../api.js";
import { esc, icono, fecha, badgeEstado, toast, errorArchivo, procesando, progresoEstimado, botonesFoto, confirmar } from "../ui.js";

const CLASE_REVISION = { "Presente": "detectado", "Ausente": "no-local", "No determinado": "baja" };

function noEncontrado(raiz, texto) {
  raiz.innerHTML = `
    <div class="tarjeta vacio">
      ${icono("i-search-off", "vacio__icono")}
      <h2>Análisis no encontrado</h2>
      <p>${texto}</p>
      <a class="btn btn--primario" href="#/">Volver al inicio</a>
    </div>`;
}

async function cargar(id) {
  const [detalle, revisiones] = await Promise.all([obtenerAnalisis(id), listarRevisiones(id)]);
  return { analisis: desdeServidor(detalle), revisiones };
}

// id numérico = análisis en SQLite; "EJEMPLO" = demostración con datos ficticios.
export function vistaResultado(raiz, id) {
  if (id === "EJEMPLO") {
    const ejemplo = analisisEjemplo();
    return pintarReporte(raiz, ejemplo, ejemplo.revisiones);
  }
  if (!/^\d+$/.test(id)) return noEncontrado(raiz, "La dirección no corresponde a ningún análisis.");

  raiz.innerHTML = `<div class="tarjeta vacio"><div class="spinner"></div><p>Cargando análisis #${esc(id)}…</p></div>`;
  cargar(id)
    .then(({ analisis, revisiones }) => raiz.isConnected && pintarReporte(raiz, analisis, revisiones))
    .catch(err => {
      if (!raiz.isConnected) return;
      noEncontrado(raiz, err.status === 404
        ? `El análisis #${esc(id)} no existe; puede que se haya eliminado.`
        : "No se pudo conectar con el servidor. Verifica que el backend esté encendido e inténtalo de nuevo.");
    });
}

// ---------- Plantillas ----------

// ctx.ultima: última revisión manual por regla. ctx.antes: estados previos, para resaltar cambios (CU-06).
function tarjetaRegla(r, ctx) {
  const clase = ESTADOS[r.estado]?.clase ?? "manual";
  const previo = ctx.antes?.get(r.codigo);
  const cambio = previo && previo !== r.estado;
  const rev = ctx.ultima.get(r.codigo);
  return `
    <li class="regla regla--${clase}${cambio ? " regla--cambio" : ""}" data-estado="${esc(r.estado)}">
      <div class="regla__cabecera">
        <span class="codigo">${esc(r.codigo)}</span>
        <h3>${esc(r.requisito)}</h3>
        ${badgeEstado(r.estado)}
      </div>
      ${r.valor ? `
        <div class="regla__valor">
          <span class="texto-suave">Texto leído</span>
          <code>${esc(r.valor)}</code>
        </div>` : ""}
      ${r.estado !== "Detectado" ? `<p class="regla__obs texto-suave">${esc(ESTADOS[r.estado]?.ayuda ?? "")}</p>` : ""}
      ${cambio ? `<p class="regla__cambio">${icono("i-info")}Antes: ${esc(previo)}</p>` : ""}
      ${rev ? `
        <div class="regla__revision">
          ${icono("i-user-check")}
          <span><strong>Revisión manual:</strong>
            <span class="badge badge--${CLASE_REVISION[rev.resultado] ?? "manual"}">${esc(rev.resultado)}</span>
            ${rev.observaciones ? `<span class="texto-suave">${esc(rev.observaciones)}</span>` : ""}</span>
        </div>` : ""}
      <div class="regla__pie">
        ${r.numeroImagen ? `<span>Evidencia: fotografía ${r.numeroImagen}</span>` : ""}
        ${ctx.editable ? `
          <span class="regla__acciones no-imprimir">
            ${r.estado !== "Detectado" ? `
              <button type="button" class="btn btn--texto" data-evidencia title="Subir otra foto y volver a evaluar">
                ${icono("i-image-add")}Agregar foto</button>` : ""}
            <button type="button" class="btn btn--texto" data-revisar="${esc(r.codigo)}">${icono("i-edit")}Revisar</button>
          </span>` : ""}
      </div>
    </li>`;
}

function tarjetaImagen(img, resultados, evidencias = []) {
  const detectadas = evidencias.filter(
    e => e.numeroImagen === img.numero && e.estado === "Detectado"
  );
  const miniatura = img.url
    ? `<a href="${esc(img.url)}" target="_blank" rel="noopener" title="Abrir la fotografía original">
         <img src="${esc(img.url)}" alt="Fotografía ${img.numero}" loading="lazy"></a>`
    : `<span class="imagenes__ph">${icono("i-camera")}</span>`;
  return `
    <li>
      ${miniatura}
      <div>
        <strong>Fotografía ${img.numero}</strong>
        <small>${img.confianza != null ? `Confianza OCR: ${Math.round(img.confianza)}%` : "Confianza OCR: no disponible"}</small>
        ${img.confianza != null && img.confianza < 60 ? `<small class="imagenes__aviso">${icono("i-alert")}Lectura poco confiable</small>` : ""}
        <span class="imagenes__reglas">${detectadas.length
          ? detectadas.map(r => `
              <span class="codigo" title="${esc(r.codigo)}">
                ${esc(r.codigo)}: ${esc(r.valor ?? "Detectado")}
              </span>`).join("")
          : `<small class="texto-suave">Sin detecciones confirmadas</small>`}</span>
      </div>
    </li>`;
}

function seccionRevision(analisis, revisiones, ctx) {
  const historial = revisiones.length
    ? `<ul class="revisiones">${revisiones.map(rv => `
        <li>
          <div><span class="codigo">${esc(rv.codigo_regla)}</span> <strong>${esc(rv.requisito)}</strong>
            <span class="badge badge--${CLASE_REVISION[rv.resultado] ?? "manual"}">${esc(rv.resultado)}</span></div>
          ${rv.observaciones ? `<p>${esc(rv.observaciones)}</p>` : ""}
          <small class="texto-suave">${rv.usuario ? `${esc(rv.usuario)} · ` : ""}${rv.fecha_revision ? fecha(fechaServidor(rv.fecha_revision)) : "Ejemplo"}</small>
        </li>`).join("")}</ul>`
    : `<p class="texto-suave">Todavía no hay revisiones manuales.</p>`;

  const formulario = ctx.editable ? `
    <form id="form-revision" class="form-revision no-imprimir">
      <div class="rejilla-campos">
        <div class="campo">
          <label for="rv-regla">Requisito a revisar</label>
          <select id="rv-regla" name="codigo_regla" required>
            <option value="">Selecciona…</option>
            ${analisis.resultados.map(r => `<option value="${esc(r.codigo)}">${esc(r.codigo)} · ${esc(r.requisito)}</option>`).join("")}
          </select>
        </div>
        <div class="campo">
          <label for="rv-resultado">Resultado</label>
          <select id="rv-resultado" name="resultado" required>
            <option value="">Selecciona…</option>
            ${RESULTADOS_REVISION.map(r => `<option>${esc(r)}</option>`).join("")}
          </select>
        </div>
      </div>
      <div class="campo">
        <label for="rv-obs">Observaciones</label>
        <textarea id="rv-obs" name="observaciones" rows="3" maxlength="2000"
                  placeholder="Qué encontraste al revisar las fotografías…"></textarea>
      </div>
      <button type="submit" class="btn btn--primario">${icono("i-check")}Guardar revisión</button>
    </form>` : analisis.ejemplo
      ? `<div class="aviso aviso--info">${icono("i-info")}<span>En un análisis real aquí se registra la revisión visual de cada requisito.</span></div>`
      : "";

  return `
    <section class="tarjeta" id="revision">
      <header class="tarjeta__cabecera">
        <div><h2>Revisión manual</h2>
        <p class="texto-suave">Evaluación visual de un revisor. No modifica las detecciones del OCR.</p></div>
      </header>
      ${formulario}
      <h3 class="revisiones__titulo">Historial de revisiones (${revisiones.length})</h3>
      ${historial}
    </section>`;
}

// ---------- Acciones ----------

async function recargar(raiz, id, antes = null) {
  const { analisis, revisiones } = await cargar(id);
  if (raiz.isConnected) pintarReporte(raiz, analisis, revisiones, antes);
  return analisis;
}

// CU-06: sube una foto más al mismo análisis; el servidor solo lee esa foto y vuelve a aplicar las reglas.
async function agregarFoto(raiz, analisis, archivo) {
  const error = errorArchivo(archivo);
  if (error) return toast(error, "error");

  const antes = new Map(analisis.resultados.map(r => [r.codigo, r.estado]));
  const detener = progresoEstimado(raiz, "Subiendo y leyendo la foto nueva…", { segundos: 10 });
  try {
    await agregarEvidencia(analisis.id, [archivo]);
    detener();
    const nuevo = await recargar(raiz, analisis.id, antes);
    const cambios = nuevo.resultados.filter(r => antes.has(r.codigo) && antes.get(r.codigo) !== r.estado).length;
    toast(cambios ? `${cambios} requisito(s) cambiaron de estado.` : "Foto agregada; ningún requisito cambió de estado.", "ok");
  } catch (err) {
    detener();
    console.error(err);
    raiz.querySelector(".procesando")?.remove();
    toast(err.message || "No se pudo agregar la foto.", "error");
  }
}

// Cierra el análisis en el servidor y repinta el reporte en solo lectura.
async function finalizar(raiz, analisis) {
  const pendientes = analisis.resultados.filter(r => r.estado !== "Detectado").length;
  const aviso = pendientes ? `Aún hay ${pendientes} requisito(s) sin detectar. ` : "";
  if (!confirmar(`${aviso}¿Finalizar el análisis? Ya no podrás agregar fotos ni revisiones.`)) return;
  try {
    procesando(raiz, "Finalizando análisis…", 60);
    await finalizarAnalisis(analisis.id);
    await recargar(raiz, analisis.id);
    toast("Análisis finalizado", "ok");
  } catch (err) {
    console.error(err);
    raiz.querySelector(".procesando")?.remove();
    toast(err.message || "No se pudo finalizar.", "error");
  }
}

async function enviarRevision(raiz, analisis, form) {
  const boton = form.querySelector('[type="submit"]');
  boton.disabled = true;
  try {
    const datos = Object.fromEntries(new FormData(form));
    await guardarRevision(analisis.id, datos);
    await recargar(raiz, analisis.id);
    toast(`Revisión de ${datos.codigo_regla} guardada`, "ok");
  } catch (err) {
    console.error(err);
    boton.disabled = false;
    toast(err.message || "No se pudo guardar la revisión.", "error");
  }
}

// ---------- Reporte ----------

function pintarReporte(raiz, analisis, revisiones = [], antes = null) {
  const { resultados, imagenes } = analisis;
  const conteo = Object.keys(ESTADOS).map(e => [e, resultados.filter(r => r.estado === e).length]);
  const total = resultados.length;
  const detectados = conteo[0][1];
  const ctx = {
    editable: !analisis.ejemplo && !analisis.finalizado,
    // El servidor las devuelve de la más reciente a la más antigua.
    ultima: new Map([...revisiones].reverse().map(rv => [rv.codigo_regla, rv])),
    antes,
  };

  raiz.innerHTML = `
    <div class="encabezado-vista encabezado-vista--reporte">
      <a href="#/" class="volver no-imprimir">${icono("i-arrow-left")}Inicio</a>
      <div class="encabezado-vista__fila">
        <div>
          <p class="eyebrow">Reporte de análisis${analisis.ejemplo ? " · Ejemplo" : ""}</p>
          <h1>${analisis.ejemplo ? "Tequila de muestra" : `Análisis #${esc(analisis.id)}`}</h1>
          <p class="texto-suave">${fecha(analisis.fecha)} · ${imagenes.length} fotografía(s) · ${esc(analisis.estado)}</p>
        </div>
        <div class="acciones no-imprimir">
          ${ctx.editable ? `<button type="button" class="btn btn--secundario" data-accion="finalizar">${icono("i-check")}Finalizar análisis</button>` : ""}
          <button type="button" class="btn btn--secundario" data-accion="imprimir">${icono("i-printer")}Imprimir / PDF</button>
          <a class="btn btn--primario" href="#/nuevo">${icono("i-plus")}Nuevo análisis</a>
        </div>
      </div>
    </div>

    ${analisis.finalizado ? `<div class="aviso aviso--ok">${icono("i-check")}<span><strong>Análisis finalizado.</strong> Quedó en solo lectura: ya no admite fotos nuevas ni revisiones.</span></div>` : ""}
    ${analisis.ejemplo
      ? `<div class="aviso aviso--info">${icono("i-info")}<span>Este es un <strong>análisis de ejemplo</strong> con datos ficticios para mostrar el formato del reporte.</span></div>`
      : `<div class="aviso aviso--info">${icono("i-info")}<span>Resultados del <strong>OCR</strong> y el <strong>motor de reglas</strong>. Herramienta de apoyo: revisa manualmente los requisitos que no aparecen como Detectado.</span></div>`}

    <section class="tarjeta resumen">
      <div class="resumen__principal">
        <div class="anillo" style="--pct:${total ? (detectados / total) * 100 : 0}">
          <span><strong>${detectados}</strong>/${total}</span>
        </div>
        <div>
          <h2>Requisitos detectados</h2>
          <p class="texto-suave">${total - detectados} requisito(s) necesitan atención. Una lectura fallida no implica incumplimiento.</p>
        </div>
      </div>
      <div class="barra-estados" aria-hidden="true">
        ${conteo.filter(([, n]) => n).map(([e, n]) => `<span class="seg--${ESTADOS[e].clase}" style="flex:${n}" title="${esc(e)}: ${n}"></span>`).join("")}
      </div>
      <div class="filtros no-imprimir" role="group" aria-label="Filtrar por estado">
        <button type="button" class="filtro" data-filtro="" aria-pressed="true">Todos <span>${total}</span></button>
        ${conteo.map(([e, n]) => `
          <button type="button" class="filtro filtro--${ESTADOS[e].clase}" data-filtro="${esc(e)}" aria-pressed="false" ${n ? "" : "disabled"}>
            ${icono(ESTADOS[e].icono)}${esc(e)} <span>${n}</span>
          </button>`).join("")}
      </div>
    </section>

    <div class="rejilla-reporte">
      <div class="columna">
        <section>
          <h2 class="titulo-seccion">Requisitos (matriz ET)</h2>
          <ul class="reglas" id="reglas">${resultados.map(r => tarjetaRegla(r, ctx)).join("")}</ul>
        </section>
        ${seccionRevision(analisis, revisiones, ctx)}
      </div>

      <aside class="lateral">
        <section class="tarjeta">
          <header class="tarjeta__cabecera"><h2>Fotografías (${imagenes.length})</h2></header>
          <ul class="imagenes">${imagenes.map(img => tarjetaImagen(img, resultados, analisis.evidencias ?? [])).join("")}</ul>
          ${ctx.editable ? `
            <div class="evidencia no-imprimir">
              <h3>Agregar evidencia</h3>
              <p class="texto-suave texto-chico">Sube otra foto (p. ej. contraetiqueta o lote) para un requisito difícil.
                Solo se lee la foto nueva y se vuelven a evaluar las reglas.</p>
              <div class="evidencia__botones">${botonesFoto("data-ev", { textoPc: "Elegir foto" })}</div>
            </div>` : ""}
        </section>
      </aside>
    </div>

    <p class="leyenda-impresion">Herramienta de apoyo. Este reporte no sustituye una certificación oficial. Base normativa: NOM-006-SCFI-2012.</p>`;

  // Asignación (no addEventListener) para no acumular manejadores cuando el reporte se vuelve a pintar.
  raiz.onchange = e => {
    if (!e.target.matches("[data-ev]") || !e.target.files[0]) return;
    agregarFoto(raiz, analisis, e.target.files[0]);
    e.target.value = "";
  };

  raiz.onsubmit = e => {
    if (e.target.id !== "form-revision") return;
    e.preventDefault();
    enviarRevision(raiz, analisis, e.target);
  };

  raiz.onclick = e => {
    if (e.target.closest('[data-accion="imprimir"]')) return window.print();
    if (e.target.closest('[data-accion="finalizar"]')) return finalizar(raiz, analisis);

    // "Agregar foto" en una regla: abre la cámara (celular) o el selector de archivos (PC).
    if (e.target.closest("[data-evidencia]")) return raiz.querySelector("[data-ev]")?.click();

    // "Revisar": preselecciona la regla en el formulario de revisión manual.
    const revisar = e.target.closest("[data-revisar]");
    if (revisar) {
      raiz.querySelector("#rv-regla").value = revisar.dataset.revisar;
      raiz.querySelector("#revision").scrollIntoView({ behavior: "smooth", block: "start" });
      return raiz.querySelector("#rv-resultado").focus({ preventScroll: true });
    }

    const btn = e.target.closest("[data-filtro]");
    if (!btn) return;
    const filtro = btn.dataset.filtro || null;
    raiz.querySelectorAll("[data-filtro]").forEach(b => b.setAttribute("aria-pressed", b === btn));
    raiz.querySelectorAll("#reglas .regla").forEach(li => {
      li.hidden = filtro !== null && li.dataset.estado !== filtro;
    });
  };
}
