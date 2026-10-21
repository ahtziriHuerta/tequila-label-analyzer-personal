"""Servicio de reconocimiento de texto mediante PaddleOCR.

El OCR corre en un proceso aparte con el modelo ya cargado. Parte del trabajo
de Paddle no suelta el GIL, así que en un hilo dejaba al servidor sin atender
peticiones (ni /salud) durante cada análisis y la app lo daba por apagado.
"""

import importlib.util
import threading
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures.process import BrokenProcessPool
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def obtener_motor():
    """Carga el modelo una sola vez por proceso."""
    from paddleocr import PaddleOCR

    return PaddleOCR(
        lang="es",
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
        # En Windows (CPU) oneDNN falla con los modelos PP-OCRv6:
        # "ConvertPirAttribute2RuntimeAttribute not support".
        enable_mkldnn=False,
        # El detector del modelo trae limit_type="min" y procesa la foto completa
        # (12 MP en un iPhone): en CPU eran minutos por foto. Se limita el lado
        # mayor para detectar; el reconocimiento sigue leyendo los recortes de la
        # imagen original, así que no pierde nitidez.
        text_det_limit_type="max",
        text_det_limit_side_len=1920,
    )


# ==========================================
# PROCESO DE OCR
# ==========================================

_proceso = None
_candado = threading.Lock()


def _iniciar_proceso():
    """Un solo proceso: Paddle ya usa todos los núcleos y cada uno carga ~2 GB."""
    global _proceso
    with _candado:
        if _proceso is None:
            _proceso = ProcessPoolExecutor(max_workers=1, initializer=obtener_motor)
        return _proceso


def _reiniciar_proceso():
    global _proceso
    with _candado:
        if _proceso is not None:
            _proceso.shutdown(wait=False, cancel_futures=True)
        _proceso = None


def precargar():
    """Arranca el proceso y carga el modelo (se llama al iniciar el servidor)."""
    if paddle_instalado():
        _iniciar_proceso().submit(int).result()


def paddle_instalado() -> bool:
    return (
        importlib.util.find_spec("paddleocr") is not None
        and importlib.util.find_spec("paddle") is not None
    )


def extraer_texto_paddle(ruta_imagen: str) -> dict:
    """Extrae texto y lo adapta al formato del analizador."""

    if not Path(ruta_imagen).is_file():
        raise FileNotFoundError(ruta_imagen)
    if not paddle_instalado():
        raise ImportError("PaddleOCR no está instalado")

    try:
        return _iniciar_proceso().submit(_extraer_en_proceso, ruta_imagen).result()
    except BrokenProcessPool:
        # El proceso murió (p. ej. sin memoria): el próximo análisis lo vuelve a crear.
        _reiniciar_proceso()
        raise


def _extraer_en_proceso(ruta_imagen: str) -> dict:
    """Se ejecuta dentro del proceso de OCR."""

    resultados = obtener_motor().predict(ruta_imagen)

    textos = []
    confianzas = []

    for resultado in resultados:
        datos = resultado.json
        datos = datos.get("res", datos)

        for texto, confianza in zip(
            datos.get("rec_texts", []),
            datos.get("rec_scores", []),
        ):
            texto = str(texto).strip()
            confianza = float(confianza)

            if texto:
                textos.append(texto)
                confianzas.append(confianza * 100)

    confianza_promedio = (
        sum(confianzas) / len(confianzas)
        if confianzas
        else 0.0
    )

    confianza_promedio = round(confianza_promedio, 2)

    return {
        "texto": " ".join(textos),
        "confianza": confianza_promedio,
        "elementos_detectados": len(textos),
        "version": "paddleocr",
        "psm": 0,
        "puntuacion": confianza_promedio,
        "intentos": [],
    }
