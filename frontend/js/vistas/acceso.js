import { entrar, cambiarContrasena } from "../api.js";
import { esc, icono } from "../ui.js";

// Pantallas sin sesión: iniciar sesión y crear contraseña (primer acceso o restablecida).
// Comparten la identidad de la portada. No hay registro público: las cuentas las crea
// un administrador (backend/app/usuarios_cli.py).

export const LONGITUD_MINIMA = 10;

// Campo de contraseña con botón Mostrar/Ocultar. `autocomplete` permite que el iPhone
// (Llavero, Face ID) y los gestores de contraseñas llenen o guarden la contraseña.
export function campoContrasena({ id, etiqueta, autocomplete, ayuda = "" }) {
  return `
    <div class="campo">
      <label for="${id}">${etiqueta}</label>
      <div class="campo-contrasena">
        <input id="${id}" name="${id}" type="password" autocomplete="${autocomplete}" required
               autocapitalize="none" spellcheck="false" ${ayuda ? `aria-describedby="${id}-ayuda"` : ""}>
        <button type="button" class="campo-contrasena__ver" data-ver="${id}" aria-controls="${id}" aria-pressed="false">Mostrar</button>
      </div>
      ${ayuda}
    </div>`;
}

// Delegado: alterna la visibilidad de cualquier campo de contraseña dentro de `raiz`.
export function activarMostrar(raiz) {
  raiz.addEventListener("click", e => {
    const boton = e.target.closest("[data-ver]");
    if (!boton) return;
    const input = raiz.querySelector(`#${boton.dataset.ver}`);
    const visible = input.type === "password";
    input.type = visible ? "text" : "password";
    boton.textContent = visible ? "Ocultar" : "Mostrar";
    boton.setAttribute("aria-pressed", String(visible));
  });
}

function marco(contenido) {
  return `
    <div class="acceso">
      <div class="acceso__foto" aria-hidden="true">
        <img class="acceso__imagen" src="img/portada.webp" alt="" width="900" height="1200" fetchpriority="high">
        <img class="acceso__logo" src="img/logo-crt.png" alt="" width="520" height="368">
      </div>
      <div class="acceso__panel">
        ${contenido}
        <p class="acceso__pie">Herramienta de apoyo. Los resultados no sustituyen una certificación oficial.</p>
      </div>
    </div>`;
}

function mostrarError(form, mensaje) {
  const aviso = form.querySelector(".aviso--error");
  aviso.querySelector("span").textContent = mensaje;
  aviso.hidden = false;
}

// ---------- Iniciar sesión ----------

export function vistaAcceso(raiz, { alEntrar }) {
  raiz.innerHTML = marco(`
    <p class="eyebrow">NOM-006-SCFI-2012</p>
    <h1 class="titulo-marca">Análisis de <em>etiquetado</em> <small>de tequila</small></h1>
    <form class="acceso__form" novalidate>
      <div class="aviso aviso--error" role="alert" hidden>${icono("i-alert")}<span></span></div>
      <div class="campo">
        <label for="correo">Correo</label>
        <input id="correo" name="correo" type="email" inputmode="email" autocomplete="username" required
               autocapitalize="none" spellcheck="false">
      </div>
      ${campoContrasena({ id: "contrasena", etiqueta: "Contraseña", autocomplete: "current-password" })}
      <button type="submit" class="btn btn--primario btn--grande">Entrar</button>
    </form>
    <p class="acceso__nota">¿Olvidaste tu contraseña? Pídele a un administrador que la restablezca.</p>`);

  const form = raiz.querySelector("form");
  const correo = form.correo;
  const contrasena = form.contrasena;
  const boton = form.querySelector('[type="submit"]');
  activarMostrar(raiz);

  form.addEventListener("submit", async e => {
    e.preventDefault();
    if (!correo.value.trim() || !contrasena.value) {
      mostrarError(form, "Escribe tu correo y tu contraseña.");
      (correo.value.trim() ? contrasena : correo).focus();
      return;
    }
    boton.disabled = true;
    boton.textContent = "Entrando…";
    try {
      // La contraseña se pasa en memoria por si es temporal: así no hay que escribirla dos veces.
      alEntrar(await entrar(correo.value.trim(), contrasena.value), contrasena.value);
    } catch (err) {
      boton.disabled = false;
      boton.textContent = "Entrar";
      mostrarError(form, err.sinConexion
        ? "No se pudo conectar con el servidor. Revisa tu conexión e inténtalo de nuevo."
        : err.message);
      contrasena.setAttribute("aria-invalid", "true");
      contrasena.select();
      contrasena.focus();
    }
  });
  contrasena.addEventListener("input", () => contrasena.removeAttribute("aria-invalid"));

  correo.focus();
}

// ---------- Cambio de contraseña ----------

// Formulario reutilizable: pantalla obligatoria (contraseña temporal) y Configuración.
// pedirActual = false cuando ya se conoce (se acaba de escribir al iniciar sesión).
export function formularioCambio({ correo, obligatorio, pedirActual = true }) {
  return `
    <form class="form-contrasena" novalidate>
      <div class="aviso aviso--error" role="alert" hidden>${icono("i-alert")}<span></span></div>
      <!-- Para que el gestor de contraseñas guarde la nueva en la cuenta correcta. -->
      <input type="text" name="usuario" autocomplete="username" value="${esc(correo)}" hidden>
      ${pedirActual ? campoContrasena({ id: "actual", etiqueta: obligatorio ? "Contraseña temporal" : "Contraseña actual", autocomplete: "current-password" }) : ""}
      ${campoContrasena({
        id: "nueva", etiqueta: "Contraseña nueva", autocomplete: "new-password",
        ayuda: `
          <ul class="requisitos" id="nueva-ayuda">
            <li data-req="largo">Al menos ${LONGITUD_MINIMA} caracteres</li>
            <li data-req="distinta">Distinta de la ${obligatorio ? "temporal" : "actual"}</li>
            <li data-req="coincide">Coincide con la confirmación</li>
          </ul>` })}
      ${campoContrasena({ id: "confirmar", etiqueta: "Confirmar contraseña nueva", autocomplete: "new-password" })}
      <button type="submit" class="btn btn--primario ${obligatorio ? "btn--grande" : ""}">${obligatorio ? "Guardar y continuar" : "Cambiar contraseña"}</button>
    </form>`;
}

// Conecta el formulario: requisitos en vivo y envío. `alGuardar(datos)` recibe la respuesta del servidor.
export function activarCambio(raiz, { alGuardar, actualConocida = null }) {
  const form = raiz.querySelector(".form-contrasena");
  const { actual, nueva, confirmar } = form;
  const valorActual = () => actual?.value ?? actualConocida ?? "";
  const boton = form.querySelector('[type="submit"]');
  const textoBoton = boton.textContent;
  activarMostrar(form);

  const cumple = () => ({
    largo: nueva.value.length >= LONGITUD_MINIMA,
    distinta: !!nueva.value && nueva.value !== valorActual(),
    coincide: !!nueva.value && nueva.value === confirmar.value,
  });

  function actualizar() {
    Object.entries(cumple()).forEach(([req, ok]) =>
      form.querySelector(`[data-req="${req}"]`).classList.toggle("is-ok", ok));
  }
  form.addEventListener("input", actualizar);

  form.addEventListener("submit", async e => {
    e.preventDefault();
    const estado = cumple();
    const faltante = !valorActual() ? [actual, "Escribe tu contraseña actual."]
      : !estado.largo ? [nueva, `La contraseña nueva debe tener al menos ${LONGITUD_MINIMA} caracteres.`]
      : !estado.distinta ? [nueva, "La contraseña nueva debe ser distinta de la actual."]
      : !estado.coincide ? [confirmar, "La confirmación no coincide con la contraseña nueva."]
      : null;
    if (faltante) {
      mostrarError(form, faltante[1]);
      faltante[0].focus();
      return;
    }
    boton.disabled = true;
    boton.textContent = "Guardando…";
    try {
      const datos = await cambiarContrasena(valorActual(), nueva.value);
      form.reset();
      actualizar();
      form.querySelector(".aviso--error").hidden = true;
      alGuardar(datos);
    } catch (err) {
      mostrarError(form, err.sinConexion ? "No se pudo conectar con el servidor." : err.message);
      ((err.status === 400 && /actual/i.test(err.message) && actual) || nueva).focus();
    } finally {
      boton.disabled = false;
      boton.textContent = textoBoton;
    }
  });
}

export function vistaCambioObligatorio(raiz, { usuario, contrasenaTemporal = null, alGuardar, alSalir }) {
  raiz.innerHTML = marco(`
    <p class="eyebrow">Primer acceso</p>
    <h1 class="titulo-marca">Crea tu <em>contraseña</em></h1>
    <p class="acceso__texto">Hola, ${esc(usuario.nombre)}. Entraste con una contraseña temporal que te dio el administrador; elige una nueva para continuar.</p>
    ${formularioCambio({ correo: usuario.correo, obligatorio: true, pedirActual: !contrasenaTemporal })}
    <button type="button" class="btn btn--texto acceso__salir" data-accion="salir">Usar otra cuenta</button>`);

  activarCambio(raiz, { alGuardar, actualConocida: contrasenaTemporal });
  raiz.querySelector('[data-accion="salir"]').addEventListener("click", alSalir);
  raiz.querySelector(contrasenaTemporal ? "#nueva" : "#actual").focus();
}
