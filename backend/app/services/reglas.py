"""Motor de reglas para análisis de etiquetado."""

import re
import unicodedata
from typing import Optional


ESTADOS = [
    "Detectado",
    "No localizado",
    "Imagen adicional requerida",
    "Baja legibilidad",
    "Revisión manual",
]


def normalizar(texto: str) -> str:
    """
    Convierte el texto a mayúsculas,
    elimina acentos y uniforma espacios.
    """

    texto = unicodedata.normalize(
        "NFD",
        texto.upper()
    )

    texto = "".join(
        caracter
        for caracter in texto
        if unicodedata.category(caracter) != "Mn"
    )

    return re.sub(
        r"\s+",
        " ",
        texto
    ).strip()


def detectar_denominacion(
    texto_normalizado: str,
    confianza_ocr: Optional[float] = None
) -> str:
    """
    ET-01: detectar la denominación TEQUILA.
    """

    if "TEQUILA" in texto_normalizado:
        return "Detectado"

    if (
        confianza_ocr is not None
        and confianza_ocr < 60
    ):
        return "Baja legibilidad"

    return "No localizado"


def detectar_categoria(
    texto_normalizado: str,
    confianza_ocr: Optional[float] = None
) -> dict:
    """
    ET-02: detectar categoría.
    """

    patrones_100_agave = [
        "100% DE AGAVE",
        "100 % DE AGAVE",
        "100% AGAVE",
        "100 % AGAVE",
    ]

    for patron in patrones_100_agave:
        if patron in texto_normalizado:
            return {
                "estado": "Detectado",
                "valor": "100% de agave"
            }

    if (
        confianza_ocr is not None
        and confianza_ocr < 60
    ):
        return {
            "estado": "Baja legibilidad",
            "valor": None
        }

    return {
        "estado": "Revisión manual",
        "valor": None
    }


def detectar_clase(
    texto_normalizado: str,
    confianza_ocr: Optional[float] = None
) -> dict:
    """
    ET-03: detectar la clase del tequila.
    """

    clases = [
        ("EXTRA ANEJO", "Extra añejo"),
        ("REPOSADO", "Reposado"),
        ("ANEJO", "Añejo"),
        ("BLANCO", "Blanco"),
        ("PLATA", "Blanco"),
        ("JOVEN", "Joven"),
        ("ORO", "Joven"),
    ]

    for termino, valor in clases:
        if termino in texto_normalizado:
            return {
                "estado": "Detectado",
                "valor": valor
            }

    if (
        confianza_ocr is not None
        and confianza_ocr < 60
    ):
        return {
            "estado": "Baja legibilidad",
            "valor": None
        }

    return {
        "estado": "No localizado",
        "valor": None
    }

def detectar_contenido_neto(
    texto_normalizado: str,
    confianza_ocr: Optional[float] = None
) -> dict:
    """
    ET-05: localizar el contenido neto declarado.

    Ejemplos:
    750 ML, 700 ML, 1 L, 1.5 L.
    """

    patron = (
        r"(?<![A-Z0-9])"
        r"(\d{1,4}(?:[.,]\d{1,3})?)"
        r"\s*(ML|LITROS?|L)"
        r"(?![A-Z])"
    )

    coincidencias = re.findall(
        patron,
        texto_normalizado
    )

    valores = []

    for cantidad, unidad in coincidencias:
        numero = float(cantidad.replace(",", "."))

        if unidad in ("L", "LITRO", "LITROS"):
            mililitros = numero * 1000
        else:
            mililitros = numero

        if 50 <= mililitros <= 5000:
            valores.append(mililitros)

    if valores:
        valores_unicos = sorted(set(valores))

        if len(valores_unicos) == 1:
            cantidad = valores_unicos[0]

            return {
                "estado": "Detectado",
                "valor": f"{cantidad:g} mL"
            }

        return {
            "estado": "Revisión manual",
            "valor": ", ".join(
                f"{valor:g} mL"
                for valor in valores_unicos
            )
        }

    if confianza_ocr is not None and confianza_ocr < 60:
        return {
            "estado": "Baja legibilidad",
            "valor": None
        }

    return {
        "estado": "No localizado",
        "valor": None
    }

def detectar_graduacion_alcoholica(
    texto_normalizado: str,
    confianza_ocr: Optional[float] = None
) -> dict:
    """
    ET-07: detectar el porcentaje de alcohol declarado.
    """

    patron = (
        r"(?<![\d])"
        r"(\d{1,2}(?:[.,]\d{1,2})?)"
        r"\s*%\s*"
        r"(?:ALC\.?\s*[/.-]?\s*VOL\.?|VOL\.?)"
        r"(?![A-Z])"
    )

    coincidencias = re.findall(
        patron,
        texto_normalizado
    )

    valores = []

    for cantidad in coincidencias:
        porcentaje = float(cantidad.replace(",", "."))

        if 0 < porcentaje <= 100:
            valores.append(porcentaje)

    valores_unicos = sorted(set(valores))

    if len(valores_unicos) == 1:
        return {
            "estado": "Detectado",
            "valor": f"{valores_unicos[0]:g}% Alc. Vol."
        }

    if len(valores_unicos) > 1:
        return {
            "estado": "Revisión manual",
            "valor": ", ".join(
                f"{valor:g}%"
                for valor in valores_unicos
            )
        }

    if confianza_ocr is not None and confianza_ocr < 60:
        return {
            "estado": "Baja legibilidad",
            "valor": None
        }

    return {
        "estado": "No localizado",
        "valor": None
    }