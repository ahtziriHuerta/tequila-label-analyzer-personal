"""Inicio y cierre de sesión, y cambio de contraseña."""

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from app import basedatos
from app.services import seguridad


router = APIRouter(
    prefix="/auth",
    tags=["auth"]
)

CREDENCIALES_INVALIDAS = "Correo o contraseña incorrectos. Revisa los datos e inténtalo de nuevo."
DEMASIADOS_INTENTOS = (
    "Demasiados intentos fallidos. "
    f"Espera {int(seguridad.BLOQUEO.total_seconds() // 60)} minutos e inténtalo de nuevo."
)


class EntradaSesion(BaseModel):
    correo: str = Field(min_length=1, max_length=254)
    contrasena: str = Field(min_length=1, max_length=256)


class CambioContrasena(BaseModel):
    actual: str = Field(min_length=1, max_length=256)
    nueva: str = Field(min_length=1, max_length=256)


def respuesta_usuario(usuario: dict) -> dict:
    return {
        "usuario": usuario,
        "pruebas_activas": seguridad.pruebas_activas(),
    }


@router.post("/entrar")
def entrar(datos: EntradaSesion, request: Request, response: Response):
    """Verifica correo y contraseña y abre la sesión (cookie HttpOnly)."""

    correo = datos.correo.strip().lower()
    ip = request.client.host if request.client else "desconocida"

    if seguridad.ip_bloqueada(ip):
        raise HTTPException(status_code=429, detail=DEMASIADOS_INTENTOS)

    momento = seguridad.ahora()

    with basedatos.obtener_conexion() as conexion:
        usuario = conexion.execute(
            "SELECT * FROM usuarios WHERE lower(correo) = ?",
            (correo,)
        ).fetchone()

        if usuario is not None and usuario["bloqueado_hasta"] and \
                seguridad.de_texto(usuario["bloqueado_hasta"]) > momento:
            raise HTTPException(status_code=429, detail=DEMASIADOS_INTENTOS)

        valida = seguridad.verificar(
            usuario["contrasena_hash"] if usuario is not None else None,
            datos.contrasena
        )

        if not valida or not usuario["activo"]:
            seguridad.registrar_fallo_ip(ip)

            if usuario is not None and usuario["contrasena_hash"]:
                intentos = usuario["intentos_fallidos"] + 1
                bloqueo = None
                if intentos >= seguridad.MAX_INTENTOS:
                    intentos = 0
                    bloqueo = seguridad.a_texto(momento + seguridad.BLOQUEO)
                conexion.execute(
                    "UPDATE usuarios SET intentos_fallidos = ?, bloqueado_hasta = ? WHERE id = ?",
                    (intentos, bloqueo, usuario["id"])
                )
                # Se guarda antes de responder con el error.
                conexion.commit()

            raise HTTPException(status_code=401, detail=CREDENCIALES_INVALIDAS)

        nuevo_hash = (
            seguridad.cifrar(datos.contrasena)
            if seguridad.necesita_recifrar(usuario["contrasena_hash"])
            else usuario["contrasena_hash"]
        )
        conexion.execute(
            """
            UPDATE usuarios
            SET intentos_fallidos = 0, bloqueado_hasta = NULL,
                ultimo_acceso = ?, contrasena_hash = ?
            WHERE id = ?
            """,
            (seguridad.a_texto(momento), nuevo_hash, usuario["id"])
        )

        token = seguridad.crear_sesion(
            conexion,
            usuario["id"],
            request.headers.get("user-agent")
        )

    seguridad.poner_cookie(response, request, token)
    return respuesta_usuario(seguridad.publico(usuario))


@router.post("/salir", status_code=204)
def salir(request: Request, response: Response):
    """Cierra la sesión en el servidor y borra la cookie."""

    with basedatos.obtener_conexion() as conexion:
        seguridad.cerrar_sesion(conexion, request.cookies.get(seguridad.NOMBRE_COOKIE))

    seguridad.quitar_cookie(response)


@router.get("/yo")
def yo(usuario: dict = Depends(seguridad.sesion_valida)):
    """Usuario de la sesión actual (la app lo consulta al abrir)."""

    return respuesta_usuario(usuario)


@router.post("/cambiar-contrasena")
def cambiar_contrasena(
    datos: CambioContrasena,
    request: Request,
    usuario: dict = Depends(seguridad.sesion_valida),
):
    """
    Cambia la contraseña del usuario actual. Cierra sus otras sesiones
    (por ejemplo, en un equipo que olvidó cerrar).
    """

    with basedatos.obtener_conexion() as conexion:
        fila = conexion.execute(
            "SELECT contrasena_hash FROM usuarios WHERE id = ?",
            (usuario["id"],)
        ).fetchone()

        if not seguridad.verificar(fila["contrasena_hash"], datos.actual):
            raise HTTPException(status_code=400, detail="La contraseña actual no es correcta.")

        motivo = seguridad.error_contrasena_nueva(datos.nueva, datos.actual)
        if motivo:
            raise HTTPException(status_code=400, detail=motivo)

        conexion.execute(
            "UPDATE usuarios SET contrasena_hash = ?, debe_cambiar_contrasena = 0 WHERE id = ?",
            (seguridad.cifrar(datos.nueva), usuario["id"])
        )
        seguridad.cerrar_sesiones_de(
            conexion,
            usuario["id"],
            excepto=request.cookies.get(seguridad.NOMBRE_COOKIE)
        )

    return respuesta_usuario({**usuario, "debe_cambiar_contrasena": False})
