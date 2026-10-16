import { FINALIZADO } from "../catalogos.js";
import { listarAnalisis, eliminarAnalisis, fechaServidor } from "../api.js";
import { esc, icono, fecha, badgeEstado, toast, confirmar } from "../ui.js";

// Historial completo leído de SQLite (GET /analisis/historial). Inicio muestra solo los recientes.

function estadoGeneral(a) {
  if (!a.total_detecciones) return "Revisión manual"; // sin reglas evaluadas
  return a.total_detectados === a.total_detecciones ? "Detectado" : "Revisión manual";
}

// `eliminable`: en Inicio la lista es solo de consulta; se elimina desde el Historial.
export function filaAnalisis(a, { eliminable = false } = {}) {
  const total = a.total_detecciones;
  const detectados = a.total_detectados ?? 0;
  const pct = total ? Math.round((detectados / total) * 100) : 0;
  const finalizado = a.estado === FINALIZADO;
  return `
    <li class="lista-item">
      <a class="lista-item__link" href="#/analisis/${esc(a.id)}">
        <span class="lista-item__icono">${icono("i-bottle")}</span>
        <span class="lista-item__cuerpo">
          <strong>Análisis #${esc(a.id)}${finalizado ? ' <span class="chip">Finalizado</span>' : ""}</strong>
          <small>${a.total_imagenes} foto(s) · ${detectados}/${total} detectados · ${fecha(fechaServidor(a.fecha_creacion))}</small>
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

export function vistaHistorial(raiz) {
  // null = todavía consultando.
  let lista = null;
  let servidorCaido = false;

  function pintar() {
    const analisis = lista ?? [];
    const pendientes = analisis.reduce((n, a) => n + (a.total_detecciones - (a.total_detectados ?? 0)), 0);

    raiz.innerHTML = `
      <div class="encabezado-vista">
        <a href="#/" class="volver">${icono("i-arrow-left")}Inicio</a>
        <h1>Historial de análisis</h1>
      </div>

      <section class="metricas" aria-label="Resumen">
        <div class="metrica"><span class="metrica__valor">${analisis.length}</span><span class="metrica__etiqueta">Análisis realizados</span></div>
        <div class="metrica"><span class="metrica__valor">${analisis.reduce((n, a) => n + a.total_imagenes, 0)}</span><span class="metrica__etiqueta">Imágenes procesadas</span></div>
        <div class="metrica metrica--alerta"><span class="metrica__valor">${pendientes}</span><span class="metrica__etiqueta">Requisitos por revisar</span></div>
      </section>

      <section class="tarjeta">
        <header class="tarjeta__cabecera">
          <h2>Todos los análisis</h2>
          <button type="button" class="btn btn--texto" data-accion="actualizar">Actualizar</button>
        </header>
        ${servidorCaido ? `
          <div class="aviso aviso--alerta">${icono("i-alert")}<span>No se pudo consultar el servidor. Verifica que el backend esté encendido.</span></div>` : ""}
        ${analisis.length
          ? `<ul class="lista">${analisis.map(a => filaAnalisis(a, { eliminable: true })).join("")}</ul>`
          : lista === null
            ? `<div class="vacio"><div class="spinner"></div><p>Cargando historial…</p></div>`
            : servidorCaido ? "" : `
              <div class="vacio">
                ${icono("i-bottle", "vacio__icono")}
                <h3>Aún no hay análisis</h3>
                <p>Los análisis que hagas aparecerán aquí.</p>
                <a class="btn btn--primario" href="#/nuevo">${icono("i-plus")}Nuevo análisis</a>
              </div>`}
      </section>`;
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

  raiz.addEventListener("click", async e => {
    if (e.target.closest('[data-accion="actualizar"]')) {
      lista = null;
      pintar();
      return cargar();
    }

    const btn = e.target.closest("[data-eliminar]");
    if (!btn) return;
    const id = btn.dataset.eliminar;
    if (!confirmar(`¿Eliminar el análisis #${id} con sus fotos y revisiones? Esta acción no se puede deshacer.`)) return;

    btn.disabled = true;
    try {
      await eliminarAnalisis(id);
      lista = lista.filter(a => String(a.id) !== id);
      toast("Análisis eliminado", "ok");
      pintar();
    } catch (err) {
      console.error(err);
      btn.disabled = false;
      toast(err.message || "No se pudo eliminar en el servidor", "error");
    }
  });

  pintar();
  cargar();
}
