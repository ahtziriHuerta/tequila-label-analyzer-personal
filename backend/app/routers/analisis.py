
"""Endpoints para el análisis de etiquetado de tequila."""

import os
import shutil
import uuid
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Query
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field
from typing import Literal
from app.basedatos import obtener_conexion
from app.services.analizador import analizar_imagenes
from app.services.seguridad import es_admin, pruebas_activas, requiere_admin, usuario_actual


# Todas las rutas exigen sesión con contraseña definitiva.
router = APIRouter(
    prefix="/analisis",
    tags=["analisis"],
    dependencies=[Depends(usuario_actual)]
)

# Directorio principal del proyecto.
BASE_DIR = Path(__file__).resolve().parents[3]

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


def puede_ver(usuario, analisis) -> bool:
    """
    Cada analista ve solo sus análisis; el bloque de pruebas
    es de todo el equipo y el administrador ve todo.
    """

    return (
        es_admin(usuario)
        or analisis["usuario_id"] == usuario["id"]
        or bool(analisis["es_prueba"])
    )


def obtener_analisis_visible(conexion, analisis_id, usuario):
    """
    Recuperar un análisis que el usuario puede ver.

    Si no puede verlo se responde 404, igual que si no
    existiera, para no revelar los análisis de otros.
    """

    analisis = conexion.execute(
        """
        SELECT id, usuario_id, estado, es_prueba
        FROM analisis
        WHERE id = ?
        """,
        (analisis_id,)
    ).fetchone()

    if analisis is None or not puede_ver(usuario, analisis):
        raise HTTPException(
            status_code=404,
            detail="No existe el análisis solicitado."
        )

    return analisis


def motor_ocr(imagen) -> str | None:
    """Motor que leyó la foto, para comparar en el bloque de pruebas."""

    version = imagen.get("version")
    if version == "paddleocr":
        return "paddleocr"
    if version in (None, "guardado"):
        return None
    return "tesseract"


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


def guardar_resultado(conexion, resultado, rutas, usuario_id, es_prueba=False):
    """Guardar análisis, imágenes y detecciones."""

    cursor = conexion.execute(
        """
        INSERT INTO analisis (usuario_id, estado, es_prueba)
        VALUES (?, ?, ?)
        """,
        (usuario_id, "Revisión pendiente", int(es_prueba))
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
                confianza_ocr,
                motor_ocr
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                analisis_id,
                ruta.name,
                str(ruta),
                imagen["texto"],
                imagen["confianza"],
                motor_ocr(imagen)
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


def obtener_analisis_abierto(conexion, analisis_id, usuario):
    """
    Recuperar un análisis visible que todavía admite cambios.

    Un análisis finalizado queda en solo lectura:
    no acepta fotografías ni revisiones nuevas.
    """

    analisis = obtener_analisis_visible(
        conexion,
        analisis_id,
        usuario
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
    archivos: List[UploadFile] = File(...),
    es_prueba: bool = Form(False),
    usuario: dict = Depends(usuario_actual)
):
    """
    Recibe fotografías, ejecuta OCR y reglas,
    conserva las imágenes y registra el análisis
    en SQLite a nombre del usuario de la sesión.

    es_prueba: guardarlo en el bloque de pruebas
    (solo mientras las pruebas estén activas).
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

        # El OCR es lento y síncrono: en un hilo aparte para no bloquear
        # el servidor (si no, /salud deja de responder y la app lo da por apagado).
        resultado = await run_in_threadpool(
            analizar_imagenes,
            rutas_guardadas
        )

        # ==========================================
        # 3. GUARDAR RESULTADOS EN SQLITE
        # ==========================================

        with obtener_conexion() as conexion:

            analisis_id = guardar_resultado(
                conexion,
                resultado,
                rutas_guardadas,
                usuario["id"],
                es_prueba=es_prueba and pruebas_activas()
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
def obtener_historial(
    ambito: Literal["mios", "pruebas", "todos"] = "mios",
    usuario_id: int | None = Query(default=None),
    usuario: dict = Depends(usuario_actual)
):
    """
    Consultar los análisis guardados.

    - mios: los del usuario, sin las pruebas.
    - pruebas: el bloque de pruebas del equipo.
    - todos: todos los análisis (solo administrador),
      opcionalmente de un usuario (usuario_id).
    """

    if ambito == "todos" and not es_admin(usuario):
        raise HTTPException(
            status_code=403,
            detail="Solo un administrador puede ver los análisis de todos."
        )

    condiciones = {
        "mios": ("a.usuario_id = ? AND a.es_prueba = 0", [usuario["id"]]),
        "pruebas": ("a.es_prueba = 1", []),
        "todos": ("1 = 1", []),
    }
    filtro, parametros = condiciones[ambito]

    if ambito == "todos" and usuario_id is not None:
        filtro += " AND a.usuario_id = ?"
        parametros.append(usuario_id)

    with obtener_conexion() as conexion:
        filas = conexion.execute(
            f"""
            SELECT
                a.id,
                a.usuario_id,
                u.nombre AS usuario,
                a.estado,
                a.es_prueba,
                a.fecha_creacion,
                (
                    SELECT GROUP_CONCAT(DISTINCT i.motor_ocr)
                    FROM imagenes i
                    WHERE i.analisis_id = a.id
                ) AS motores_ocr,
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
            WHERE {filtro}
            ORDER BY a.id DESC
            """,
            parametros
        ).fetchall()

        # Para el filtro por usuario del administrador.
        usuarios = (
            [
                dict(fila)
                for fila in conexion.execute(
                    """
                    SELECT DISTINCT u.id, u.nombre
                    FROM usuarios u
                    JOIN analisis a ON a.usuario_id = u.id
                    ORDER BY u.nombre
                    """
                )
            ]
            if ambito == "todos"
            else []
        )

    return {
        "total": len(filas),
        "analisis": [dict(fila) for fila in filas],
        "usuarios": usuarios
    }


# ==========================================
# 6. CONSULTAR UN ANÁLISIS POR ID
# ==========================================

@router.get("/{analisis_id}")
def obtener_analisis(
    analisis_id: int,
    usuario: dict = Depends(usuario_actual)
):
    """Consultar los detalles de un análisis guardado."""

    with obtener_conexion() as conexion:

        obtener_analisis_visible(conexion, analisis_id, usuario)

        analisis = conexion.execute(
            """
            SELECT
                a.id,
                a.usuario_id,
                u.nombre AS usuario,
                a.estado,
                a.es_prueba,
                a.fecha_creacion
            FROM analisis a
            JOIN usuarios u ON u.id = a.usuario_id
            WHERE a.id = ?
            """,
            (analisis_id,)
        ).fetchone()

        imagenes = conexion.execute(
            """
            SELECT
                id,
                nombre_archivo,
                ruta_archivo,
                texto_ocr,
                confianza_ocr,
                motor_ocr,
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

@router.delete(
    "/{analisis_id}",
    status_code=204,
    dependencies=[Depends(requiere_admin)]
)
def eliminar_analisis(analisis_id: int):
    """
    Eliminar un análisis con sus fotografías,
    detecciones y revisiones manuales.

    Solo un administrador puede hacerlo.
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
    archivos: List[UploadFile] = File(...),
    usuario: dict = Depends(usuario_actual)
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
                analisis_id,
                usuario
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

        resultado = await run_in_threadpool(
            analizar_imagenes,
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
                        confianza_ocr,
                        motor_ocr
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        analisis_id,
                        Path(ruta).name,
                        ruta,
                        imagen["texto"],
                        imagen["confianza"],
                        motor_ocr(imagen)
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
def finalizar_analisis(
    analisis_id: int,
    usuario: dict = Depends(usuario_actual)
):
    """
    Cerrar el análisis: queda en solo lectura
    (sin fotos nuevas ni revisiones manuales).
    """

    with obtener_conexion() as conexion:

        obtener_analisis_abierto(
            conexion,
            analisis_id,
            usuario
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
    revision: RevisionManualEntrada,
    usuario: dict = Depends(usuario_actual)
):
    """
    Registrar una revisión humana de una regla.

    No modifica las detecciones originales
    realizadas mediante OCR.
    """

    codigo = revision.codigo_regla.strip().upper()
    observaciones = revision.observaciones.strip()

    with obtener_conexion() as conexion:

        # Comprobar que existe, es visible y no está finalizado.
        obtener_analisis_abierto(
            conexion,
            analisis_id,
            usuario
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

        # La revisión queda a nombre de quien la hizo,
        # no del autor del análisis.
        usuario_id = usuario["id"]

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
    analisis_id: int,
    usuario: dict = Depends(usuario_actual)
):
    """
    Consultar el historial de revisiones
    manuales de un análisis.
    """

    with obtener_conexion() as conexion:

        obtener_analisis_visible(conexion, analisis_id, usuario)

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


