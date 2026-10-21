"""Contraseñas, sesiones y permisos.

- Contraseñas cifradas con Argon2id.
- Sesión en el servidor (tabla `sesiones`); el navegador solo guarda un
  token aleatorio en una cookie HttpOnly que el JavaScript no puede leer.
  En la base se guarda el SHA-256 del token, no el token.
- Sesión de 14 días que se renueva con el uso.
- Tras 5 intentos fallidos la cuenta espera 15 minutos.
"""

import hashlib
import os
import secrets
import threading
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import Depends, HTTPException, Request, Response

from app import basedatos


NOMBRE_COOKIE = "tla_sesion"
DURACION_SESION = timedelta(days=14)
# Para no escribir en la base en cada petición, la sesión
# se renueva como máximo una vez por hora.
RENOVAR_CADA = timedelta(hours=1)

MAX_INTENTOS = 5
BLOQUEO = timedelta(minutes=15)
# Límite por dirección IP, para intentos con correos que no existen.
MAX_FALLOS_POR_IP = 20

LONGITUD_MINIMA = 10

ROL_ADMIN = "administrador"
ROL_ANALISTA = "analista"

_hasher = PasswordHasher()
# Se verifica contra este hash cuando el correo no existe, para que
# la respuesta tarde lo mismo y no revele qué cuentas hay.
_HASH_SIMULADO = _hasher.hash(secrets.token_urlsafe(16))


# ==========================================
# CONTRASEÑAS
# ==========================================

def cifrar(contrasena: str) -> str:
    return _hasher.hash(contrasena)


def verificar(contrasena_hash: str | None, contrasena: str) -> bool:
    try:
        return _hasher.verify(contrasena_hash or _HASH_SIMULADO, contrasena) and bool(contrasena_hash)
    except (VerificationError, InvalidHashError):
        return False


def necesita_recifrar(contrasena_hash: str) -> bool:
    return _hasher.check_needs_rehash(contrasena_hash)


def error_contrasena_nueva(nueva: str, actual: str | None = None) -> str | None:
    """Devuelve el motivo por el que la contraseña no sirve, o None."""

    if len(nueva) < LONGITUD_MINIMA:
        return f"La contraseña debe tener al menos {LONGITUD_MINIMA} caracteres."
    if actual is not None and nueva == actual:
        return "La contraseña nueva debe ser distinta de la actual."
    return None


def contrasena_temporal() -> str:
    """Contraseña aleatoria para cuentas nuevas o restablecidas."""
    return secrets.token_urlsafe(9)  # 12 caracteres


# ==========================================
# FECHAS (mismo formato UTC que CURRENT_TIMESTAMP)
# ==========================================

def ahora() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def a_texto(fecha: datetime) -> str:
    return fecha.strftime("%Y-%m-%d %H:%M:%S")


def de_texto(texto: str) -> datetime:
    return datetime.strptime(texto, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)


# ==========================================
# SESIONES
# ==========================================

def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def crear_sesion(conexion, usuario_id: int, agente: str | None) -> str:
    token = secrets.token_urlsafe(32)
    momento = ahora()

    # Limpieza de paso: sesiones vencidas de cualquier usuario.
    conexion.execute("DELETE FROM sesiones WHERE expira <= ?", (a_texto(momento),))
    conexion.execute(
        """
        INSERT INTO sesiones (token_hash, usuario_id, creada, expira, ultimo_uso, agente)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            _hash_token(token),
            usuario_id,
            a_texto(momento),
            a_texto(momento + DURACION_SESION),
            a_texto(momento),
            (agente or "")[:200],
        )
    )
    return token


def cerrar_sesion(conexion, token: str | None) -> None:
    if token:
        conexion.execute("DELETE FROM sesiones WHERE token_hash = ?", (_hash_token(token),))


def cerrar_sesiones_de(conexion, usuario_id: int, excepto: str | None = None) -> None:
    """Cierra todas las sesiones de un usuario (menos, si se indica, la actual)."""

    conexion.execute(
        "DELETE FROM sesiones WHERE usuario_id = ? AND token_hash != ?",
        (usuario_id, _hash_token(excepto) if excepto else "")
    )


def poner_cookie(respuesta: Response, solicitud: Request, token: str) -> None:
    respuesta.set_cookie(
        NOMBRE_COOKIE,
        token,
        max_age=int(DURACION_SESION.total_seconds()),
        httponly=True,
        # En https (túnel o servidor) solo viaja cifrada. En http://127.0.0.1
        # (desarrollo local) el navegador no la aceptaría con Secure.
        secure=solicitud.url.scheme == "https",
        samesite="lax",
        path="/",
    )


def quitar_cookie(respuesta: Response) -> None:
    respuesta.delete_cookie(NOMBRE_COOKIE, path="/")


def publico(usuario) -> dict:
    """Datos del usuario que se pueden enviar al navegador."""

    return {
        "id": usuario["id"],
        "nombre": usuario["nombre"],
        "correo": usuario["correo"],
        "rol": usuario["rol"],
        "debe_cambiar_contrasena": bool(usuario["debe_cambiar_contrasena"]),
    }


def pruebas_activas() -> bool:
    """Mientras dure el desarrollo se pueden guardar análisis como prueba."""
    return os.environ.get("TEQUILA_PRUEBAS_ACTIVAS", "1") != "0"


# ==========================================
# LÍMITE DE INTENTOS POR IP (en memoria)
# ==========================================

_fallos_ip: dict[str, deque] = defaultdict(deque)
_candado_ip = threading.Lock()


def ip_bloqueada(ip: str) -> bool:
    limite = ahora() - BLOQUEO
    with _candado_ip:
        fallos = _fallos_ip[ip]
        while fallos and fallos[0] < limite:
            fallos.popleft()
        return len(fallos) >= MAX_FALLOS_POR_IP


def registrar_fallo_ip(ip: str) -> None:
    with _candado_ip:
        _fallos_ip[ip].append(ahora())


def reiniciar_fallos_ip() -> None:
    """Solo para pruebas."""
    with _candado_ip:
        _fallos_ip.clear()


# ==========================================
# DEPENDENCIAS DE FASTAPI
# ==========================================

NO_AUTENTICADO = HTTPException(
    status_code=401,
    detail="Inicia sesión para continuar.",
)


def sesion_valida(request: Request, response: Response) -> dict:
    """
    Usuario de la sesión actual, aunque deba cambiar su contraseña.
    Solo para las rutas de /auth.
    """

    token = request.cookies.get(NOMBRE_COOKIE)
    if not token:
        raise NO_AUTENTICADO

    with basedatos.obtener_conexion() as conexion:
        fila = conexion.execute(
            """
            SELECT s.id AS sesion_id, s.expira, s.ultimo_uso,
                   u.id, u.nombre, u.correo, u.rol, u.activo,
                   u.debe_cambiar_contrasena
            FROM sesiones s
            JOIN usuarios u ON u.id = s.usuario_id
            WHERE s.token_hash = ?
            """,
            (_hash_token(token),)
        ).fetchone()

        momento = ahora()

        if fila is None or not fila["activo"] or de_texto(fila["expira"]) <= momento:
            if fila is not None:
                conexion.execute("DELETE FROM sesiones WHERE id = ?", (fila["sesion_id"],))
            quitar_cookie(response)
            raise NO_AUTENTICADO

        # Renovación: cada uso extiende la sesión otros 14 días.
        if momento - de_texto(fila["ultimo_uso"]) >= RENOVAR_CADA:
            conexion.execute(
                "UPDATE sesiones SET expira = ?, ultimo_uso = ? WHERE id = ?",
                (a_texto(momento + DURACION_SESION), a_texto(momento), fila["sesion_id"])
            )
            poner_cookie(response, request, token)

    return publico(fila)


def usuario_actual(usuario: dict = Depends(sesion_valida)) -> dict:
    """Usuario con sesión y contraseña definitiva: lo exigen todas las rutas de datos."""

    if usuario["debe_cambiar_contrasena"]:
        raise HTTPException(
            status_code=403,
            detail="Debes cambiar tu contraseña temporal antes de continuar.",
        )
    return usuario


def requiere_admin(usuario: dict = Depends(usuario_actual)) -> dict:
    if usuario["rol"] != ROL_ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Solo un administrador puede hacer esto.",
        )
    return usuario


def es_admin(usuario: dict) -> bool:
    return usuario["rol"] == ROL_ADMIN
