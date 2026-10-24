import { ESTADOS, CUMPLE, REGLAS, SECCIONES, ORDEN_REGLAS, VISTAS, DESTINOS, MOTORES_OCR } from "../catalogos.js";
import { analisisEjemplo } from "../ejemplo.js";
import {
  obtenerAnalisis, desdeServidor, listarRevisiones, guardarDictamen, actualizarDatos,
  agregarEvidencia, finalizarAnalisis, fechaServidor,
} from "../api.js";
import { esc, icono, fecha, badgeEstado, toast, errorArchivo, procesando, progresoEstimado, botonesFoto, confirmar } from "../ui.js";
import { camposDatos, leerDatos, resumenDatos } from "../formato.js";

const CLASE_REVISION = { "Presente": "detectado", "Ausente": "no-local", "No determinado": "baja" };
const nombreVista = id => VISTAS.find(v => v.id === id)?.nombre ?? null;
const seccionDe = codigo => REGLAS.find(r => r.codigo === codigo)?.seccion ?? "apartado11";

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
      if (err.sesionCerrada) return;
      noEncontrado(raiz, err.status === 404
        ? `El análisis #${esc(id)} no existe o no está disponible para tu cuenta.`
        : "No se pudo conectar con el servidor. Verifica que el backend esté encendido e inténtalo de nuevo.");
    });
}

// ---------- Plantillas ----------

const badgeCumple = c => c
  ? `<span class="badge badge--${CUMPLE[c]?.clase ?? "manual"}">Cumple: ${esc(CUMPLE[c]?.nombre ?? c)}</span>`
  : "";

// ctx.dictamen: último dictamen por regla. ctx.antes: estados previos, para resaltar cambios (CU-06).
function tarjetaRegla(r, ctx) {
  const clase = ESTADOS[r.estado]?.clase ?? "manual";
  const previo = ctx.antes?.get(r.codigo);
  const cambio = previo && previo !== r.estado;
  const dic = ctx.dictamen.get(r.codigo);
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
      ${r.observacion ? `<p class="regla__nota">${icono("i-info")}<span>${esc(r.observacion)}</span></p>`
        : r.estado !== "Detectado" ? `<p class="regla__obs texto-suave">${esc(ESTADOS[r.estado]?.ayuda ?? "")}</p>` : ""}
      ${cambio ? `<p class="regla__cambio">${icono("i-info")}Antes: ${esc(previo)}</p>` : ""}
      ${dic ? `
        <div class="regla__revision">
          ${icono("i-user-check")}
          <span><strong>Dictamen:</strong> ${badgeCumple(dic.cumple)}
            ${dic.informacion_correcta ? `<span class="texto-suave">Debe decir: ${esc(dic.informacion_correcta)}</span>` : ""}
            ${dic.observaciones ? `<span class="texto-suave">${esc(dic.observaciones)}</span>` : ""}</span>
        </div>` : ""}
      <div class="regla__pie">
        ${r.numeroImagen ? `<span>Evidencia: fotografía ${r.numeroImagen}</span>` : ""}
        ${ctx.editable ? `
          <span class="regla__acciones no-imprimir">
            ${!["Detectado", "No aplica"].includes(r.estado) ? `
              <button type="button" class="btn btn--texto" data-evidencia title="Subir otra foto y volver a evaluar">
                ${icono("i-image-add")}Agregar foto</button>` : ""}
            <button type="button" class="btn btn--texto" data-dictaminar="${esc(r.codigo)}">${icono("i-edit")}Dictaminar</button>
          </span>` : ""}
      </div>
    </li>`;
}

function tarjetaImagen(img, evidencias = []) {
  const detectadas = evidencias.filter(
    e => e.numeroImagen === img.numero && e.estado === "Detectado"
  );
  const miniatura = img.url
    ? `<a href="${esc(img.url)}" target="_blank" rel="noopener" title="Abrir la fotografía original">
         <img src="${esc(img.url)}" alt="Fotografía ${img.numero}" loading="lazy"></a>`
    : `<span class="imagenes__ph">${icono("i-camera")}</span>`;
  const vista = nombreVista(img.vista);
  return `
    <li>
      ${miniatura}
      <div>
        <strong>Fotografía ${img.numero}${vista ? ` · ${esc(vista)}` : ""}</strong>
        <small>${img.motor ? `${esc(MOTORES_OCR[img.motor] ?? img.motor)} · ` : ""}${img.confianza != null ? `Confianza OCR: ${Math.round(img.confianza)}%` : "Confianza: no disponible"}</small>
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

function seccionDatos(analisis, ctx) {
  const destino = DESTINOS.find(d => d.id === analisis.datos?.destino)?.nombre;
  return `
    <section class="tarjeta" id="datos-formato">
      <header class="tarjeta__cabecera">
        <div><h2>Formato CRT · Requisitos de etiquetado NOM-006</h2>
          <p class="texto-suave">MO-RV/20 · ${destino ? esc(destino) : "Destino sin declarar"} · Inspector: ${esc(analisis.autor ?? "—")}</p></div>
        ${ctx.editable ? `<button type="button" class="btn btn--texto no-imprimir" data-accion="editar-datos">${icono("i-edit")}Editar datos</button>` : ""}
      </header>
      <div data-datos-vista>${resumenDatos(analisis.datos)}</div>
      ${ctx.editable ? `
        <form id="form-datos-reporte" class="form-datos no-imprimir" hidden novalidate>
          ${camposDatos(analisis.datos ?? {}, { prefijo: "fr" })}
          <p class="texto-suave texto-chico">Al guardar se vuelven a evaluar los requisitos con el texto ya leído (no se repite la lectura de las fotos).</p>
          <div class="acciones">
            <button type="submit" class="btn btn--primario">${icono("i-check")}Guardar y reevaluar</button>
            <button type="button" class="btn btn--secundario" data-accion="cancelar-datos">Cancelar</button>
          </div>
        </form>` : ""}
    </section>`;
}

function seccionDictamen(analisis, ctx) {
  const historial = analisis.dictamenes.length
    ? `<ul class="revisiones">${analisis.dictamenes.map(d => `
        <li>
          <div><span class="codigo">${esc(d.codigo_regla)}</span> <strong>${esc(d.requisito)}</strong> ${badgeCumple(d.cumple)}</div>
          ${d.informacion_incorrecta ? `<p><span class="texto-suave">Incorrecta:</span> ${esc(d.informacion_incorrecta)}</p>` : ""}
          ${d.informacion_correcta ? `<p><span class="texto-suave">Correcta:</span> ${esc(d.informacion_correcta)}</p>` : ""}
          ${d.observaciones ? `<p>${esc(d.observaciones)}</p>` : ""}
          <small class="texto-suave">${d.usuario ? `${esc(d.usuario)} · ` : ""}${d.fecha ? fecha(fechaServidor(d.fecha)) : "Ejemplo"}</small>
        </li>`).join("")}</ul>`
    : `<p class="texto-suave">Todavía no hay dictámenes.</p>`;

  const formulario = ctx.editable ? `
    <form id="form-dictamen" class="form-revision no-imprimir">
      <div class="campo">
        <label for="dc-regla">Requisito</label>
        <select id="dc-regla" name="codigo_regla" required>
          <option value="">Selecciona…</option>
          ${analisis.resultados.map(r => `<option value="${esc(r.codigo)}">${esc(r.codigo)} · ${esc(r.requisito)}</option>`).join("")}
        </select>
      </div>
      <fieldset class="segmentado">
        <legend>Cumple especificación</legend>
        ${Object.entries(CUMPLE).map(([valor, c]) => `
          <label class="segmentado__opcion">
            <input type="radio" name="cumple" value="${valor}" required><span>${esc(c.nombre)}</span>
          </label>`).join("")}
      </fieldset>
      <div class="rejilla-campos">
        <div class="campo">
          <label for="dc-incorrecta">Información incorrecta</label>
          <textarea id="dc-incorrecta" name="informacion_incorrecta" rows="2" maxlength="1000" placeholder="Lo que dice la etiqueta"></textarea>
        </div>
        <div class="campo">
          <label for="dc-correcta">Información correcta</label>
          <textarea id="dc-correcta" name="informacion_correcta" rows="2" maxlength="1000" placeholder="Cómo debe decir (obligatorio si no cumple)"></textarea>
        </div>
      </div>
      <div class="campo">
        <label for="dc-obs">Observaciones</label>
        <textarea id="dc-obs" name="observaciones" rows="2" maxlength="2000"></textarea>
      </div>
      <button type="submit" class="btn btn--primario">${icono("i-check")}Guardar dictamen</button>
    </form>` : analisis.ejemplo
      ? `<div class="aviso aviso--info">${icono("i-info")}<span>En un análisis real aquí el inspector marca Sí / No / N/A en cada renglón del formato.</span></div>`
      : "";

  return `
    <section class="tarjeta" id="dictamen">
      <header class="tarjeta__cabecera">
        <div><h2>Dictamen del inspector</h2>
        <p class="texto-suave">Columna «Cumple especificación» del formato. No modifica las detecciones automáticas.
          Si no cumple, cita cómo debe decir (nota *** del formato, NOM-006 11.2.3).</p></div>
      </header>
      ${formulario}
      <h3 class="revisiones__titulo">Historial (${analisis.dictamenes.length})</h3>
      ${historial}
    </section>`;
}

// Revisiones manuales hechas antes de que existiera el dictamen del formato.
function seccionRevisionesAnteriores(revisiones) {
  if (!revisiones.length) return "";
  return `
    <section class="tarjeta">
      <header class="tarjeta__cabecera"><h2>Revisiones manuales anteriores (${revisiones.length})</h2></header>
      <ul class="revisiones">${revisiones.map(rv => `
        <li>
          <div><span class="codigo">${esc(rv.codigo_regla)}</span> <strong>${esc(rv.requisito)}</strong>
            <span class="badge badge--${CLASE_REVISION[rv.resultado] ?? "manual"}">${esc(rv.resultado)}</span></div>
          ${rv.observaciones ? `<p>${esc(rv.observaciones)}</p>` : ""}
          <small class="texto-suave">${rv.usuario ? `${esc(rv.usuario)} · ` : ""}${rv.fecha_revision ? fecha(fechaServidor(rv.fecha_revision)) : "Ejemplo"}</small>
        </li>`).join("")}</ul>
    </section>`;
}

// El formato MO-RV/20 lleno: una fila por requisito, como el papel del CRT.
function tablaFormato(analisis, ctx) {
  const marca = (dic, valor) => dic?.cumple === valor ? "X" : "";
  const filas = seccion => analisis.resultados
    .filter(r => seccionDe(r.codigo) === seccion)
    .map(r => {
      const dic = ctx.dictamen.get(r.codigo);
      return `
        <tr>
          <th scope="row">${esc(r.requisito)}</th>
          <td class="tabla-formato__auto">${badgeEstado(r.estado)}${r.valor ? `<br><small>${esc(r.valor)}</small>` : ""}</td>
          <td class="tabla-formato__marca">${marca(dic, "SI")}</td>
          <td class="tabla-formato__marca">${marca(dic, "NO")}</td>
          <td class="tabla-formato__marca">${marca(dic, "NA")}</td>
          <td>${esc(dic?.informacion_incorrecta ?? "")}</td>
          <td>${esc(dic?.informacion_correcta ?? "")}</td>
          <td>${esc(dic?.observaciones ?? "")}</td>
        </tr>`;
    }).join("");
  return `
    <section class="tarjeta" id="formato">
      <header class="tarjeta__cabecera">
        <div><h2>Formato MO-RV/20</h2>
        <p class="texto-suave">Así queda el formato del CRT con la detección automática y el dictamen.</p></div>
      </header>
      <div class="tabla-formato__marco">
        <table class="tabla-formato">
          <thead>
            <tr><th rowspan="2">Apartado 11 de la norma</th><th rowspan="2">Detección automática</th>
              <th colspan="3">Cumple especificación</th><th rowspan="2">Información incorrecta</th>
              <th rowspan="2">Información correcta</th><th rowspan="2">Observaciones</th></tr>
            <tr><th>Sí</th><th>No</th><th>N/A</th></tr>
          </thead>
          <tbody>${filas("apartado11")}</tbody>
          <tbody><tr><th colspan="8" class="tabla-formato__seccion">${SECCIONES.otras}</th></tr>${filas("otras")}</tbody>
        </table>
      </div>
    </section>`;
}

// ---------- Acciones ----------

async function recargar(raiz, id, antes = null) {
  const { analisis, revisiones } = await cargar(id);
  if (raiz.isConnected) pintarReporte(raiz, analisis, revisiones, antes);
  return analisis;
}

// CU-06: sube una foto más al mismo análisis; el servidor solo lee esa foto y vuelve a aplicar las reglas.
async function agregarFoto(raiz, analisis, archivo, vista) {
  const error = errorArchivo(archivo);
  if (error) return toast(error, "error");

  const antes = new Map(analisis.resultados.map(r => [r.codigo, r.estado]));
  const detener = progresoEstimado(raiz, "Subiendo y leyendo la foto nueva…", { segundos: 12 });
  try {
    await agregarEvidencia(analisis.id, [archivo], [vista || "otra"]);
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

async function guardarDatos(raiz, analisis, form) {
  const antes = new Map(analisis.resultados.map(r => [r.codigo, r.estado]));
  try {
    procesando(raiz, "Guardando datos y reevaluando…", 60);
    await actualizarDatos(analisis.id, leerDatos(form));
    const nuevo = await recargar(raiz, analisis.id, antes);
    const cambios = nuevo.resultados.filter(r => antes.get(r.codigo) !== r.estado).length;
    toast(cambios ? `Datos guardados: ${cambios} requisito(s) cambiaron de estado.` : "Datos guardados.", "ok");
  } catch (err) {
    console.error(err);
    raiz.querySelector(".procesando")?.remove();
    toast(err.message || "No se pudieron guardar los datos.", "error");
  }
}

// Cierra el análisis en el servidor y repinta el reporte en solo lectura.
async function finalizar(raiz, analisis, ctx) {
  const sinDictamen = analisis.resultados.filter(r => !ctx.dictamen.has(r.codigo)).length;
  const aviso = sinDictamen ? `Faltan ${sinDictamen} requisito(s) por dictaminar. ` : "";
  if (!confirmar(`${aviso}¿Finalizar el análisis? Ya no podrás agregar fotos, datos ni dictámenes.`)) return;
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

async function enviarDictamen(raiz, analisis, form) {
  const datos = Object.fromEntries(new FormData(form));
  if (datos.cumple === "NO" && !datos.informacion_correcta?.trim()) {
    form.querySelector("#dc-correcta").focus();
    return toast("Si no cumple, escribe la información correcta (cómo debe decir).", "error");
  }
  const boton = form.querySelector('[type="submit"]');
  boton.disabled = true;
  try {
    await guardarDictamen(analisis.id, datos);
    await recargar(raiz, analisis.id);
    toast(`Dictamen de ${datos.codigo_regla} guardado`, "ok");
  } catch (err) {
    console.error(err);
    boton.disabled = false;
    toast(err.message || "No se pudo guardar el dictamen.", "error");
  }
}

// ---------- Reporte ----------

function pintarReporte(raiz, analisis, revisiones = [], antes = null) {
  const resultados = [...analisis.resultados].sort(
    (a, b) => (ORDEN_REGLAS.get(a.codigo) ?? 99) - (ORDEN_REGLAS.get(b.codigo) ?? 99)
  );
  analisis = { ...analisis, resultados, dictamenes: analisis.dictamenes ?? [] };
  const { imagenes } = analisis;

  const conteo = Object.keys(ESTADOS).map(e => [e, resultados.filter(r => r.estado === e).length]);
  const aplicables = resultados.filter(r => r.estado !== "No aplica").length;
  const detectados = resultados.filter(r => r.estado === "Detectado").length;
  const ctx = {
    editable: !analisis.ejemplo && !analisis.finalizado,
    // El servidor los devuelve del más reciente al más antiguo: vale el primero de cada regla.
    dictamen: new Map([...analisis.dictamenes].reverse().map(d => [d.codigo_regla, d])),
    antes,
  };
  const dictaminados = resultados.filter(r => ctx.dictamen.has(r.codigo)).length;
  const grupos = Object.entries(SECCIONES).map(([id, titulo]) => [titulo, resultados.filter(r => seccionDe(r.codigo) === id)]);

  raiz.innerHTML = `
    <div class="encabezado-vista encabezado-vista--reporte">
      <a href="#/" class="volver no-imprimir">${icono("i-arrow-left")}Inicio</a>
      <div class="encabezado-vista__fila">
        <div>
          <p class="eyebrow">Reporte de análisis${analisis.ejemplo ? " · Ejemplo" : ""}${analisis.esPrueba ? " · Prueba" : ""}</p>
          <h1>${analisis.ejemplo ? "Tequila de muestra"
            : `Análisis #${esc(analisis.id)}${analisis.datos?.marca ? ` · ${esc(analisis.datos.marca)}` : ""}`}</h1>
          <p class="texto-suave">${analisis.autor ? `Analizado por ${esc(analisis.autor)} · ` : ""}${fecha(analisis.fecha)} · ${imagenes.length} fotografía(s) · ${esc(analisis.estado)}</p>
        </div>
        <div class="acciones no-imprimir">
          ${ctx.editable ? `<button type="button" class="btn btn--secundario" data-accion="finalizar">${icono("i-check")}Finalizar análisis</button>` : ""}
          <button type="button" class="btn btn--secundario" data-accion="imprimir">${icono("i-printer")}Imprimir / PDF</button>
          <a class="btn btn--primario" href="#/nuevo">${icono("i-plus")}Nuevo análisis</a>
        </div>
      </div>
    </div>

    ${analisis.finalizado ? `<div class="aviso aviso--ok">${icono("i-check")}<span><strong>Análisis finalizado.</strong> Quedó en solo lectura: ya no admite fotos, datos ni dictámenes.</span></div>` : ""}
    ${analisis.ejemplo
      ? `<div class="aviso aviso--info">${icono("i-info")}<span>Este es un <strong>análisis de ejemplo</strong> con datos ficticios para mostrar el formato del reporte.</span></div>`
      : `<div class="aviso aviso--info">${icono("i-info")}<span>Detección automática de apoyo. El dictamen (Sí / No / N/A) lo da el inspector en cada requisito.</span></div>`}

    ${seccionDatos(analisis, ctx)}

    <section class="tarjeta resumen">
      <div class="resumen__principal">
        <div class="anillo" style="--pct:${aplicables ? (detectados / aplicables) * 100 : 0}">
          <span><strong>${detectados}</strong>/${aplicables}</span>
        </div>
        <div>
          <h2>Requisitos detectados</h2>
          <p class="texto-suave">${aplicables - detectados} requisito(s) necesitan atención${resultados.length - aplicables ? ` · ${resultados.length - aplicables} no aplican` : ""}.
            Dictaminados: <strong>${dictaminados}/${resultados.length}</strong>. Una lectura fallida no implica incumplimiento.</p>
        </div>
      </div>
      <div class="barra-estados" aria-hidden="true">
        ${conteo.filter(([, n]) => n).map(([e, n]) => `<span class="seg--${ESTADOS[e].clase}" style="flex:${n}" title="${esc(e)}: ${n}"></span>`).join("")}
      </div>
      <div class="filtros no-imprimir" role="group" aria-label="Filtrar por estado">
        <button type="button" class="filtro" data-filtro="" aria-pressed="true">Todos <span>${resultados.length}</span></button>
        ${conteo.filter(([, n]) => n).map(([e, n]) => `
          <button type="button" class="filtro filtro--${ESTADOS[e].clase}" data-filtro="${esc(e)}" aria-pressed="false">
            ${icono(ESTADOS[e].icono)}${esc(e)} <span>${n}</span>
          </button>`).join("")}
      </div>
    </section>

    <div class="rejilla-reporte">
      <div class="columna">
        ${grupos.filter(([, lista]) => lista.length).map(([titulo, lista]) => `
          <section>
            <h2 class="titulo-seccion">${esc(titulo)}</h2>
            <ul class="reglas" data-reglas>${lista.map(r => tarjetaRegla(r, ctx)).join("")}</ul>
          </section>`).join("")}
        ${seccionDictamen(analisis, ctx)}
        ${seccionRevisionesAnteriores(revisiones)}
      </div>

      <aside class="lateral">
        <section class="tarjeta">
          <header class="tarjeta__cabecera"><h2>Fotografías (${imagenes.length})</h2></header>
          <ul class="imagenes">${imagenes.map(img => tarjetaImagen(img, analisis.evidencias ?? [])).join("")}</ul>
          ${ctx.editable ? `
            <div class="evidencia no-imprimir">
              <h3>Agregar evidencia</h3>
              <p class="texto-suave texto-chico">Sube otra foto (p. ej. contraetiqueta o lote) para un requisito difícil.
                Solo se lee la foto nueva y se vuelven a evaluar las reglas.</p>
              <div class="campo">
                <label for="ev-vista">Vista de la foto</label>
                <select id="ev-vista" data-ev-vista>
                  ${VISTAS.map(v => `<option value="${v.id}" ${v.id === "posterior" ? "selected" : ""}>${esc(v.nombre)}</option>`).join("")}
                </select>
              </div>
              <div class="evidencia__botones">${botonesFoto("data-ev", { textoPc: "Elegir foto" })}</div>
            </div>` : ""}
        </section>
      </aside>
    </div>

    ${tablaFormato(analisis, ctx)}

    <p class="leyenda-impresion">Herramienta de apoyo. Este reporte no sustituye una certificación oficial. Base normativa: NOM-006-SCFI-2012,
      NOM-030-SCFI-2006, NOM-142-SSA1/SCFI-2014 y NOM-106-SCFI-2017. Formato de referencia: CRT MO-RV/20.</p>`;

  // Asignación (no addEventListener) para no acumular manejadores cuando el reporte se vuelve a pintar.
  raiz.onchange = e => {
    if (!e.target.matches("[data-ev]") || !e.target.files[0]) return;
    agregarFoto(raiz, analisis, e.target.files[0], raiz.querySelector("[data-ev-vista]")?.value);
    e.target.value = "";
  };

  raiz.onsubmit = e => {
    if (e.target.id === "form-dictamen") {
      e.preventDefault();
      return enviarDictamen(raiz, analisis, e.target);
    }
    if (e.target.id === "form-datos-reporte") {
      e.preventDefault();
      return guardarDatos(raiz, analisis, e.target);
    }
  };

  const formDatos = raiz.querySelector("#form-datos-reporte");
  const vistaDatos = raiz.querySelector("[data-datos-vista]");

  raiz.onclick = e => {
    if (e.target.closest('[data-accion="imprimir"]')) return window.print();
    if (e.target.closest('[data-accion="finalizar"]')) return finalizar(raiz, analisis, ctx);

    if (e.target.closest('[data-accion="editar-datos"]') && formDatos) {
      formDatos.hidden = false;
      vistaDatos.hidden = true;
      return formDatos.querySelector("input, select")?.focus();
    }
    if (e.target.closest('[data-accion="cancelar-datos"]') && formDatos) {
      formDatos.hidden = true;
      vistaDatos.hidden = false;
      return;
    }

    // "Agregar foto" en una regla: abre la cámara (celular) o el selector de archivos (PC).
    if (e.target.closest("[data-evidencia]")) return raiz.querySelector("[data-ev]")?.click();

    // "Dictaminar": preselecciona la regla en el formulario del dictamen.
    const dictaminar = e.target.closest("[data-dictaminar]");
    if (dictaminar) {
      raiz.querySelector("#dc-regla").value = dictaminar.dataset.dictaminar;
      raiz.querySelector("#dictamen").scrollIntoView({ behavior: "smooth", block: "start" });
      return raiz.querySelector('#form-dictamen input[name="cumple"]').focus({ preventScroll: true });
    }

    const btn = e.target.closest("[data-filtro]");
    if (!btn) return;
    const filtro = btn.dataset.filtro || null;
    raiz.querySelectorAll("[data-filtro]").forEach(b => b.setAttribute("aria-pressed", b === btn));
    raiz.querySelectorAll("[data-reglas] .regla").forEach(li => {
      li.hidden = filtro !== null && li.dataset.estado !== filtro;
    });
  };
}
