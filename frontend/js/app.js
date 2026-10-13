
const API = "http://127.0.0.1:8001";

// ==========================================
// ELEMENTOS DEL HTML
// ==========================================

const estadoApi = document.getElementById("estado-api");
const inputImagenes = document.getElementById("imagenes");
const listaImagenes = document.getElementById("lista-imagenes");

// Galería de evidencias
const galeriaEvidencias = document.getElementById("galeria-evidencias");
const listaEvidencias = document.getElementById("lista-evidencias");

const btnAnalizar = document.getElementById("btn-analizar");
const btnNuevo = document.getElementById("btn-nuevo");

const procesando = document.getElementById("procesando");
const resultados = document.getElementById("resultados");
const resumenReglas = document.getElementById("resumen-reglas");
const error = document.getElementById("error");

const identificadorAnalisis = document.getElementById(
  "identificador-analisis"
);

const listaHistorial = document.getElementById(
  "lista-historial"
);

const btnActualizarHistorial = document.getElementById(
  "btn-actualizar-historial"
);



// ==========================================
// VERIFICAR BACKEND
// ==========================================

async function verificarBackend() {
  try {
    const respuesta = await fetch(`${API}/salud`);

    if (!respuesta.ok) {
      throw new Error("Backend no disponible");
    }

    const datos = await respuesta.json();

    estadoApi.textContent = `● Backend: ${datos.estado}`;

  } catch (err) {
    estadoApi.textContent = "● Backend no disponible";
    console.error("Error al verificar backend:", err);
  }
}


// ==========================================
// SELECCIÓN DE FOTOGRAFÍAS
// ==========================================

inputImagenes.addEventListener("change", () => {
  listaImagenes.innerHTML = "";

  const archivos = Array.from(inputImagenes.files);

  btnAnalizar.disabled = archivos.length === 0;

  resultados.classList.add("oculto");
  error.classList.add("oculto");

  ocultarGaleria();

  archivos.forEach((archivo, indice) => {
    const elemento = document.createElement("div");
    elemento.className = "archivo-imagen";

    const nombre = document.createElement("span");
    nombre.textContent = `📷 ${indice + 1}. ${archivo.name}`;

    const tamano = document.createElement("small");
    tamano.textContent = formatearTamano(archivo.size);

    elemento.appendChild(nombre);
    elemento.appendChild(tamano);

    listaImagenes.appendChild(elemento);
  });
});


// ==========================================
// ANALIZAR BOTELLA
// ==========================================

btnAnalizar.addEventListener("click", async () => {
  const archivos = Array.from(inputImagenes.files);

  if (archivos.length === 0) {
    mostrarError("Selecciona al menos una fotografía.");
    return;
  }

  const formulario = new FormData();

  archivos.forEach(archivo => {
    formulario.append("archivos", archivo);
  });

  btnAnalizar.disabled = true;

  resultados.classList.add("oculto");
  error.classList.add("oculto");

  ocultarGaleria();

  procesando.classList.remove("oculto");

  try {
    const respuesta = await fetch(
      `${API}/analisis/imagenes`,
      {
        method: "POST",
        body: formulario
      }
    );

    if (!respuesta.ok) {
      throw new Error(
        await obtenerMensajeError(
          respuesta,
          "No fue posible realizar el análisis."
        )
      );
    }

    const datos = await respuesta.json();

    mostrarResultados(datos);

    // Recuperar las fotografías guardadas en SQLite
    // para mostrar la galería inmediatamente.
    if (datos.id_analisis != null) {
      await cargarGaleriaDeAnalisis(datos.id_analisis);
    }

    if (datos.guardado === true) {
      cargarHistorial();
    }

  } catch (err) {
    console.error("Error durante el análisis:", err);

    mostrarError(
      err.message || "Ocurrió un error durante el análisis."
    );

  } finally {
    procesando.classList.add("oculto");
    btnAnalizar.disabled = false;
  }
});



 // ==========================================
 // MOSTRAR RESULTADOS
 // ==========================================

function mostrarResultados(datos) {
  resumenReglas.innerHTML = "";

  // Reiniciar la revisión manual anterior
  analisisActivoId = null;
  seccionRevision.classList.add("oculto");

  // Ocultar fotografías del análisis anterior
  ocultarGaleria();

  const reglas = datos.reglas || {};

  identificadorAnalisis.textContent =
    datos.id_analisis != null
      ? `Análisis #${datos.id_analisis}`
      : "";

  Object.entries(reglas).forEach(([codigo, regla]) => {
    const elemento = document.createElement("div");
    elemento.className = "regla";

    const codigoElemento = document.createElement("div");
    codigoElemento.className = "codigo-regla";
    codigoElemento.textContent = codigo;

    const informacion = document.createElement("div");
    informacion.className = "info-regla";

    const requisito = document.createElement("strong");
    requisito.textContent =
      regla.requisito || "Requisito sin nombre";

    const valor = document.createElement("div");
    valor.className = "valor-regla";
    valor.textContent = regla.valor ?? "No determinado";

    informacion.appendChild(requisito);
    informacion.appendChild(valor);

    const estado = document.createElement("div");
    estado.className =
      `estado-regla ${obtenerClaseEstado(regla.estado)}`;

    estado.textContent = regla.estado || "Sin evaluar";

    elemento.appendChild(codigoElemento);
    elemento.appendChild(informacion);
    elemento.appendChild(estado);

    resumenReglas.appendChild(elemento);
  });

  // Mostrar resultados
  resultados.classList.remove("oculto");

  // Activar revisión manual
  if (datos.id_analisis != null) {
    prepararRevisionManual(
      datos.id_analisis,
      reglas
    );
  }

  resultados.scrollIntoView({
    behavior: "smooth",
    block: "start"
  });
}



// ==========================================
// CLASES SEGÚN ESTADO
// ==========================================

function obtenerClaseEstado(estado) {
  if (estado === "Detectado") {
    return "estado-detectado";
  }

  if (estado === "Revisión manual") {
    return "estado-revision";
  }

  if (estado === "Baja legibilidad") {
    return "estado-baja";
  }

  return "estado-revision";
}


// ==========================================
// MOSTRAR ERRORES
// ==========================================

function mostrarError(mensaje) {
  error.textContent = mensaje;
  error.classList.remove("oculto");
}


// ==========================================
// LEER ERRORES DEL BACKEND
// ==========================================

async function obtenerMensajeError(respuesta, mensajeGeneral) {
  try {
    const detalle = await respuesta.json();

    if (typeof detalle.detail === "string") {
      return detalle.detail;
    }
  } catch {
    // Conservar el mensaje general.
  }

  return mensajeGeneral;
}


// ==========================================
// NUEVO ANÁLISIS
// ==========================================

btnNuevo.addEventListener("click", () => {
  inputImagenes.value = "";

  listaImagenes.innerHTML = "";
  resumenReglas.innerHTML = "";

  identificadorAnalisis.textContent = "";

  ocultarGaleria();

  resultados.classList.add("oculto");
  procesando.classList.add("oculto");
  error.classList.add("oculto");

  btnAnalizar.disabled = true;

  window.scrollTo({
    top: 0,
    behavior: "smooth"
  });
});


// ==========================================
// HISTORIAL DE ANÁLISIS
// ==========================================

async function cargarHistorial() {
  listaHistorial.textContent =
    "Cargando análisis guardados...";

  btnActualizarHistorial.disabled = true;

  try {
    const respuesta = await fetch(
      `${API}/analisis/historial`
    );

    if (!respuesta.ok) {
      throw new Error(
        "No fue posible consultar el historial."
      );
    }

    const datos = await respuesta.json();

    listaHistorial.innerHTML = "";

    if (
      !Array.isArray(datos.analisis) ||
      datos.analisis.length === 0
    ) {
      listaHistorial.textContent =
        "Todavía no hay análisis guardados.";
      return;
    }

    datos.analisis.forEach(analisis => {
      const elemento = document.createElement("div");
      elemento.className = "historial-item";

      const informacion = document.createElement("div");
      informacion.className = "historial-info";

      const titulo = document.createElement("strong");
      titulo.textContent = `Análisis #${analisis.id}`;

      const detalle = document.createElement("div");
      detalle.className = "historial-detalle";

      detalle.textContent =
        `${analisis.total_imagenes} fotografías · ` +
        `${analisis.total_detecciones} detecciones`;

      const fecha = document.createElement("small");
      fecha.className = "historial-fecha";

      fecha.textContent =
        `Fecha: ${formatearFecha(analisis.fecha_creacion)}`;

      informacion.appendChild(titulo);
      informacion.appendChild(detalle);
      informacion.appendChild(fecha);

      const boton = document.createElement("button");
      boton.type = "button";
      boton.className = "historial-boton";
      boton.textContent = "Ver resultados";

      boton.addEventListener("click", () => {
        consultarAnalisis(analisis.id);
      });

      elemento.appendChild(informacion);
      elemento.appendChild(boton);

      listaHistorial.appendChild(elemento);
    });

  } catch (err) {
    console.error("Error al cargar historial:", err);

    listaHistorial.textContent =
      err.message || "Error al cargar el historial.";

  } finally {
    btnActualizarHistorial.disabled = false;
  }
}


// ==========================================
// CONSULTAR ANÁLISIS GUARDADO
// ==========================================

async function consultarAnalisis(id) {
  error.classList.add("oculto");
  resultados.classList.add("oculto");

  ocultarGaleria();

  procesando.classList.remove("oculto");

  try {
    const respuesta = await fetch(
      `${API}/analisis/${id}`
    );

    if (!respuesta.ok) {
      throw new Error(
        await obtenerMensajeError(
          respuesta,
          "No fue posible recuperar el análisis."
        )
      );
    }

    const datos = await respuesta.json();

    const reglas = {};

    (datos.detecciones || []).forEach(deteccion => {
      reglas[deteccion.codigo_regla] = {
        requisito: deteccion.requisito,
        valor: deteccion.valor,
        estado: deteccion.estado
      };
    });

    mostrarResultados({
      id_analisis: datos.analisis.id,
      reglas: reglas
    });

    // Mostrar fotografías asociadas al análisis.
   mostrarGaleria(
     datos.imagenes || [],
     datos.evidencias || []
   ); 

  } catch (err) {
    console.error("Error al consultar análisis:", err);

    mostrarError(
      err.message || "Error al consultar el análisis."
    );

  } finally {
    procesando.classList.add("oculto");
  }
}


// ==========================================
// RECUPERAR GALERÍA DESDE SQLITE
// ==========================================

async function cargarGaleriaDeAnalisis(id) {
  try {
    const respuesta = await fetch(
      `${API}/analisis/${id}`
    );

    if (!respuesta.ok) {
      throw new Error(
        "No se pudieron consultar las fotografías."
      );
    }

    const datos = await respuesta.json();

    mostrarGaleria(
      datos.imagenes || [],
      datos.evidencias || []
    );

  } catch (err) {
    console.error("Error al cargar galería:", err);

    // El análisis puede seguir mostrándose
    // aunque falle la carga de fotografías.
    mostrarAvisoGaleria(
      "No fue posible recuperar las fotografías."
    );
  }
}


// ==========================================
// OCULTAR GALERÍA
// ==========================================

function ocultarGaleria() {
  if (!galeriaEvidencias || !listaEvidencias) {
    return;
  }

  galeriaEvidencias.classList.add("oculto");
  listaEvidencias.innerHTML = "";
}


// ==========================================
// AVISO DE GALERÍA
// ==========================================

function mostrarAvisoGaleria(mensaje) {
  if (!galeriaEvidencias || !listaEvidencias) {
    console.error(
      "No se encontraron los elementos HTML de la galería."
    );
    return;
  }

  listaEvidencias.textContent = mensaje;
  galeriaEvidencias.classList.remove("oculto");
}


// ==========================================
// MOSTRAR GALERÍA DE FOTOGRAFÍAS
// ==========================================

function mostrarGaleria(imagenes, evidencias) {
  if (!galeriaEvidencias || !listaEvidencias) {
    console.error(
      "Falta galeria-evidencias o lista-evidencias en HTML."
    );
    return;
  }

console.log("MOSTRAR GALERÍA EJECUTADO");
console.log("Imágenes recibidas:", imagenes);
console.log("Elemento galería:", galeriaEvidencias);
console.log("Contenedor de imágenes:", listaEvidencias);

  listaEvidencias.innerHTML = "";

  if (!Array.isArray(imagenes) || imagenes.length === 0) {
    mostrarAvisoGaleria(
      "Este análisis no tiene fotografías registradas."
    );
    return;
  }

  imagenes.forEach((imagen, indice) => {
    const tarjeta = document.createElement("div");
    tarjeta.className = "evidencia-imagen";

    // Fotografía original
    const fotografia = document.createElement("img");

    fotografia.src =
      `${API}/imagenes/${imagen.id}`;

    fotografia.alt =
      `Fotografía ${indice + 1} del análisis`;

    fotografia.loading = "lazy";

    fotografia.addEventListener("error", () => {
      fotografia.style.display = "none";

      if (!tarjeta.querySelector(".error-fotografia")) {
        const aviso = document.createElement("p");
        aviso.className = "error-fotografia";

        aviso.textContent =
          "No se pudo cargar esta fotografía.";

        tarjeta.prepend(aviso);
      }

      console.error(
        `Error al cargar ${fotografia.src}`
      );
    });

    // Abrir imagen original en otra pestaña
    fotografia.style.cursor = "pointer";

    fotografia.addEventListener("click", () => {
      window.open(
        fotografia.src,
        "_blank",
        "noopener,noreferrer"
      );
    });

    const titulo = document.createElement("strong");
    titulo.textContent = `Fotografía ${indice + 1}`;

    // Confianza OCR
    const confianza = document.createElement("small");

    const valorConfianza = Number(imagen.confianza_ocr);

    confianza.textContent =
      imagen.confianza_ocr != null &&
      Number.isFinite(valorConfianza)
        ? `Confianza OCR: ${valorConfianza.toFixed(2)}`
        : "Confianza OCR: No disponible";

    // Detecciones vinculadas a la fotografía
    const reglasEncontradas = (
      Array.isArray(evidencias) ? evidencias : []
    ).filter(evidencia =>
      Number(evidencia.imagen_id) === Number(imagen.id) &&
      evidencia.estado === "Detectado"
    );

    const listaReglas = document.createElement("div");
    listaReglas.className = "evidencia-reglas";

    if (reglasEncontradas.length === 0) {
      const aviso = document.createElement("small");

      aviso.textContent =
        "Sin detecciones confirmadas asociadas.";

      listaReglas.appendChild(aviso);

    } else {
      reglasEncontradas.forEach(evidencia => {
        const elemento = document.createElement("span");

        elemento.textContent =
          `${evidencia.codigo_regla}: ` +
          `${evidencia.valor_detectado ?? "Detectado"}`;

        listaReglas.appendChild(elemento);
      });
    }

    tarjeta.appendChild(fotografia);
    tarjeta.appendChild(titulo);
    tarjeta.appendChild(confianza);
    tarjeta.appendChild(listaReglas);

    listaEvidencias.appendChild(tarjeta);
  });

  galeriaEvidencias.classList.remove("oculto");

  console.log(
    `Galería cargada: ${imagenes.length} fotografías.`
  );
}


// ==========================================
// ACTUALIZAR HISTORIAL
// ==========================================

btnActualizarHistorial.addEventListener(
  "click",
  cargarHistorial
);


// ==========================================
// FORMATEAR TAMAÑO DE ARCHIVOS
// ==========================================

function formatearTamano(bytes) {
  if (bytes < 1024) {
    return `${bytes} B`;
  }

  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }

  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}


// ==========================================
// FORMATEAR FECHA
// ==========================================

function formatearFecha(fechaTexto) {
  if (!fechaTexto) {
    return "Fecha no disponible";
  }

  const partes = fechaTexto.split(" ");

  if (partes.length !== 2) {
    return fechaTexto;
  }

  const [anio, mes, dia] = partes[0].split("-");

  return `${dia}/${mes}/${anio} · ${partes[1]}`;
}


// ==========================================
// INICIAR APLICACIÓN
// ==========================================

verificarBackend();
cargarHistorial();


// ==========================================
// ELEMENTOS DE REVISIÓN MANUAL
// ==========================================

const seccionRevision = document.getElementById(
  "revision-manual"
);

const formRevision = document.getElementById(
  "form-revision"
);

const selectRegla = document.getElementById(
  "revision-regla"
);

const selectResultado = document.getElementById(
  "revision-resultado"
);

const inputObservaciones = document.getElementById(
  "revision-observaciones"
);

const btnGuardarRevision = document.getElementById(
  "btn-guardar-revision"
);

const mensajeRevision = document.getElementById(
  "mensaje-revision"
);

const listaRevisiones = document.getElementById(
  "lista-revisiones"
);

let analisisActivoId = null;


// ==========================================
// PREPARAR REVISIÓN MANUAL
// ==========================================

function prepararRevisionManual(id, reglas) {
  analisisActivoId = id;

  selectRegla.innerHTML =
    '<option value="">Selecciona una regla</option>';

  Object.entries(reglas || {}).forEach(([codigo, regla]) => {
    const opcion = document.createElement("option");
    opcion.value = codigo;
    opcion.textContent = `${codigo} - ${regla.requisito}`;
    selectRegla.appendChild(opcion);
  });

  formRevision.reset();
  mensajeRevision.textContent = "";

  seccionRevision.classList.remove("oculto");

  cargarRevisiones(id);
}


// ==========================================
// CONSULTAR REVISIONES GUARDADAS
// ==========================================

async function cargarRevisiones(id) {
  listaRevisiones.textContent = "Cargando revisiones...";

  try {
    const respuesta = await fetch(
      `${API}/analisis/${id}/revisiones`
    );

    if (!respuesta.ok) {
      throw new Error("No se pudieron consultar las revisiones.");
    }

    const datos = await respuesta.json();

    listaRevisiones.innerHTML = "";

    if (!datos.revisiones.length) {
      listaRevisiones.textContent =
        "Todavía no hay revisiones manuales.";
      return;
    }

    datos.revisiones.forEach(revision => {
      const tarjeta = document.createElement("div");
      tarjeta.className = "revision-item";

      const titulo = document.createElement("strong");
      titulo.textContent =
        `${revision.codigo_regla} · ${revision.requisito}`;

      const resultado = document.createElement("p");
      resultado.textContent =
        `Resultado: ${revision.resultado}`;

      const observaciones = document.createElement("p");
      observaciones.textContent =
        revision.observaciones || "Sin observaciones.";

      const fecha = document.createElement("small");
      fecha.textContent =
        `Fecha: ${revision.fecha_revision}`;

      tarjeta.append(
        titulo,
        resultado,
        observaciones,
        fecha
      );

      listaRevisiones.appendChild(tarjeta);
    });

  } catch (error) {
    listaRevisiones.textContent = error.message;
  }
}


// ==========================================
// GUARDAR REVISIÓN MANUAL
// ==========================================

formRevision.addEventListener("submit", async (evento) => {
  evento.preventDefault();

  if (analisisActivoId === null) {
    return;
  }

  btnGuardarRevision.disabled = true;
  mensajeRevision.textContent = "Guardando revisión...";

  try {
    const respuesta = await fetch(
      `${API}/analisis/${analisisActivoId}/revisiones`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          codigo_regla: selectRegla.value,
          resultado: selectResultado.value,
          observaciones: inputObservaciones.value
        })
      }
    );

    if (!respuesta.ok) {
      throw new Error("No se pudo guardar la revisión.");
    }

    mensajeRevision.textContent =
      "Revisión guardada correctamente.";

    formRevision.reset();

    await cargarRevisiones(analisisActivoId);

  } catch (error) {
    mensajeRevision.textContent = error.message;

  } finally {
    btnGuardarRevision.disabled = false;
  }
});
