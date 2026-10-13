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
    ET-01: Detectar la denominación TEQUILA
    como palabra completa.
    """

    if re.search(r"\bTEQUILA\b", texto_normalizado):
        return "Detectado"

    if confianza_ocr is not None and confianza_ocr < 60:
        return "Baja legibilidad"

    return "No localizado"


def detectar_categoria(
    texto_normalizado: str,
    confianza_ocr: Optional[float] = None
) -> dict:
    """
    ET-02: Identificar la categoría del tequila.
    No inferir categoría por ausencia de información.
    """

    texto = normalizar(texto_normalizado)

    patron_agave = (
        r"\b100\s*%\s*"
        r"(?:DE\s*)?AGAVE\b"
    )

    if re.search(patron_agave, texto):
        return {
            "estado": "Detectado",
            "valor": "100% de agave"
        }

    if confianza_ocr is not None and confianza_ocr < 60:
        return {
            "estado": "Baja legibilidad",
            "valor": None
        }

    if re.search(r"\bTEQUILA\b", texto):
        return {
            "estado": "Revisión manual",
            "valor": None
        }

    return {
        "estado": "No localizado",
        "valor": None
    }


def detectar_clase(
    texto_normalizado: str,
    confianza_ocr: Optional[float] = None
) -> dict:
    """
    ET-03: Detectar la clase del tequila.
    Evita coincidencias parciales y detecta
    clases diferentes en un mismo análisis.
    """

    texto = normalizar(texto_normalizado)

    patrones = [
        (r"\bEXTRA\s+ANEJO\b", "Extra añejo"),
        (r"\bREPOSADO\b", "Reposado"),
        (r"\bANEJO\b", "Añejo"),
        (r"\bBLANCO\b|\bPLATA\b", "Blanco"),
        (r"\bJOVEN\b|\bORO\b", "Joven"),
    ]

    encontrados = []

    for patron, clase in patrones:
        if re.search(patron, texto):
            encontrados.append(clase)

    # EXTRA AÑEJO no debe contarse también como AÑEJO.
    if "Extra añejo" in encontrados and "Añejo" in encontrados:
        encontrados.remove("Añejo")

    if len(encontrados) == 1:
        return {
            "estado": "Detectado",
            "valor": encontrados[0]
        }

    if len(encontrados) > 1:
        return {
            "estado": "Revisión manual",
            "valor": ", ".join(encontrados)
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


def detectar_contenido_neto(
    texto_normalizado: str,
    confianza_ocr: Optional[float] = None
) -> dict:
    """
    ET-05: Detectar contenido neto.

    Ejemplos:
    750 ML
    700 ML
    1 L
    1.5 L

    Evita coincidencias parciales como ML2026.
    """

    texto = normalizar(texto_normalizado)

    patron = (
        r"(?<![A-Z0-9])"
        r"(\d{1,4}(?:[.,]\d{1,3})?)"
        r"\s*(ML|LITROS?|L)"
        r"(?![A-Z0-9])"
    )

    coincidencias = re.findall(patron, texto)

    valores = []

    for cantidad, unidad in coincidencias:
        numero = float(cantidad.replace(",", "."))

        if unidad in ("L", "LITRO", "LITROS"):
            mililitros = numero * 1000
        else:
            mililitros = numero

        if 50 <= mililitros <= 5000:
            valores.append(mililitros)

    valores_unicos = sorted(set(valores))

    if len(valores_unicos) == 1:
        return {
            "estado": "Detectado",
            "valor": f"{valores_unicos[0]:g} mL"
        }

    if len(valores_unicos) > 1:
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
    ET-07: Detecta graduación alcohólica.

    Formatos aceptados:
    - 40% Alc. Vol.
    - 38 % ALC/VOL
    - 35% VOL
    - 40% DE ALCOHOL

    Evita coincidencias parciales como:
    - 40% ALC/VOL2026
    """

    texto = normalizar(texto_normalizado)

    patron = (
        r"(?<![A-Z0-9])"
        r"(\d{1,2}(?:[.,]\d{1,2})?)"
        r"\s*%\s*"
        r"(?:"
        r"ALC\.?\s*[/.-]?\s*VOL\.?"
        r"|VOL\.?"
        r"|DE\s+ALCOHOL"
        r")"
        r"(?![A-Z0-9])"
    )

    coincidencias = re.findall(patron, texto)

    valores = []

    for cantidad in coincidencias:
        numero = float(cantidad.replace(",", "."))

        if 0 < numero <= 100:
            valores.append(numero)

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
                f"{valor:g}% Alc. Vol."
                for valor in valores_unicos
            )
        }
        # Posible confusión OCR entre VOL y VAL.
    # Recuperamos el porcentaje, pero exigimos revisión manual.
    patron_val = (
        r"(?<![A-Z0-9])"
        r"(\d{1,2}(?:[.,]\d{1,2})?)"
        r"\s*%\s*"
        r"ALC\.?\s*[/.-]?\s*VAL\.?"
        r"(?![A-Z0-9])"
    )

    coincidencias_val = re.findall(patron_val, texto)

    if coincidencias_val:
        valores_val = sorted({
            float(valor.replace(",", "."))
            for valor in coincidencias_val
            if 0 < float(valor.replace(",", ".")) <= 100
        })

        if valores_val:
            return {
                "estado": "Revisión manual",
                "valor": ", ".join(
                    f"{valor:g}% Alc. Val. (verificar en fotografía)"
                    for valor in valores_val
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
