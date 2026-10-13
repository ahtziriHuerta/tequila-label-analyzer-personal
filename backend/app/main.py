import os
from pathlib import Path
import sqlite3

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
import pytesseract
from fastapi.middleware.cors import CORSMiddleware

from app.routers import analisis


app = FastAPI(
    title="Analizador de etiquetado de Tequila"
)

# ==========================================
# CONFIGURACIÓN DE RUTAS
# ==========================================

BASE_DIR = Path(__file__).resolve().parents[2]

DATABASE_PATH = Path(
    os.environ.get(
        "TEQUILA_DB_PATH",
        str(BASE_DIR / "database" / "tequila.db")
    )
)


UPLOADS_DIR = Path(
    os.environ.get(
        "TEQUILA_UPLOADS_DIR",
        str(BASE_DIR / "backend" / "uploads")
    )
).resolve()

FRONTEND_DIR = BASE_DIR / "frontend"


# ==========================================
# CORS
# ==========================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500"
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================
# ROUTERS
# ==========================================

app.include_router(analisis.router)


# ==========================================
# SALUD DEL BACKEND
# ==========================================

@app.get("/salud")
def salud():
    """Estado del backend y disponibilidad de los motores OCR."""

    # Verificar PaddleOCR sin cargar los modelos.
    try:
        import importlib.util
        paddle_disponible = (
            importlib.util.find_spec("paddleocr") is not None
            and importlib.util.find_spec("paddle") is not None
        )
    except Exception:
        paddle_disponible = False

    # Verificar Tesseract como motor de respaldo.
    try:
        version_tesseract = str(pytesseract.get_tesseract_version())
        idiomas = pytesseract.get_languages()
        tesseract_disponible = {"spa", "eng"} <= set(idiomas)
    except Exception:
        version_tesseract = None
        idiomas = []
        tesseract_disponible = False

    motor = (
        "paddleocr" if paddle_disponible
        else "tesseract" if tesseract_disponible
        else None
    )

    return {
        "estado": "ok",
        "ocr": motor,
        "ocr_disponible": motor is not None,
        "ocr_version": "PaddleOCR" if motor == "paddleocr" else version_tesseract,
        "ocr_idiomas": idiomas,
        "paddleocr_disponible": paddle_disponible,
        "tesseract_disponible": tesseract_disponible,
        "tesseract_version": version_tesseract,
    }


# ==========================================
# FRONTEND (PWA)
# ==========================================
# El backend también sirve la interfaz en /app/.
# Así basta un solo puerto (8000) para usarla desde
# el celular o a través de un túnel HTTPS.

@app.get("/", include_in_schema=False)
def inicio():
    return RedirectResponse("/app/")


# ==========================================
# CONSULTAR FOTOGRAFÍA GUARDADA
# ==========================================

@app.get("/imagenes/{imagen_id}")
def obtener_imagen(imagen_id: int):
    """
    Consulta una fotografía registrada en SQLite.

    Se valida que el archivo corresponda a una
    imagen registrada y esté dentro de uploads.
    """

    with sqlite3.connect(DATABASE_PATH) as conexion:

        fila = conexion.execute(
            """
            SELECT ruta_archivo
            FROM imagenes
            WHERE id = ?
            """,
            (imagen_id,)
        ).fetchone()

    if fila is None:
        raise HTTPException(
            status_code=404,
            detail="La imagen no está registrada."
        )

    ruta = Path(fila[0]).resolve()

    # Impedir acceder a archivos fuera de uploads.
    if not ruta.is_relative_to(UPLOADS_DIR):
        raise HTTPException(
            status_code=403,
            detail="Ruta de imagen no permitida."
        )

    if not ruta.is_file():
        raise HTTPException(
            status_code=404,
            detail="El archivo de imagen no existe."
        )

    return FileResponse(ruta)


# Se monta al final para no tapar las rutas de la API.
app.mount(
    "/app",
    StaticFiles(directory=FRONTEND_DIR, html=True),
    name="frontend"
)
