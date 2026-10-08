"""RF-06: extracción adaptativa de texto mediante Tesseract OCR."""

import re
import pytesseract
from pytesseract import Output

from app.services.preprocesamiento import preprocesar


# Términos frecuentes y útiles en etiquetado de tequila.
# No determinan cumplimiento; solamente ayudan a elegir
# qué resultado OCR parece contener información relevante.
TERMINOS_RELEVANTES = [
    "TEQUILA",
    "AGAVE",
    "ALC",
    "VOL",
    "MEXICO",
    "JALISCO",
    "LOTE",
    "CRISTALINO",
    "BLANCO",
    "REPOSADO",
    "ANEJO",
    "EXTRA ANEJO",
    "ML",
    "L",
    "NOM",
]


def _normalizar_simple(texto: str) -> str:
    """Normalización sencilla usada únicamente para puntuar OCR."""
    texto = texto.upper()
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


def _ejecutar_ocr(imagen, psm: int) -> dict:
    """Ejecuta Tesseract sobre una versión de la imagen."""

    datos = pytesseract.image_to_data(
        imagen,
        lang="spa+eng",
        config=f"--oem 3 --psm {psm}",
        output_type=Output.DICT,
    )

    palabras = []
    confianzas = []

    for texto, confianza in zip(
        datos["text"],
        datos["conf"]
    ):
        texto = texto.strip()

        try:
            confianza = float(confianza)
        except (ValueError, TypeError):
            continue

        if texto and confianza >= 0:
            palabras.append(texto)
            confianzas.append(confianza)

    texto_completo = " ".join(palabras)

    confianza_promedio = (
        sum(confianzas) / len(confianzas)
        if confianzas
        else 0.0
    )

    return {
        "texto": texto_completo,
        "confianza": round(confianza_promedio, 2),
        "elementos_detectados": len(palabras),
        "psm": psm,
    }


def _calcular_puntuacion(resultado: dict) -> float:
    """
    Puntúa la utilidad del resultado OCR.

    Combina:
    - confianza de Tesseract
    - cantidad razonable de texto
    - presencia de términos relevantes
    """

    texto = _normalizar_simple(resultado["texto"])
    confianza = resultado["confianza"]
    elementos = resultado["elementos_detectados"]

    encontrados = sum(
        1
        for termino in TERMINOS_RELEVANTES
        if termino in texto
    )

    # La confianza sigue siendo importante.
    puntuacion = confianza

    # Premiamos resultados con vocabulario relevante.
    puntuacion += encontrados * 15

    # Un poco de recompensa por obtener texto,
    # pero limitamos su peso para no premiar ruido.
    puntuacion += min(elementos, 30) * 0.15

    return round(puntuacion, 2)


def extraer_texto(ruta_imagen: str) -> dict:
    """
    Ejecuta OCR adaptativo.

    Genera varias versiones de la misma fotografía,
    prueba diferentes modos PSM y selecciona el
    resultado que parece más útil.
    """

    versiones = preprocesar(ruta_imagen)

    resultados = []

    for nombre_version, imagen in versiones.items():

        for psm in (6, 11, 12):

            resultado = _ejecutar_ocr(
                imagen,
                psm
            )

            resultado["version"] = nombre_version
            resultado["puntuacion"] = (
                _calcular_puntuacion(resultado)
            )

            resultados.append(resultado)

    mejor = max(
        resultados,
        key=lambda r: r["puntuacion"]
    )

    return {
        "texto": mejor["texto"],
        "confianza": mejor["confianza"],
        "elementos_detectados":
            mejor["elementos_detectados"],
        "version": mejor["version"],
        "psm": mejor["psm"],
        "puntuacion": mejor["puntuacion"],

        # Conservamos todos los intentos para
        # poder auditar por qué eligió ese resultado.
        "intentos": [
            {
                "version": r["version"],
                "psm": r["psm"],
                "confianza": r["confianza"],
                "elementos":
                    r["elementos_detectados"],
                "puntuacion": r["puntuacion"],
            }
            for r in resultados
        ],
    }