import { sesion, entrar, alVencerSesion } from "./api.js";
import { esc, icono } from "./ui.js";
import { campoContrasena, activarMostrar } from "./vistas/acceso.js";

// Estado de la sesión en la interfaz: menú de usuario y ventana de sesión vencida.

const ROLES = { administrador: "Administrador", analista: "Analista" };
export const nombreRol = rol => ROLES[rol] ?? rol;

export function establecerSesion(datos) {
  sesion.usuario = datos.usuario;
  sesion.pruebasActivas = !!datos.pruebas_activas;
  pintarMenu();
}

export function olvidarSesion() {
  sesion.usuario = null;
  sesion.pruebasActivas = false;
  pintarMenu();
}

// ---------- Menú de usuario (barra superior) ----------

const menu = document.getElementById("menu-usuario");
let alCerrarSesion = () => {};
export const navegacion = { irACuenta: false };

export function configurarMenu({ cerrarSesion }) {
  alCerrarSesion = cerrarSesion;
}

function pintarMenu() {
  const u = sesion.usuario;
  menu.hidden = !u;
  if (!u) return (menu.innerHTML = "");
  menu.innerHTML = `
    <button type="button" class="menu-usuario__boton" aria-expanded="false" aria-controls="menu-usuario-lista"
            aria-label="Cuenta de ${esc(u.nombre)}">
      <span class="avatar" aria-hidden="true">${esc(u.nombre.trim()[0] ?? "?")}</span>
      <span class="menu-usuario__nombre">${esc(u.nombre)}</span>
      ${u.rol === "administrador" ? `<span class="menu-usuario__rol">Admin</span>` : ""}
    </button>
    <div class="menu-usuario__lista" id="menu-usuario-lista" hidden>
      <div class="menu-usuario__yo">
        <strong>${esc(u.nombre)}</strong>
        <small>${esc(u.correo)} · ${nombreRol(u.rol)}</small>
      </div>
      <a href="#/configuracion" data-cuenta>${icono("i-lock")}Cambiar contraseña</a>
      <button type="button" class="menu-usuario__salir" data-salir>${icono("i-logout")}Cerrar sesión</button>
    </div>`;
}

function abrirMenu(abrir) {
  const boton = menu.querySelector(".menu-usuario__boton");
  const lista = menu.querySelector(".menu-usuario__lista");
  if (!boton) return;
  boton.setAttribute("aria-expanded", String(abrir));
  lista.hidden = !abrir;
}

menu.addEventListener("click", e => {
  if (e.target.closest(".menu-usuario__boton")) {
    return abrirMenu(menu.querySelector(".menu-usuario__lista").hidden);
  }
  if (e.target.closest("[data-cuenta]")) {
    abrirMenu(false);
    // Configuración lleva el foco a la sección "Tu cuenta" (si ya está abierta, se hace aquí).
    const cuenta = document.getElementById("cuenta");
    if (location.hash === "#/configuracion" && cuenta) {
      e.preventDefault();
      cuenta.scrollIntoView({ block: "start" });
      cuenta.focus({ preventScroll: true });
    } else {
      navegacion.irACuenta = true;
    }
    return;
  }
  if (e.target.closest("[data-salir]")) {
    abrirMenu(false);
    alCerrarSesion();
  }
});
document.addEventListener("click", e => { if (!menu.contains(e.target)) abrirMenu(false); });
document.addEventListener("keydown", e => {
  if (e.key === "Escape" && !menu.querySelector(".menu-usuario__lista")?.hidden) {
    abrirMenu(false);
    menu.querySelector(".menu-usuario__boton")?.focus();
  }
});

// ---------- Sesión vencida ----------
// La API respondió 401 a mitad del trabajo: se pide la contraseña encima de la pantalla
// actual, sin navegar, para no perder fotos ni lo capturado. Varias peticiones que
// fallan a la vez esperan la misma ventana.

let pendiente = null;

function pedirContrasena() {
  if (pendiente) return pendiente;

  pendiente = new Promise((resolver, rechazar) => {
    const u = sesion.usuario;
    const fondo = [document.querySelector(".topbar"), document.getElementById("vista"), document.querySelector(".pie")];
    const velo = document.createElement("div");
    velo.className = "velo-sesion";
    velo.innerHTML = `
      <form class="hoja-sesion" role="dialog" aria-modal="true" aria-labelledby="hoja-sesion-titulo" novalidate>
        <span class="hoja-sesion__agarre" aria-hidden="true"></span>
        <h2 id="hoja-sesion-titulo">Tu sesión terminó</h2>
        <p class="texto-suave">Entra de nuevo para continuar. Lo que estabas haciendo sigue aquí.</p>
        <div class="aviso aviso--error" role="alert" hidden>${icono("i-alert")}<span></span></div>
        <input type="email" name="usuario" autocomplete="username" value="${esc(u?.correo ?? "")}" hidden>
        ${campoContrasena({ id: "contrasena-sesion", etiqueta: `Contraseña de ${esc(u?.correo ?? "tu cuenta")}`, autocomplete: "current-password" })}
        <button type="submit" class="btn btn--primario btn--grande">Entrar y continuar</button>
        <button type="button" class="btn btn--texto" data-otra>Usar otra cuenta</button>
      </form>`;

    document.body.append(velo);
    fondo.forEach(el => el?.setAttribute("inert", ""));
    activarMostrar(velo);

    const form = velo.querySelector("form");
    const input = form.querySelector("#contrasena-sesion");
    const boton = form.querySelector('[type="submit"]');
    const aviso = form.querySelector(".aviso--error");
    input.focus();

    function cerrar() {
      fondo.forEach(el => el?.removeAttribute("inert"));
      velo.remove();
    }

    form.addEventListener("submit", async e => {
      e.preventDefault();
      if (!input.value) return input.focus();
      boton.disabled = true;
      boton.textContent = "Entrando…";
      try {
        establecerSesion(await entrar(u.correo, input.value));
        cerrar();
        resolver();
      } catch (err) {
        aviso.querySelector("span").textContent = err.sinConexion ? "No se pudo conectar con el servidor." : err.message;
        aviso.hidden = false;
        boton.disabled = false;
        boton.textContent = "Entrar y continuar";
        input.select();
        input.focus();
      }
    });

    form.querySelector("[data-otra]").addEventListener("click", () => {
      cerrar();
      rechazar(Object.assign(new Error("Sesión cerrada."), { status: 401, sesionCerrada: true }));
      alCerrarSesion();
    });
  }).finally(() => { pendiente = null; });

  return pendiente;
}

alVencerSesion(pedirContrasena);
