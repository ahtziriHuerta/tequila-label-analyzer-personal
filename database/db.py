
"""Configuración y operaciones básicas de SQLite."""

import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "tequila.db"
SCHEMA_PATH = BASE_DIR / "schema.sql"


def obtener_conexion():
    """
    Abre una conexión a SQLite.
    Permite acceder a los resultados por nombre de columna.
    """
    conexion = sqlite3.connect(DB_PATH)
    conexion.row_factory = sqlite3.Row

    # Habilita las relaciones entre tablas.
    conexion.execute("PRAGMA foreign_keys = ON")

    return conexion


def inicializar_base_datos():
    """Crea las tablas si todavía no existen."""

    with open(SCHEMA_PATH, "r", encoding="utf-8") as archivo:
        esquema = archivo.read()

    with obtener_conexion() as conexion:
        conexion.executescript(esquema)

    print("Base de datos inicializada correctamente.")
    print(f"Ubicación: {DB_PATH}")


def guardar_usuario(nombre, correo):
    """Registra un usuario y devuelve su identificador."""

    with obtener_conexion() as conexion:
        cursor = conexion.execute(
            """
            INSERT INTO usuarios (nombre, correo)
            VALUES (?, ?)
            """,
            (nombre, correo)
        )

        return cursor.lastrowid


def crear_analisis(usuario_id, estado="Pendiente"):
    """Crea un análisis asociado a un usuario."""

    with obtener_conexion() as conexion:
        cursor = conexion.execute(
            """
            INSERT INTO analisis (usuario_id, estado)
            VALUES (?, ?)
            """,
            (usuario_id, estado)
        )

        return cursor.lastrowid


def guardar_imagen(
    analisis_id,
    nombre_archivo,
    ruta_archivo,
    texto_ocr="",
    confianza_ocr=None
):
    """Guarda los datos de una fotografía."""

    with obtener_conexion() as conexion:
        cursor = conexion.execute(
            """
            INSERT INTO imagenes (
                analisis_id,
                nombre_archivo,
                ruta_archivo,
                texto_ocr,
                confianza_ocr
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                analisis_id,
                nombre_archivo,
                ruta_archivo,
                texto_ocr,
                confianza_ocr
            )
        )

        return cursor.lastrowid


def guardar_regla(codigo, requisito, descripcion=""):
    """Registra una regla sin duplicar su código."""

    with obtener_conexion() as conexion:
        conexion.execute(
            """
            INSERT INTO reglas (
                codigo,
                requisito,
                descripcion
            )
            VALUES (?, ?, ?)
            ON CONFLICT(codigo) DO UPDATE SET
                requisito = excluded.requisito,
                descripcion = excluded.descripcion
            """,
            (codigo, requisito, descripcion)
        )


def guardar_deteccion(
    analisis_id,
    codigo_regla,
    estado,
    valor=None,
    imagen_id=None
):
    """Guarda una detección y su fotografía, si existe."""

    with obtener_conexion() as conexion:
        cursor = conexion.execute(
            """
            INSERT INTO detecciones (
                analisis_id,
                imagen_id,
                codigo_regla,
                valor,
                estado
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                analisis_id,
                imagen_id,
                codigo_regla,
                valor,
                estado
            )
        )

        return cursor.lastrowid


if __name__ == "__main__":
    inicializar_base_datos()
