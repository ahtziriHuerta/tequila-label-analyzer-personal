"""Servicio de reconocimiento de texto mediante PaddleOCR."""

from functools import lru_cache
from pathlib import Path

from paddleocr import PaddleOCR


@lru_cache(maxsize=1)
def obtener_motor():
    """Carga el modelo una sola vez por proceso."""
    return PaddleOCR(
        lang="es",
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
    )


def extraer_texto_paddle(ruta_imagen: str) -> dict:
    """Extrae texto y lo adapta al formato del analizador."""

    if not Path(ruta_imagen).is_file():
        raise FileNotFoundError(ruta_imagen)

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
