"""Conexión a SQLite y actualización del esquema de bases existentes."""

import os
import sqlite3
from pathlib import Path


# Directorio principal del proyecto.
BASE_DIR = Path(__file__).resolve().parents[2]

DATABASE_PATH = Path(
    os.environ.get(
        "TEQUILA_DB_PATH",
        str(BASE_DIR / "database" / "tequila.db")
    )
)

ESQUEMA_PATH = BASE_DIR / "database" / "schema.sql"

# Dueño de los análisis hechos antes de que existiera el login.
CORREO_USUARIO_PRUEBA = "sistema@tequila.local"


def obtener_conexion():
    """Crear una conexión a SQLite con acceso por nombre de columna."""

    conexion = sqlite3.connect(DATABASE_PATH)
    conexion.row_factory = sqlite3.Row
    conexion.execute("PRAGMA foreign_keys = ON")

    return conexion


# Columnas agregadas después de la primera versión del esquema.
# Las bases creadas antes no las tienen: se agregan al arrancar.
COLUMNAS_NUEVAS = {
    "usuarios": {
        "contrasena_hash": "TEXT",
        "rol": "TEXT NOT NULL DEFAULT 'analista'",
        "activo": "INTEGER NOT NULL DEFAULT 1",
        "debe_cambiar_contrasena": "INTEGER NOT NULL DEFAULT 0",
        "intentos_fallidos": "INTEGER NOT NULL DEFAULT 0",
        "bloqueado_hasta": "TEXT",
        "ultimo_acceso": "TEXT",
    },
    "analisis": {
        "es_prueba": "INTEGER NOT NULL DEFAULT 0",
        # Formato CRT MO-RV/20.
        "destino": "TEXT",
        "empresa": "TEXT",
        "marca": "TEXT",
        "categoria": "TEXT",
        "clase": "TEXT",
        "contenido_ml": "REAL",
        "alcohol": "REAL",
        "aditivos": "TEXT",
    },
    "imagenes": {
        "motor_ocr": "TEXT",
        "vista": "TEXT",
    },
    "detecciones": {
        "observacion": "TEXT",
    },
}

# Versión del esquema guardada en PRAGMA user_version.
VERSION_ESQUEMA = 1


def asegurar_esquema():
    """
    Crear las tablas que falten y actualizar bases anteriores.

    Versión 1 (login): los análisis que ya existían pasan al
    bloque de pruebas, para seguir viendo su evolución.
    """

    with obtener_conexion() as conexion:
        conexion.executescript(
            ESQUEMA_PATH.read_text(encoding="utf-8")
        )

        for tabla, columnas in COLUMNAS_NUEVAS.items():
            existentes = {
                fila["name"]
                for fila in conexion.execute(f"PRAGMA table_info({tabla})")
            }
            for columna, definicion in columnas.items():
                if columna not in existentes:
                    conexion.execute(
                        f"ALTER TABLE {tabla} ADD COLUMN {columna} {definicion}"
                    )

        version = conexion.execute("PRAGMA user_version").fetchone()[0]

        if version < 1:
            conexion.execute("UPDATE analisis SET es_prueba = 1")
            conexion.execute(
                "UPDATE usuarios SET contrasena_hash = NULL WHERE correo = ?",
                (CORREO_USUARIO_PRUEBA,)
            )

        conexion.execute(f"PRAGMA user_version = {VERSION_ESQUEMA}")
