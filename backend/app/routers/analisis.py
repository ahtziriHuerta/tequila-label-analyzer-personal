
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
DATABASE_PATH = Path(
    os.environ.get(
        "TEQUILA_DB_PATH",
        str(BASE_DIR / "database" / "tequila.db")
    )
)

# Directorio donde se conservarán las fotografías.
UPLOADS_DIR = Path(
    os.environ.get(
        "TEQUILA_UPLOADS_DIR",
        str(BASE_DIR / "backend" / "uploads")
    )
).resolve()

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

    guardar_detecciones(
        conexion,
        analisis_id,
        resultado,
        ids_imagenes
    )

    return analisis_id


def guardar_detecciones(conexion, analisis_id, resultado, ids_imagenes):
    """
    Guardar un resultado por regla.

    ids_imagenes relaciona el número de fotografía
    (1, 2, 3...) con su ID en SQLite.
    """

    registrar_reglas(
        conexion,
        resultado["reglas"]
    )

    for codigo, regla in resultado["reglas"].items():

        evidencias = resultado["evidencias"].get(
            codigo,
            []
        )

        imagen_id = None

        if evidencias:
            numero_imagen = evidencias[0]["numero_imagen"]
            imagen_id = ids_imagenes.get(numero_imagen)

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
                codigo,
                (
                    str(regla["valor"])
                    if regla["valor"] is not None
                    else None
                ),
                regla["estado"]
            )
        )

        # Guardar evidencias de cada fotografía.
        deteccion_id = cursor.lastrowid

        for evidencia in evidencias:
            imagen_evidencia_id = ids_imagenes.get(
                evidencia["numero_imagen"]
            )

            if imagen_evidencia_id is None:
                continue

            valor_detectado = evidencia.get("valor_detectado")

            conexion.execute(
                """
                INSERT INTO evidencias (
                    deteccion_id,
                    imagen_id,
                    valor_detectado,
                    estado
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    deteccion_id,
                    imagen_evidencia_id,
                    str(valor_detectado) if valor_detectado is not None else None,
                    evidencia["estado"]
                )
            )


EXTENSIONES_PERMITIDAS = {
    ".jpg", ".jpeg", ".png",
    ".webp", ".bmp", ".tif", ".tiff"
}

ESTADO_FINALIZADO = "Finalizado"


def guardar_archivo(archivo: UploadFile) -> str:
    """Validar una fotografía y conservarla en uploads."""

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

    if extension not in EXTENSIONES_PERMITIDAS:
        raise HTTPException(
            status_code=400,
            detail="Formato de imagen no permitido."
        )

    ruta_destino = UPLOADS_DIR / f"{uuid.uuid4().hex}{extension}"

    with open(ruta_destino, "wb") as destino:
        shutil.copyfileobj(
            archivo.file,
            destino
        )

    return str(ruta_destino)


def obtener_analisis_abierto(conexion, analisis_id):
    """
    Recuperar un análisis que todavía admite cambios.

    Un análisis finalizado queda en solo lectura:
    no acepta fotografías ni revisiones nuevas.
    """

    analisis = conexion.execute(
        """
        SELECT id, usuario_id, estado
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

    if analisis["estado"] == ESTADO_FINALIZADO:
        raise HTTPException(
            status_code=409,
            detail="El análisis está finalizado (solo lectura)."
        )

    return analisis


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

            rutas_guardadas.append(
                guardar_archivo(archivo)
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
                ) AS total_detecciones,
                (
                    SELECT COUNT(*)
                    FROM detecciones d
                    WHERE d.analisis_id = a.id
                      AND d.estado = 'Detectado'
                ) AS total_detectados
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

        evidencias = conexion.execute(
            """
            SELECT
                e.id,
                e.deteccion_id,
                e.imagen_id,
                d.codigo_regla,
                e.valor_detectado,
                e.estado
            FROM evidencias e
            JOIN detecciones d
                ON d.id = e.deteccion_id
            WHERE d.analisis_id = ?
            ORDER BY e.imagen_id, d.codigo_regla
            """,
            (analisis_id,)
        ).fetchall()

    return {
        "analisis": dict(analisis),
        "imagenes": [dict(imagen) for imagen in imagenes],
        "detecciones": [dict(deteccion) for deteccion in detecciones],
        "evidencias": [dict(evidencia) for evidencia in evidencias]
    }

# ==========================================
# 6.1 ELIMINAR UN ANÁLISIS
# ==========================================

@router.delete("/{analisis_id}", status_code=204)
def eliminar_analisis(analisis_id: int):
    """
    Eliminar un análisis con sus fotografías,
    detecciones y revisiones manuales.
    """

    with obtener_conexion() as conexion:

        filas = conexion.execute(
            """
            SELECT ruta_archivo
            FROM imagenes
            WHERE analisis_id = ?
            """,
            (analisis_id,)
        ).fetchall()

        cursor = conexion.execute(
            "DELETE FROM analisis WHERE id = ?",
            (analisis_id,)
        )

        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail="No existe el análisis solicitado."
            )

    # Borrar los archivos solo después de confirmar
    # el borrado en la base de datos.
    for fila in filas:
        ruta = Path(fila["ruta_archivo"]).resolve()

        if ruta.is_relative_to(UPLOADS_DIR.resolve()):
            ruta.unlink(missing_ok=True)


# ==========================================
# 6.2 AGREGAR EVIDENCIA (CU-06)
# ==========================================

@router.post("/{analisis_id}/imagenes")
async def agregar_evidencia(
    analisis_id: int,
    archivos: List[UploadFile] = File(...)
):
    """
    Agregar fotografías a un análisis existente
    y volver a evaluar las reglas.

    Solo se ejecuta OCR sobre las fotos nuevas;
    las anteriores reutilizan el texto guardado.
    Las revisiones manuales se conservan.
    """

    rutas_nuevas = []

    try:

        with obtener_conexion() as conexion:

            obtener_analisis_abierto(
                conexion,
                analisis_id
            )

            anteriores = conexion.execute(
                """
                SELECT id, ruta_archivo, texto_ocr, confianza_ocr
                FROM imagenes
                WHERE analisis_id = ?
                ORDER BY id
                """,
                (analisis_id,)
            ).fetchall()

        for archivo in archivos:
            rutas_nuevas.append(
                guardar_archivo(archivo)
            )

        ocr_previo = {
            fila["ruta_archivo"]: {
                "texto": fila["texto_ocr"] or "",
                "confianza": fila["confianza_ocr"] or 0.0,
                "version": "guardado",
                "psm": None,
                "puntuacion": None,
            }
            for fila in anteriores
        }

        rutas = [
            fila["ruta_archivo"]
            for fila in anteriores
        ] + rutas_nuevas

        resultado = analizar_imagenes(
            rutas,
            ocr_previo=ocr_previo
        )

        with obtener_conexion() as conexion:

            # Número de fotografía -> ID en SQLite.
            ids_imagenes = {
                indice + 1: fila["id"]
                for indice, fila in enumerate(anteriores)
            }

            for indice, ruta in enumerate(
                rutas_nuevas,
                start=len(anteriores)
            ):
                imagen = resultado["imagenes"][indice]

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
                        Path(ruta).name,
                        ruta,
                        imagen["texto"],
                        imagen["confianza"]
                    )
                )

                ids_imagenes[indice + 1] = cursor.lastrowid

            # Reemplazar las detecciones anteriores
            # por la nueva evaluación.
            conexion.execute(
                "DELETE FROM detecciones WHERE analisis_id = ?",
                (analisis_id,)
            )

            guardar_detecciones(
                conexion,
                analisis_id,
                resultado,
                ids_imagenes
            )

        resultado["id_analisis"] = analisis_id
        resultado["guardado"] = True

        return resultado

    except HTTPException:
        for ruta in rutas_nuevas:
            Path(ruta).unlink(missing_ok=True)
        raise

    except Exception as error:
        for ruta in rutas_nuevas:
            Path(ruta).unlink(missing_ok=True)

        raise HTTPException(
            status_code=500,
            detail=f"Error al agregar la evidencia: {error}"
        )

    finally:
        for archivo in archivos:
            await archivo.close()


# ==========================================
# 6.3 FINALIZAR ANÁLISIS
# ==========================================

@router.post("/{analisis_id}/finalizar")
def finalizar_analisis(analisis_id: int):
    """
    Cerrar el análisis: queda en solo lectura
    (sin fotos nuevas ni revisiones manuales).
    """

    with obtener_conexion() as conexion:

        obtener_analisis_abierto(
            conexion,
            analisis_id
        )

        conexion.execute(
            """
            UPDATE analisis
            SET estado = ?
            WHERE id = ?
            """,
            (ESTADO_FINALIZADO, analisis_id)
        )

    return {
        "id_analisis": analisis_id,
        "estado": ESTADO_FINALIZADO
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

        # Comprobar que existe y no está finalizado.
        analisis = obtener_analisis_abierto(
            conexion,
            analisis_id
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


