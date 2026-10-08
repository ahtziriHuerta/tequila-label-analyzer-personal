
from pathlib import Path
import sqlite3

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from app.routers import analisis


app = FastAPI(
    title="Analizador de etiquetado de Tequila"
)

# ==========================================
# CONFIGURACIÓN DE RUTAS
# ==========================================

BASE_DIR = Path(__file__).resolve().parents[2]

DATABASE_PATH = BASE_DIR / "database" / "tequila.db"

UPLOADS_DIR = (
    BASE_DIR / "backend" / "uploads"
).resolve()


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
    return {"estado": "ok"}


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
