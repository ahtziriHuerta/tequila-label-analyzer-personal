import { FINALIZADO } from "../catalogos.js";
import { consultarHistorial, eliminarAnalisis, fechaServidor, esAdmin, sesion } from "../api.js";
import { esc, icono, fecha, badgeEstado, toast, confirmar } from "../ui.js";

// Historial leído de SQLite (GET /analisis/historial). Inicio muestra solo los pendientes.
// Pestañas: los análisis propios, el bloque de pruebas del equipo y, para el
// administrador, los de todos con filtro por usuario. Solo el administrador elimina.

const PESTANAS = [
  { id: "mios", texto: "Mis análisis" },
  { id: "pruebas", texto: "Pruebas" },
  { id: "todos", texto: "Todos", soloAdmin: true },
];

const MOTORES = { gemini: "Gemini", paddleocr: "Paddle", tesseract: "Tesseract" };

function estadoGeneral(a) {
  if (!a.total_detecciones) return "Revisión manual"; // sin reglas evaluadas
  return a.total_detectados === a.total_detecciones ? "Detectado" : "Revisión manual";
}

// `eliminable`: botón de eliminar (solo administrador, en el Historial).
// `autor`: mostrar quién lo hizo (pruebas y vista de todos).
export function filaAnalisis(a, { eliminable = false, autor = false } = {}) {
  const total = a.total_detecciones;
  const detectados = a.total_detectados ?? 0;
  const pct = total ? Math.round((detectados / total) * 100) : 0;
  const finalizado = a.estado === FINALIZADO;
  const motores = (a.motores_ocr ?? "").split(",").filter(Boolean).map(m => MOTORES[m] ?? m).join(" + ");
  const detalle = [
    autor ? esc(a.usuario) : null,
    `${a.total_imagenes} foto(s)`,
    `${detectados}/${total} detectados`,
    a.es_prueba && motores ? `<span class="mono">${esc(motores)}</span>` : null,
    fecha(fechaServidor(a.fecha_creacion)),
  ].filter(Boolean).join(" · ");
  return `
    <li class="lista-item">
      <a class="lista-item__link" href="#/analisis/${esc(a.id)}">
        <span class="lista-item__icono">${icono("i-bottle")}</span>
        <span class="lista-item__cuerpo">
          <strong>Análisis #${esc(a.id)}${a.marca ? ` · ${esc(a.marca)}${a.clase ? ` ${esc(a.clase)}` : ""}` : ""}${a.es_prueba ? ' <span class="chip chip--prueba">Prueba</span>' : ""}${finalizado ? ' <span class="chip">Finalizado</span>' : ""}</strong>
          <small>${detalle}</small>
        </span>
        <span class="lista-item__meta">
          ${badgeEstado(estadoGeneral(a))}
          <span class="mini-progreso" title="${detectados} de ${total} requisitos detectados">
            <span style="width:${pct}%"></span>
          </span>
        </span>
        ${icono("i-chevron", "lista-item__flecha")}
      </a>
      ${eliminable ? `
        <button class="btn-icono" data-eliminar="${esc(a.id)}" aria-label="Eliminar análisis #${esc(a.id)}">
          ${icono("i-trash")}
        </button>` : ""}
    </li>`;
}

// La pestaña elegida se recuerda mientras dure la visita.
let ultimaPestana = "mios";

export function vistaHistorial(raiz) {
  const admin = esAdmin();
  const pestanas = PESTANAS.filter(p => !p.soloAdmin || admin);
  const estado = {
    pestana: pestanas.some(p => p.id === ultimaPestana) ? ultimaPestana : "mios",
    usuarioId: "",
    lista: null, // null = todavía consultando
    usuarios: [],
    servidorCaido: false,
  };

  function vacio() {
    const textos = {
      mios: ["Aún no tienes análisis", "Los análisis que hagas aparecerán aquí."],
      pruebas: ["No hay análisis de prueba", "Los análisis guardados como prueba aparecerán aquí para todo el equipo."],
      todos: ["No hay análisis", "Ningún usuario ha guardado análisis con este filtro."],
    }[estado.pestana];
    return `
      <div class="vacio">
        ${icono("i-bottle", "vacio__icono")}
        <h3>${textos[0]}</h3>
        <p>${textos[1]}</p>
        ${estado.pestana === "mios" ? `<a class="btn btn--primario" href="#/nuevo">${icono("i-plus")}Nuevo análisis</a>` : ""}
      </div>`;
  }

  function pintar() {
    const analisis = estado.lista ?? [];
    const pendientes = analisis.reduce((n, a) => n + (a.total_detecciones - (a.total_detectados ?? 0)), 0);
    const autor = estado.pestana !== "mios";

    raiz.innerHTML = `
      <div class="encabezado-vista">
        <a href="#/" class="volver">${icono("i-arrow-left")}Inicio</a>
        <h1>Historial de análisis</h1>
        <p class="texto-suave">${esc(sesion.usuario?.nombre ?? "")}${admin ? " · Administrador" : ""}</p>
      </div>

      <div class="pestanas" role="tablist" aria-label="Qué análisis ver">
        ${pestanas.map(p => `
          <button type="button" role="tab" id="pestana-${p.id}" aria-controls="panel-historial"
                  aria-selected="${p.id === estado.pestana}" tabindex="${p.id === estado.pestana ? 0 : -1}"
                  data-pestana="${p.id}">${p.texto}</button>`).join("")}
      </div>

      <div id="panel-historial" role="tabpanel" aria-labelledby="pestana-${estado.pestana}" class="panel-historial">
        ${estado.pestana === "pruebas" ? `
          <div class="aviso aviso--prueba">${icono("i-info")}<span>Análisis de prueba del equipo, para comparar cómo evoluciona la lectura. No cuentan en las métricas de nadie.</span></div>` : ""}

        <section class="metricas" aria-label="Resumen">
          <div class="metrica"><span class="metrica__valor">${analisis.length}</span><span class="metrica__etiqueta">Análisis</span></div>
          <div class="metrica"><span class="metrica__valor">${analisis.reduce((n, a) => n + a.total_imagenes, 0)}</span><span class="metrica__etiqueta">Imágenes procesadas</span></div>
          <div class="metrica metrica--alerta"><span class="metrica__valor">${pendientes}</span><span class="metrica__etiqueta">Requisitos por revisar</span></div>
        </section>

        <section class="tarjeta">
          <header class="tarjeta__cabecera">
            <h2>${pestanas.find(p => p.id === estado.pestana).texto}</h2>
            <div class="tarjeta__herramientas">
              ${estado.pestana === "todos" ? `
                <label class="filtro-usuario">
                  <span class="sr-only">Filtrar por usuario</span>
                  <select id="filtro-usuario" data-filtro>
                    <option value="">Todos los usuarios</option>
                    ${estado.usuarios.map(u => `<option value="${esc(u.id)}" ${String(u.id) === estado.usuarioId ? "selected" : ""}>${esc(u.nombre)}</option>`).join("")}
                  </select>
                </label>` : ""}
              <button type="button" class="btn btn--texto" data-accion="actualizar">Actualizar</button>
            </div>
          </header>
          ${estado.servidorCaido ? `
            <div class="aviso aviso--alerta">${icono("i-alert")}<span>No se pudo consultar el servidor. Verifica tu conexión e inténtalo de nuevo.</span></div>` : ""}
          ${analisis.length
            ? `<ul class="lista">${analisis.map(a => filaAnalisis(a, { eliminable: admin, autor })).join("")}</ul>`
            : estado.lista === null
              ? `<div class="vacio"><div class="spinner"></div><p>Cargando historial…</p></div>`
              : estado.servidorCaido ? "" : vacio()}
        </section>
      </div>`;
  }

  async function cargar() {
    const pedida = `${estado.pestana}:${estado.usuarioId}`;
    try {
      const datos = await consultarHistorial({ ambito: estado.pestana, usuarioId: estado.usuarioId || null });
      // Si el usuario cambió de pestaña mientras cargaba, se descarta esta respuesta.
      if (pedida !== `${estado.pestana}:${estado.usuarioId}`) return;
      estado.lista = datos.analisis;
      if (estado.pestana === "todos" && !estado.usuarioId) estado.usuarios = datos.usuarios;
      estado.servidorCaido = false;
    } catch (err) {
      if (pedida !== `${estado.pestana}:${estado.usuarioId}`) return;
      estado.lista = [];
      estado.servidorCaido = !err.sesionCerrada;
    }
    if (raiz.isConnected) pintar();
  }

  function recargar() {
    estado.lista = null;
    pintar();
    return cargar();
  }

  function elegirPestana(id, enfocar = false) {
    if (id === estado.pestana) return;
    estado.pestana = ultimaPestana = id;
    estado.usuarioId = "";
    recargar();
    if (enfocar) raiz.querySelector(`#pestana-${id}`)?.focus();
  }

  raiz.addEventListener("click", async e => {
    const pestana = e.target.closest("[data-pestana]");
    if (pestana) return elegirPestana(pestana.dataset.pestana);

    if (e.target.closest('[data-accion="actualizar"]')) return recargar();

    const btn = e.target.closest("[data-eliminar]");
    if (!btn) return;
    const id = btn.dataset.eliminar;
    if (!confirmar(`¿Eliminar el análisis #${id} con sus fotos y revisiones? Esta acción no se puede deshacer.`)) return;

    btn.disabled = true;
    try {
      await eliminarAnalisis(id);
      estado.lista = estado.lista.filter(a => String(a.id) !== id);
      toast("Análisis eliminado", "ok");
      pintar();
    } catch (err) {
      console.error(err);
      btn.disabled = false;
      toast(err.message || "No se pudo eliminar en el servidor", "error");
    }
  });

  // Flechas izquierda/derecha entre pestañas (patrón de pestañas accesible).
  raiz.addEventListener("keydown", e => {
    if (!e.target.closest('[role="tab"]') || !["ArrowLeft", "ArrowRight"].includes(e.key)) return;
    const i = pestanas.findIndex(p => p.id === estado.pestana);
    const siguiente = pestanas[(i + (e.key === "ArrowRight" ? 1 : -1) + pestanas.length) % pestanas.length];
    elegirPestana(siguiente.id, true);
  });

  raiz.addEventListener("change", e => {
    if (!e.target.matches("[data-filtro]")) return;
    estado.usuarioId = e.target.value;
    recargar();
  });

  pintar();
  cargar();
}
