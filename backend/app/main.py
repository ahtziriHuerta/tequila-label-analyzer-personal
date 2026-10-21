import os
from contextlib import asynccontextmanager
from pathlib import Path
import threading
from urllib.parse import urlsplit

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
import pytesseract
from fastapi.middleware.cors import CORSMiddleware

from app import basedatos
from app.routers import analisis, auth
from app.services.seguridad import usuario_actual


def _precargar_paddle():
    """Arranca el proceso de OCR y carga el modelo al iniciar el servidor,
    para que el primer análisis desde la app no espere ~10 s de carga."""
    try:
        from app.services.paddle_ocr import precargar
        precargar()
    except Exception:
        pass  # sin Paddle se usa Tesseract


@asynccontextmanager
async def ciclo_de_vida(_app):
    # Crea las tablas que falten y actualiza bases anteriores al login.
    basedatos.asegurar_esquema()
    threading.Thread(target=_precargar_paddle, daemon=True).start()
    yield


app = FastAPI(
    title="Analizador de etiquetado de Tequila",
    lifespan=ciclo_de_vida,
)

# ==========================================
# CONFIGURACIÓN DE RUTAS
# ==========================================

BASE_DIR = Path(__file__).resolve().parents[2]

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

# Live Server (:5500) para desarrollo del frontend; envía la cookie de sesión.
ORIGENES_DESARROLLO = [
    "http://127.0.0.1:5500",
    "http://localhost:5500"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGENES_DESARROLLO,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================
# PROTECCIÓN DE PETICIONES
# ==========================================

METODOS_QUE_MODIFICAN = {"POST", "PUT", "PATCH", "DELETE"}
RUTAS_PRIVADAS = ("/analisis", "/auth", "/imagenes")


@app.middleware("http")
async def proteger_peticiones(request, call_next):
    """
    - Rechaza peticiones que modifican datos si vienen de otro sitio
      (complementa la cookie SameSite=Lax contra CSRF).
    - Pide no guardar en caché las respuestas privadas: datos y fotos
      de una cuenta no deben quedar en el navegador tras cerrar sesión.
    """

    origen = request.headers.get("origin")

    if (
        request.method in METODOS_QUE_MODIFICAN
        and origen
        and urlsplit(origen).netloc != request.headers.get("host")
        and origen not in ORIGENES_DESARROLLO
    ):
        return JSONResponse(
            status_code=403,
            content={"detail": "Petición rechazada: origen no permitido."}
        )

    respuesta = await call_next(request)

    if request.url.path.startswith(RUTAS_PRIVADAS):
        respuesta.headers["Cache-Control"] = "no-store"

    return respuesta


# ==========================================
# ROUTERS
# ==========================================

app.include_router(auth.router)
app.include_router(analisis.router)


# ==========================================
# SALUD DEL BACKEND
# ==========================================

# Consultar Tesseract lanza dos procesos; mientras Paddle ocupa la CPU eso
# tardaba más de 20 s y la app daba el backend por apagado. Se guarda la
# primera consulta exitosa (no cambia mientras el servidor está encendido).
_tesseract_cache = None


def _estado_tesseract():
    global _tesseract_cache
    if _tesseract_cache is None:
        _tesseract_cache = (
            str(pytesseract.get_tesseract_version()),
            pytesseract.get_languages(),
        )
    return _tesseract_cache


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
        version_tesseract, idiomas = _estado_tesseract()
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


@app.middleware("http")
async def revalidar_frontend(request, call_next):
    """
    Pedir al navegador que confirme la versión de la interfaz
    antes de usar su copia guardada. Sin esto, Safari (iPhone)
    podía mezclar archivos viejos y nuevos tras un cambio.
    Si no hubo cambios el servidor responde 304, que es ligero.
    """

    respuesta = await call_next(request)

    if request.url.path.startswith("/app"):
        respuesta.headers["Cache-Control"] = "no-cache"

    return respuesta


# ==========================================
# CONSULTAR FOTOGRAFÍA GUARDADA
# ==========================================

@app.get("/imagenes/{imagen_id}")
def obtener_imagen(
    imagen_id: int,
    usuario: dict = Depends(usuario_actual)
):
    """
    Consulta una fotografía registrada en SQLite.

    Solo si el usuario puede ver el análisis al que
    pertenece. Se valida que el archivo corresponda a
    una imagen registrada y esté dentro de uploads.
    """

    with basedatos.obtener_conexion() as conexion:

        fila = conexion.execute(
            """
            SELECT i.ruta_archivo, a.usuario_id, a.es_prueba
            FROM imagenes i
            JOIN analisis a ON a.id = i.analisis_id
            WHERE i.id = ?
            """,
            (imagen_id,)
        ).fetchone()

    if fila is None or not analisis.puede_ver(usuario, fila):
        raise HTTPException(
            status_code=404,
            detail="La imagen no está registrada."
        )

    ruta = Path(fila["ruta_archivo"]).resolve()

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
