import { FINALIZADO } from "../catalogos.js";
import { listarAnalisis, eliminarAnalisis, fechaServidor } from "../api.js";
import { esc, icono, fecha, badgeEstado, toast, confirmar } from "../ui.js";

// Historial leído de SQLite (GET /analisis/historial).

function estadoGeneral(a) {
  if (!a.total_detecciones) return "Revisión manual"; // sin reglas evaluadas
  return a.total_detectados === a.total_detecciones ? "Detectado" : "Revisión manual";
}

function filaAnalisis(a) {
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
      <button class="btn-icono" data-eliminar="${esc(a.id)}" aria-label="Eliminar análisis #${esc(a.id)}">
        ${icono("i-trash")}
      </button>
    </li>`;
}

export function vistaInicio(raiz) {
  // null = todavía consultando.
  let lista = null;
  let servidorCaido = false;

  function pintar() {
    const analisis = lista ?? [];
    const pendientes = analisis.reduce((n, a) => n + (a.total_detecciones - (a.total_detectados ?? 0)), 0);

    raiz.innerHTML = `
      <section class="hero hero--portada">
        <img class="hero__foto" src="img/portada.webp" alt="" width="900" height="1200" fetchpriority="high">
        <div class="hero__texto">
          <img class="hero__logo" src="img/logo-crt.png" alt="Consejo Regulador del Tequila" width="520" height="368">
          <p class="eyebrow">Sistema de apoyo · NOM-006-SCFI-2012</p>
          <h1>Análisis de <strong>etiquetado</strong> de tequila</h1>
          <p class="hero__lead">Fotografía la botella desde varias vistas y obtén un reporte de los requisitos
            de información comercial que se localizaron, los que faltan y los que requieren revisión.</p>
          <div class="acciones">
            <a class="btn btn--primario btn--grande" href="#/nuevo">${icono("i-plus")}Nuevo análisis</a>
            <a class="btn btn--secundario btn--grande" href="#/analisis/EJEMPLO">${icono("i-file")}Ver ejemplo</a>
          </div>
        </div>
      </section>

      <section class="herramientas" aria-label="Herramientas">
        <a class="herramienta" href="#/nuevo">
          <span class="herramienta__icono">${icono("i-camera")}</span>
          <strong>Nuevo análisis</strong><small>Fotografías de la botella desde varias vistas</small>
        </a>
        <a class="herramienta" href="#/analisis/EJEMPLO">
          <span class="herramienta__icono">${icono("i-file")}</span>
          <strong>Reporte de ejemplo</strong><small>Estado por requisito ET-xx, evidencia y revisión manual</small>
        </a>
        <a class="herramienta" href="#/configuracion">
          <span class="herramienta__icono">${icono("i-settings")}</span>
          <strong>Configuración</strong><small>Servidor, motor OCR y requisitos evaluados</small>
        </a>
      </section>

      <section class="metricas" aria-label="Resumen">
        <div class="metrica"><span class="metrica__valor">${analisis.length}</span><span class="metrica__etiqueta">Análisis realizados</span></div>
        <div class="metrica"><span class="metrica__valor">${analisis.reduce((n, a) => n + a.total_imagenes, 0)}</span><span class="metrica__etiqueta">Imágenes procesadas</span></div>
        <div class="metrica metrica--alerta"><span class="metrica__valor">${pendientes}</span><span class="metrica__etiqueta">Requisitos por revisar</span></div>
      </section>

      <section class="tarjeta">
        <header class="tarjeta__cabecera">
          <h2>Historial de análisis</h2>
          <button type="button" class="btn btn--texto" data-accion="actualizar">Actualizar</button>
        </header>
        ${servidorCaido ? `
          <div class="aviso aviso--alerta">${icono("i-alert")}<span>No se pudo consultar el servidor. Verifica que el backend esté encendido (uvicorn en el puerto 8000).</span></div>` : ""}
        ${analisis.length
          ? `<ul class="lista">${analisis.map(filaAnalisis).join("")}</ul>`
          : lista === null
            ? `<div class="vacio"><div class="spinner"></div><p>Cargando historial…</p></div>`
            : servidorCaido ? "" : `
              <div class="vacio">
                ${icono("i-bottle", "vacio__icono")}
                <h3>Aún no hay análisis</h3>
                <p>Crea el primero para ver aquí su estado y avance.</p>
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
