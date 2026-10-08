
"""Endpoints para el análisis de etiquetado de tequila."""

import os
import shutil
import sqlite3
import uuid
from pathlib import Path
from typing import List

from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel, Field
from typing import Literal
from app.services.analizador import analizar_imagenes


router = APIRouter(
    prefix="/analisis",
    tags=["analisis"]
)

# Directorio principal del proyecto.
BASE_DIR = Path(__file__).resolve().parents[3]

# Base de datos SQLite.
DATABASE_PATH = BASE_DIR / "database" / "tequila.db"

# Directorio donde se conservarán las fotografías.
UPLOADS_DIR = BASE_DIR / "backend" / "uploads"

UPLOADS_DIR.mkdir(
    parents=True,
    exist_ok=True
)


def obtener_conexion():
    """Crear una conexión a SQLite."""

    conexion = sqlite3.connect(DATABASE_PATH)
    conexion.row_factory = sqlite3.Row
    conexion.execute("PRAGMA foreign_keys = ON")

    return conexion


def obtener_usuario_sistema(conexion):
    """
    Crear o recuperar un usuario provisional.

    Posteriormente implementaremos registro
    e inicio de sesión.
    """

    correo = "sistema@tequila.local"

    conexion.execute(
        """
        INSERT OR IGNORE INTO usuarios (nombre, correo)
        VALUES (?, ?)
        """,
        ("Usuario de prueba", correo)
    )

    usuario = conexion.execute(
        """
        SELECT id
        FROM usuarios
        WHERE correo = ?
        """,
        (correo,)
    ).fetchone()

    return usuario["id"]


def registrar_reglas(conexion, reglas):
    """Registrar las reglas utilizadas por el analizador."""

    for codigo, regla in reglas.items():

        conexion.execute(
            """
            INSERT INTO reglas (
                codigo,
                requisito,
                descripcion
            )
            VALUES (?, ?, ?)
            ON CONFLICT(codigo) DO UPDATE SET
                requisito = excluded.requisito
            """,
            (
                codigo,
                regla["requisito"],
                "Evaluación automática mediante OCR"
            )
        )


def guardar_resultado(conexion, resultado, rutas):
    """Guardar análisis, imágenes y detecciones."""

    usuario_id = obtener_usuario_sistema(conexion)

    cursor = conexion.execute(
        """
        INSERT INTO analisis (usuario_id, estado)
        VALUES (?, ?)
        """,
        (usuario_id, "Revisión pendiente")
    )

    analisis_id = cursor.lastrowid

    # Relacionar número de fotografía con ID de SQLite.
    ids_imagenes = {}

    for indice, imagen in enumerate(resultado["imagenes"]):

        ruta = Path(rutas[indice])

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
                ruta.name,
                str(ruta),
                imagen["texto"],
                imagen["confianza"]
            )
        )

        ids_imagenes[indice + 1] = cursor.lastrowid

    registrar_reglas(
        conexion,
        resultado["reglas"]
    )

    # Guardar un resultado por regla.
    for codigo, regla in resultado["reglas"].items():

        evidencias = resultado["evidencias"].get(
            codigo,
            []
        )

        imagen_id = None

        if evidencias:
            numero_imagen = evidencias[0]["numero_imagen"]
            imagen_id = ids_imagenes.get(numero_imagen)

        conexion.execute(
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
                codigo,
                (
                    str(regla["valor"])
                    if regla["valor"] is not None
                    else None
                ),
                regla["estado"]
            )
        )

    return analisis_id


@router.post("/")
def crear_analisis():
    """
    Endpoint provisional.

    La creación y el guardado del análisis
    se realizan actualmente al subir imágenes.
    """

    return {
        "mensaje": (
            "Para crear y guardar un análisis, "
            "envía fotografías a /analisis/imagenes."
        )
    }


@router.post("/imagenes")
async def analizar_fotografias(
    archivos: List[UploadFile] = File(...)
):
    """
    Recibe fotografías, ejecuta OCR y reglas,
    conserva las imágenes y registra el análisis
    en SQLite.
    """

    if not archivos:
        raise HTTPException(
            status_code=400,
            detail="Debes enviar al menos una imagen."
        )

    rutas_guardadas = []

    try:

        # ==========================================
        # 1. GUARDAR FOTOGRAFÍAS
        # ==========================================

        for archivo in archivos:

            if (
                not archivo.content_type
                or not archivo.content_type.startswith("image/")
            ):
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"{archivo.filename} "
                        "no es una imagen válida."
                    )
                )

            extension = Path(
                archivo.filename or ""
            ).suffix.lower()

            if extension not in {
                ".jpg", ".jpeg", ".png",
                ".webp", ".bmp", ".tif", ".tiff"
            }:
                raise HTTPException(
                    status_code=400,
                    detail="Formato de imagen no permitido."
                )

            nombre_unico = (
                f"{uuid.uuid4().hex}{extension}"
            )

            ruta_destino = UPLOADS_DIR / nombre_unico

            with open(ruta_destino, "wb") as destino:
                shutil.copyfileobj(
                    archivo.file,
                    destino
                )

            rutas_guardadas.append(
                str(ruta_destino)
            )

        # ==========================================
        # 2. EJECUTAR ANALIZADOR
        # ==========================================

        resultado = analizar_imagenes(
            rutas_guardadas
        )

        # ==========================================
        # 3. GUARDAR RESULTADOS EN SQLITE
        # ==========================================

        with obtener_conexion() as conexion:

            analisis_id = guardar_resultado(
                conexion,
                resultado,
                rutas_guardadas
            )

        # ==========================================
        # 4. DEVOLVER RESULTADO AL FRONTEND
        # ==========================================

        resultado["id_analisis"] = analisis_id
        resultado["guardado"] = True

        return resultado

    except HTTPException:
        raise

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=f"Error al procesar el análisis: {error}"
        )

    finally:
        for archivo in archivos:
            await archivo.close()



# ==========================================
# 5. CONSULTAR HISTORIAL DE ANÁLISIS
# ==========================================

@router.get("/historial")
def obtener_historial():
    """Consultar todos los análisis guardados."""

    with obtener_conexion() as conexion:
        filas = conexion.execute(
            """
            SELECT
                a.id,
                a.usuario_id,
                u.nombre AS usuario,
                a.estado,
                a.fecha_creacion,
                (
                    SELECT COUNT(*)
                    FROM imagenes i
                    WHERE i.analisis_id = a.id
                ) AS total_imagenes,
                (
                    SELECT COUNT(*)
                    FROM detecciones d
                    WHERE d.analisis_id = a.id
                ) AS total_detecciones
            FROM analisis a
            JOIN usuarios u ON u.id = a.usuario_id
            ORDER BY a.id DESC
            """
        ).fetchall()

    return {
        "total": len(filas),
        "analisis": [dict(fila) for fila in filas]
    }


# ==========================================
# 6. CONSULTAR UN ANÁLISIS POR ID
# ==========================================

@router.get("/{analisis_id}")
def obtener_analisis(analisis_id: int):
    """Consultar los detalles de un análisis guardado."""

    with obtener_conexion() as conexion:

        analisis = conexion.execute(
            """
            SELECT
                a.id,
                a.usuario_id,
                u.nombre AS usuario,
                a.estado,
                a.fecha_creacion
            FROM analisis a
            JOIN usuarios u ON u.id = a.usuario_id
            WHERE a.id = ?
            """,
            (analisis_id,)
        ).fetchone()

        if analisis is None:
            raise HTTPException(
                status_code=404,
                detail="No se encontró el análisis solicitado."
            )

        imagenes = conexion.execute(
            """
            SELECT
                id,
                nombre_archivo,
                ruta_archivo,
                texto_ocr,
                confianza_ocr,
                fecha_carga
            FROM imagenes
            WHERE analisis_id = ?
            ORDER BY id
            """,
            (analisis_id,)
        ).fetchall()

        detecciones = conexion.execute(
            """
            SELECT
                d.id,
                d.codigo_regla,
                r.requisito,
                d.valor,
                d.estado,
                d.imagen_id,
                i.nombre_archivo AS imagen_evidencia,
                d.fecha_deteccion
            FROM detecciones d
            JOIN reglas r
                ON r.codigo = d.codigo_regla
            LEFT JOIN imagenes i
                ON i.id = d.imagen_id
            WHERE d.analisis_id = ?
            ORDER BY d.codigo_regla
            """,
            (analisis_id,)
        ).fetchall()

    return {
        "analisis": dict(analisis),
        "imagenes": [dict(imagen) for imagen in imagenes],
        "detecciones": [
            dict(deteccion)
            for deteccion in detecciones
        ]
    }


# ==========================================
# 7. MODELO DE REVISIÓN MANUAL
# ==========================================

class RevisionManualEntrada(BaseModel):
    codigo_regla: str = Field(min_length=1)

    resultado: Literal[
        "Presente",
        "Ausente",
        "No determinado"
    ]

    observaciones: str = Field(
        default="",
        max_length=2000
    )


# ==========================================
# 8. GUARDAR REVISIÓN MANUAL
# ==========================================

@router.post("/{analisis_id}/revisiones", status_code=201)
def guardar_revision_manual(
    analisis_id: int,
    revision: RevisionManualEntrada
):
    """
    Registrar una revisión humana de una regla.

    No modifica las detecciones originales
    realizadas mediante OCR.
    """

    codigo = revision.codigo_regla.strip().upper()
    observaciones = revision.observaciones.strip()

    with obtener_conexion() as conexion:

        # Comprobar que existe el análisis.
        analisis = conexion.execute(
            """
            SELECT id, usuario_id
            FROM analisis
            WHERE id = ?
            """,
            (analisis_id,)
        ).fetchone()

        if analisis is None:
            raise HTTPException(
                status_code=404,
                detail="No existe el análisis solicitado."
            )

        # Comprobar que la regla fue evaluada
        # dentro del análisis seleccionado.
        deteccion = conexion.execute(
            """
            SELECT id
            FROM detecciones
            WHERE analisis_id = ?
              AND codigo_regla = ?
            """,
            (analisis_id, codigo)
        ).fetchone()

        if deteccion is None:
            raise HTTPException(
                status_code=400,
                detail=(
                    "La regla indicada no pertenece "
                    "a este análisis."
                )
            )

        # Por ahora usamos el usuario asociado
        # al análisis. La autenticación real
        # se implementará posteriormente.
        usuario_id = analisis["usuario_id"]

        cursor = conexion.execute(
            """
            INSERT INTO revisiones_manuales (
                analisis_id,
                codigo_regla,
                usuario_id,
                resultado,
                observaciones
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                analisis_id,
                codigo,
                usuario_id,
                revision.resultado,
                observaciones
            )
        )

        revision_id = cursor.lastrowid

        fila = conexion.execute(
            """
            SELECT
                rm.id,
                rm.analisis_id,
                rm.codigo_regla,
                r.requisito,
                rm.usuario_id,
                u.nombre AS usuario,
                rm.resultado,
                rm.observaciones,
                rm.fecha_revision
            FROM revisiones_manuales rm
            JOIN reglas r
                ON r.codigo = rm.codigo_regla
            JOIN usuarios u
                ON u.id = rm.usuario_id
            WHERE rm.id = ?
            """,
            (revision_id,)
        ).fetchone()

    return {
        "mensaje": "Revisión manual guardada.",
        "revision": dict(fila)
    }


# ==========================================
# 9. CONSULTAR REVISIONES MANUALES
# ==========================================

@router.get("/{analisis_id}/revisiones")
def consultar_revisiones_manuales(
    analisis_id: int
):
    """
    Consultar el historial de revisiones
    manuales de un análisis.
    """

    with obtener_conexion() as conexion:

        analisis = conexion.execute(
            """
            SELECT id
            FROM analisis
            WHERE id = ?
            """,
            (analisis_id,)
        ).fetchone()

        if analisis is None:
            raise HTTPException(
                status_code=404,
                detail="No existe el análisis solicitado."
            )

        filas = conexion.execute(
            """
            SELECT
                rm.id,
                rm.analisis_id,
                rm.codigo_regla,
                r.requisito,
                rm.usuario_id,
                u.nombre AS usuario,
                rm.resultado,
                rm.observaciones,
                rm.fecha_revision
            FROM revisiones_manuales rm
            JOIN reglas r
                ON r.codigo = rm.codigo_regla
            JOIN usuarios u
                ON u.id = rm.usuario_id
            WHERE rm.analisis_id = ?
            ORDER BY rm.id DESC
            """,
            (analisis_id,)
        ).fetchall()

    return {
        "analisis_id": analisis_id,
        "total": len(filas),
        "revisiones": [
            dict(fila) for fila in filas
        ]
    }


