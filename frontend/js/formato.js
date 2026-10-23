// Datos del formato CRT "Requisitos de etiquetado para la NOM-006-SCFI-2012" (MO-RV/20).
// Los usan Nuevo análisis (antes de las fotos) y el reporte (para corregirlos después).
import { DESTINOS, CATEGORIAS, CLASES, PRESENTACIONES_ML, ADITIVOS } from "./catalogos.js";
import { esc } from "./ui.js";

const etiqueta = tipo => `<span class="tipo-dato tipo-dato--${tipo}">${{ sel: "Selección", man: "Manual", auto: "Automático" }[tipo]}</span>`;

const opciones = (lista, actual, vacio) => `
  <option value="">${vacio}</option>
  ${lista.map(v => `<option ${v === actual ? "selected" : ""}>${esc(v)}</option>`).join("")}`;

// Campos del encabezado. `prefijo` evita ids repetidos si hay dos formularios en pantalla.
export function camposDatos(datos = {}, { inspector = "", prefijo = "fd" } = {}) {
  const id = n => `${prefijo}-${n}`;
  return `
    <fieldset class="segmentado">
      <legend>Destino ${etiqueta("sel")}</legend>
      ${DESTINOS.map(d => `
        <label class="segmentado__opcion">
          <input type="radio" name="destino" value="${d.id}" ${(datos.destino ?? "nacional") === d.id ? "checked" : ""}>
          <span>${esc(d.nombre)}</span>
        </label>`).join("")}
    </fieldset>
    <div class="rejilla-campos">
      <div class="campo">
        <label for="${id("marca")}">Marca ${etiqueta("man")}</label>
        <input id="${id("marca")}" name="marca" maxlength="120" autocomplete="off" value="${esc(datos.marca ?? "")}" placeholder="Como aparece en la etiqueta">
      </div>
      <div class="campo">
        <label for="${id("empresa")}">Empresa ${etiqueta("man")}</label>
        <input id="${id("empresa")}" name="empresa" maxlength="200" autocomplete="organization" value="${esc(datos.empresa ?? "")}" placeholder="Productor o envasador">
      </div>
      <div class="campo">
        <label for="${id("categoria")}">Categoría ${etiqueta("sel")}</label>
        <select id="${id("categoria")}" name="categoria">${opciones(CATEGORIAS, datos.categoria, "Leer de la etiqueta")}</select>
      </div>
      <div class="campo">
        <label for="${id("clase")}">Clase ${etiqueta("sel")}</label>
        <select id="${id("clase")}" name="clase">${opciones(CLASES, datos.clase, "Leer de la etiqueta")}</select>
      </div>
      <div class="campo">
        <label for="${id("contenido")}">Presentación (mL) ${etiqueta("sel")}</label>
        <input id="${id("contenido")}" name="contenido_ml" type="number" inputmode="decimal" min="1" max="5000" step="any"
               list="${id("presentaciones")}" value="${esc(datos.contenido_ml ?? "")}" placeholder="750">
        <datalist id="${id("presentaciones")}">${PRESENTACIONES_ML.map(ml => `<option value="${ml}">`).join("")}</datalist>
      </div>
      <div class="campo">
        <label for="${id("alcohol")}">% Alc. Vol. declarado ${etiqueta("man")}</label>
        <input id="${id("alcohol")}" name="alcohol" type="number" inputmode="decimal" min="1" max="100" step="0.1"
               value="${esc(datos.alcohol ?? "")}" placeholder="35 a 55">
      </div>
      <div class="campo">
        <label for="${id("aditivos")}">¿Lleva saborizantes, colorantes u otros aditivos? ${etiqueta("sel")}</label>
        <select id="${id("aditivos")}" name="aditivos">
          ${ADITIVOS.map(a => `<option value="${a.id}" ${(datos.aditivos ?? "no_se") === a.id ? "selected" : ""}>${esc(a.nombre)}</option>`).join("")}
        </select>
        <span class="campo__ayuda">Con «No», saborizante y lista de ingredientes quedan como N/A.</span>
      </div>
    </div>
    ${inspector ? `
      <dl class="datos datos--compacto">
        <div><dt>Inspector ${etiqueta("auto")}</dt><dd>${esc(inspector)}</dd></div>
        <div><dt>Fecha ${etiqueta("auto")}</dt><dd>${new Date().toLocaleDateString("es-MX", { dateStyle: "long" })}</dd></div>
      </dl>` : ""}`;
}

// Lee los campos de un <form>; lo vacío se omite (el backend lo trata como "no declarado").
export function leerDatos(form) {
  const f = new FormData(form);
  const datos = {};
  for (const campo of ["destino", "marca", "empresa", "categoria", "clase", "aditivos"]) {
    const v = (f.get(campo) ?? "").toString().trim();
    if (v) datos[campo] = v;
  }
  for (const campo of ["contenido_ml", "alcohol"]) {
    const v = parseFloat((f.get(campo) ?? "").toString().replace(",", "."));
    if (Number.isFinite(v)) datos[campo] = v;
  }
  return datos;
}

// Resumen legible del encabezado (confirmación y reporte).
export function resumenDatos(datos = {}) {
  const destino = DESTINOS.find(d => d.id === datos.destino)?.nombre;
  const aditivos = ADITIVOS.find(a => a.id === datos.aditivos)?.nombre;
  const filas = [
    ["Destino", destino],
    ["Marca", datos.marca],
    ["Empresa", datos.empresa],
    ["Categoría", datos.categoria],
    ["Clase", datos.clase],
    ["Presentación", datos.contenido_ml != null ? `${datos.contenido_ml} mL` : null],
    ["% Alc. Vol.", datos.alcohol != null ? `${datos.alcohol}%` : null],
    ["Aditivos", aditivos],
  ];
  return `
    <dl class="datos datos--compacto">
      ${filas.map(([k, v]) => `<div><dt>${k}</dt><dd>${v ? esc(v) : '<span class="texto-suave">Sin declarar</span>'}</dd></div>`).join("")}
    </dl>`;
}
