"""Gestión de cuentas desde la terminal (mientras no exista la pantalla de Usuarios).

Desde backend/ (o con PYTHONPATH=backend) y la misma TEQUILA_DB_PATH que el servidor:

    python -m app.usuarios_cli crear --nombre "Ana López" --correo ana@ejemplo.mx --rol administrador
    python -m app.usuarios_cli restablecer --correo ana@ejemplo.mx
    python -m app.usuarios_cli desactivar --correo ana@ejemplo.mx
    python -m app.usuarios_cli activar --correo ana@ejemplo.mx
    python -m app.usuarios_cli listar

`crear` y `restablecer` muestran una contraseña temporal UNA sola vez; la persona
debe cambiarla al entrar. Entrégala por un medio privado.
"""

import argparse
import sqlite3
import sys

from app import basedatos
from app.services import seguridad


def _usuario(conexion, correo):
    fila = conexion.execute(
        "SELECT * FROM usuarios WHERE lower(correo) = ?",
        (correo.strip().lower(),)
    ).fetchone()
    if fila is None:
        sys.exit(f"No existe una cuenta con el correo {correo}.")
    return fila


def _mostrar_temporal(correo, temporal):
    print(f"\nCuenta: {correo}")
    print(f"Contraseña temporal: {temporal}")
    print("Se pedirá cambiarla al iniciar sesión. Entrégala por un medio privado.\n")


def crear(args):
    temporal = seguridad.contrasena_temporal()
    correo = args.correo.strip().lower()
    try:
        with basedatos.obtener_conexion() as conexion:
            conexion.execute(
                """
                INSERT INTO usuarios (nombre, correo, rol, contrasena_hash, debe_cambiar_contrasena)
                VALUES (?, ?, ?, ?, 1)
                """,
                (args.nombre.strip(), correo, args.rol, seguridad.cifrar(temporal))
            )
    except sqlite3.IntegrityError:
        sys.exit(f"Ya existe una cuenta con el correo {correo}.")
    _mostrar_temporal(correo, temporal)


def restablecer(args):
    temporal = seguridad.contrasena_temporal()
    with basedatos.obtener_conexion() as conexion:
        usuario = _usuario(conexion, args.correo)
        conexion.execute(
            """
            UPDATE usuarios
            SET contrasena_hash = ?, debe_cambiar_contrasena = 1,
                intentos_fallidos = 0, bloqueado_hasta = NULL
            WHERE id = ?
            """,
            (seguridad.cifrar(temporal), usuario["id"])
        )
        seguridad.cerrar_sesiones_de(conexion, usuario["id"])
    _mostrar_temporal(usuario["correo"], temporal)


def cambiar_activo(args, activo):
    with basedatos.obtener_conexion() as conexion:
        usuario = _usuario(conexion, args.correo)
        conexion.execute("UPDATE usuarios SET activo = ? WHERE id = ?", (int(activo), usuario["id"]))
        if not activo:
            # Desactivar cierra todas sus sesiones al instante.
            seguridad.cerrar_sesiones_de(conexion, usuario["id"])
    print(f"{usuario['correo']}: {'activada' if activo else 'desactivada'}.")


def listar(_args):
    with basedatos.obtener_conexion() as conexion:
        filas = conexion.execute(
            """
            SELECT nombre, correo, rol, activo, contrasena_hash IS NOT NULL AS puede_entrar,
                   ultimo_acceso
            FROM usuarios ORDER BY nombre
            """
        ).fetchall()
    for f in filas:
        estado = "activa" if f["activo"] and f["puede_entrar"] else "sin acceso"
        print(f"{f['nombre']:<28} {f['correo']:<32} {f['rol']:<14} {estado:<11} último acceso: {f['ultimo_acceso'] or '—'}")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Cuentas del analizador de etiquetado.")
    sub = parser.add_subparsers(dest="comando", required=True)

    p = sub.add_parser("crear", help="Crear una cuenta con contraseña temporal")
    p.add_argument("--nombre", required=True)
    p.add_argument("--correo", required=True)
    p.add_argument("--rol", choices=[seguridad.ROL_ANALISTA, seguridad.ROL_ADMIN], default=seguridad.ROL_ANALISTA)
    p.set_defaults(fn=crear)

    for nombre, ayuda, fn in (
        ("restablecer", "Nueva contraseña temporal (cierra sus sesiones)", restablecer),
        ("desactivar", "Impedir el acceso (cierra sus sesiones)", lambda a: cambiar_activo(a, False)),
        ("activar", "Permitir de nuevo el acceso", lambda a: cambiar_activo(a, True)),
    ):
        p = sub.add_parser(nombre, help=ayuda)
        p.add_argument("--correo", required=True)
        p.set_defaults(fn=fn)

    sub.add_parser("listar", help="Ver las cuentas").set_defaults(fn=listar)

    args = parser.parse_args(argv)
    basedatos.asegurar_esquema()
    args.fn(args)


if __name__ == "__main__":
    main()
