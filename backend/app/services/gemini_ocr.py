"""Lectura de etiquetas con la API de Gemini (Google).

Se le pide una transcripción LITERAL del texto; el motor de reglas de la
herramienta decide igual que con PaddleOCR o Tesseract. El modelo no
dictamina nada.

Configuración (backend/.env, que no se sube a git):

    GEMINI_API_KEY=...
    GEMINI_MODEL=gemini-3.6-flash               (opcional)
    GEMINI_MODEL_RESPALDO=gemini-3.5-flash      (opcional; si el principal está saturado)

Las fotos se envían a Google: no usar con etiquetas confidenciales en
una clave de nivel gratuito (Google puede usar esos datos).
"""

import base64
import io
import json
import os
import re
import time
from pathlib import Path

import httpx
from PIL import Image, ImageOps


URL_API = "https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"

# La API reduce la foto de todos modos; así se envía menos.
LADO_MAXIMO = 2048
TIEMPO_LIMITE = 60

# Errores pasajeros de la API (saturación, límite de uso): se reintenta.
ERRORES_PASAJEROS = {429, 500, 502, 503, 504}

PROMPT = """Transcribe TODO el texto visible en esta fotografía de una botella de tequila.

Devuelve SOLO un objeto JSON: {"texto": "..."}

Reglas estrictas:
- Copia el texto EXACTAMENTE como está impreso, aunque tenga errores, números raros o esté cortado. NO corrijas, NO completes palabras cortadas, NO adivines.
- Si una palabra se ve incompleta (por ejemplo "Tequi..."), escribe solo lo que se ve.
- No leas texto que se vea en espejo a través del vidrio.
- Separa los renglones con un salto de línea.
- Si no hay texto legible, devuelve {"texto": ""}.
"""


def modelo() -> str:
    return os.getenv("GEMINI_MODEL", "gemini-3.6-flash")


def modelo_respaldo() -> str:
    return os.getenv("GEMINI_MODEL_RESPALDO", "gemini-3.5-flash")


def gemini_configurado() -> bool:
    return bool(os.getenv("GEMINI_API_KEY"))


def _imagen_base64(ruta: Path) -> str:
    """JPEG derecho (según EXIF) y con el lado mayor a LADO_MAXIMO."""

    with Image.open(ruta) as imagen:
        imagen = ImageOps.exif_transpose(imagen).convert("RGB")
        imagen.thumbnail((LADO_MAXIMO, LADO_MAXIMO))
        bufer = io.BytesIO()
        imagen.save(bufer, format="JPEG", quality=90)
    return base64.b64encode(bufer.getvalue()).decode("ascii")


def extraer_texto_gemini(ruta_imagen: str) -> dict:
    """Extrae texto y lo adapta al formato del analizador."""

    ruta = Path(ruta_imagen)
    if not ruta.is_file():
        raise FileNotFoundError(ruta_imagen)
    if not gemini_configurado():
        raise RuntimeError("Falta GEMINI_API_KEY")

    cuerpo = {
        "contents": [{
            "parts": [
                {"inline_data": {"mime_type": "image/jpeg", "data": _imagen_base64(ruta)}},
                {"text": PROMPT},
            ],
        }],
        "generationConfig": {"responseMimeType": "application/json"},
    }

    # Dos intentos con el modelo principal y uno con el de respaldo;
    # si todos fallan, el analizador pasa al siguiente motor (Paddle).
    intentos = [(modelo(), 0), (modelo(), 2), (modelo_respaldo(), 1)]
    for numero, (nombre, espera) in enumerate(intentos, start=1):
        time.sleep(espera)
        respuesta = httpx.post(
            URL_API.format(modelo=nombre),
            headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"]},
            json=cuerpo,
            timeout=TIEMPO_LIMITE,
        )
        if respuesta.status_code not in ERRORES_PASAJEROS or numero == len(intentos):
            break

    respuesta.raise_for_status()

    partes = respuesta.json()["candidates"][0]["content"]["parts"]
    contenido = "".join(p.get("text", "") for p in partes).strip()
    contenido = re.sub(r"^```(?:json)?\s*|\s*```$", "", contenido)
    texto = str(json.loads(contenido).get("texto") or "")

    return {
        "texto": " ".join(texto.split()),
        # Gemini no da una confianza comparable con la del OCR:
        # None = "no disponible" (las reglas no la usan para decidir).
        "confianza": None,
        "elementos_detectados": len(texto.splitlines()),
        "version": "gemini",
        "psm": 0,
        "puntuacion": None,
        "intentos": [],
    }
