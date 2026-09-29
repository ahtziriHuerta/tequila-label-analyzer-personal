"""Motor de reglas (matriz ET-01..ET-18). Estados permitidos:
Detectado, No localizado, Imagen adicional requerida, Baja legibilidad, Revisión manual.
Regla clave: una lectura fallida NUNCA equivale a incumplimiento (RNF-07).
"""
import re

ESTADOS = ["Detectado", "No localizado", "Imagen adicional requerida", "Baja legibilidad", "Revisión manual"]


def normalizar(texto: str) -> str:
    """RF-07: mayúsculas, sin acentos, espacios uniformes (conservar el texto original aparte)."""
    import unicodedata
    t = unicodedata.normalize("NFD", texto.upper())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", t).strip()


def detectar_denominacion(texto_normalizado: str) -> str:
    """ET-01: buscar la palabra TEQUILA."""
    return "Detectado" if "TEQUILA" in texto_normalizado else "No localizado"
