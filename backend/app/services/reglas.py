"""Motor de reglas para análisis de etiquetado.

Los requisitos siguen el formato del Consejo Regulador del Tequila
"Requisitos de etiquetado para la NOM-006-SCFI-2012" (MO-RV/20) y las
normas a las que remite:

- NOM-006-SCFI-2012  Tequila (cap. 5 categorías y clases, cap. 11 etiquetado).
- NOM-030-SCFI-2006  Declaración de cantidad (unidades del contenido neto).
- NOM-142-SSA1/SCFI-2014  Etiquetado sanitario (alcohol, domicilio, lote,
  leyenda precautoria, símbolos e ingredientes).
- NOM-106-SCFI-2017  Diseño de la contraseña oficial NOM.

Las detecciones son automáticas y sirven de apoyo: ningún estado
significa "no cumple". El dictamen (SÍ / NO / N/A) lo da el inspector.
"""

import re
import unicodedata
from difflib import SequenceMatcher
from typing import Optional


ESTADOS = [
    "Detectado",
    "No localizado",
    "Imagen adicional requerida",
    "Baja legibilidad",
    "Revisión manual",
    # El requisito no aplica según los datos declarados
    # (p. ej. saborizantes cuando el producto no los lleva).
    "No aplica",
]

# Por debajo de esta confianza del OCR, un dato no encontrado
# se reporta como "Baja legibilidad" y no como "No localizado".
CONFIANZA_MINIMA = 60


# ==========================================
# CATÁLOGO: FORMATO MO-RV/20 DEL CRT
# ==========================================
# seccion: "apartado11" (Apartado 11 de la norma) u "otras"
#          (Otras disposiciones obligatorias, NOM-142).
# superficie: destinos en los que el dato debe aparecer en la
#          superficie principal de exhibición (marcas + y ° del formato;
#          NOM-006 11.2.1). Se revisa con la foto de la vista "frontal".

REQUISITOS = {
    "ET-01": {
        "requisito": 'Palabra "Tequila"',
        "seccion": "apartado11",
        "fundamento": "NOM-006 11.1 a)",
        "superficie": {"nacional", "exportacion"},
    },
    "ET-02": {
        "requisito": "Categoría",
        "seccion": "apartado11",
        "fundamento": "NOM-006 5.1, 11.1 b)",
        "superficie": {"nacional", "exportacion"},
    },
    "ET-03": {
        "requisito": "Clase",
        "seccion": "apartado11",
        "fundamento": "NOM-006 5.2, 11.1 b)",
        "superficie": {"nacional", "exportacion"},
    },
    "ET-04": {
        "requisito": "Saborizante o colorante",
        "seccion": "apartado11",
        "fundamento": "NOM-006 6.1.1.1, 11.1 c)",
        "superficie": {"nacional", "exportacion"},
    },
    "ET-05": {
        "requisito": "Contenido neto",
        "seccion": "apartado11",
        "fundamento": "NOM-006 11.1 d); NOM-030 4.1, 4.4, Tabla 3",
        "superficie": {"nacional"},
    },
    "ET-07": {
        "requisito": "Contenido alcohólico (% Alc. Vol.)",
        "seccion": "apartado11",
        "fundamento": "NOM-006 11.1 e), Tabla 1; NOM-142 9.3.6.1",
        "superficie": {"nacional"},
    },
    "ET-08": {
        "requisito": "Nombre o razón social",
        "seccion": "apartado11",
        "fundamento": "NOM-006 11.1 f)",
        "superficie": set(),
    },
    "ET-09": {
        "requisito": "Domicilio",
        "seccion": "apartado11",
        "fundamento": "NOM-006 11.1 g); NOM-142 9.3.2.1",
        "superficie": set(),
    },
    "ET-10": {
        "requisito": "Marca registrada",
        "seccion": "apartado11",
        "fundamento": "NOM-006 11.1 h)",
        "superficie": {"nacional", "exportacion"},
    },
    "ET-11": {
        "requisito": "Hecho en México",
        "seccion": "apartado11",
        "fundamento": "NOM-006 11.1 i); NOM-142 9.3.3.1",
        "superficie": set(),
    },
    "ET-12": {
        "requisito": "Contraseña oficial (NOM)",
        "seccion": "apartado11",
        "fundamento": "NOM-006 10.4, 11.1 j); NOM-106-SCFI-2017",
        "superficie": set(),
    },
    "ET-13": {
        "requisito": "Lote",
        "seccion": "apartado11",
        "fundamento": "NOM-006 11.1 k); NOM-142 9.3.4",
        "superficie": set(),
    },
    "ET-14": {
        "requisito": "Leyenda precautoria",
        "seccion": "apartado11",
        "fundamento": "NOM-142 9.3.7.2.1",
        "superficie": set(),
    },
    "ET-19": {
        "requisito": "Lista de ingredientes",
        "seccion": "otras",
        "fundamento": "NOM-142 9.3.7.1",
        "superficie": set(),
    },
    "ET-15": {
        "requisito": "Símbolos",
        "seccion": "otras",
        "fundamento": "NOM-142 9.3.7.2.4, Apéndice A",
        "superficie": set(),
    },
}

# Valores fijos que se eligen en el formato (deben coincidir con frontend/js/catalogos.js).
CATEGORIAS = ("100% de agave", "Tequila")
CLASES = ("Blanco", "Joven", "Reposado", "Añejo", "Extra añejo")
DESTINOS = ("nacional", "exportacion")
ADITIVOS = ("si", "no", "no_se")

# NOM-006 Tabla 1: el tequila se envasa entre 35 y 55 % Alc. Vol.
ALCOHOL_MINIMO = 35
ALCOHOL_MAXIMO = 55

LEYENDA_PRECAUTORIA = (
    "EL ABUSO EN EL CONSUMO DE ESTE PRODUCTO ES NOCIVO PARA LA SALUD"
)


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


def compactar(texto: str) -> str:
    """Solo letras y números: tolera espacios y signos que el OCR pierde."""

    return re.sub(r"[^A-Z0-9]", "", normalizar(texto))


def sin_texto(confianza_ocr: Optional[float]) -> dict:
    """Resultado cuando no se encontró el dato."""

    if confianza_ocr is not None and confianza_ocr < CONFIANZA_MINIMA:
        return {"estado": "Baja legibilidad", "valor": None}

    return {"estado": "No localizado", "valor": None}


# ==========================================
# ET-01: PALABRA "TEQUILA"
# ==========================================

# "Tequila" también aparece en el domicilio (Tequila, Jalisco) y en el
# nombre del Consejo; esas menciones no son la denominación.
_TEQUILA_NO_DENOMINACION = (
    r"\bTEQUILA\s*,?\s*JAL(?:ISCO)?\b\.?"
    r"|\bCONSEJO\s+REGULADOR\s+DEL\s+TEQUILA\b"
)


def detectar_denominacion(
    texto_normalizado: str,
    confianza_ocr: Optional[float] = None
) -> str:
    """
    ET-01: Detectar la denominación TEQUILA
    como palabra completa.
    """

    texto = re.sub(_TEQUILA_NO_DENOMINACION, " ", texto_normalizado)

    if re.search(r"\bTEQUILA\b", texto):
        return "Detectado"

    if confianza_ocr is not None and confianza_ocr < CONFIANZA_MINIMA:
        return "Baja legibilidad"

    return "No localizado"


# ==========================================
# ET-02: CATEGORÍA
# ==========================================

def detectar_categoria(
    texto_normalizado: str,
    confianza_ocr: Optional[float] = None
) -> dict:
    """
    ET-02: Identificar la categoría del tequila.
    No inferir categoría por ausencia de información.

    NOM-006 5.1.1 admite cuatro leyendas para el 100 %:
    "100% de agave", "100% puro de agave", "100% agave"
    y "100% puro agave" (puede añadirse "azul").
    Si no es 100 %, la categoría es solo "Tequila".
    """

    texto = normalizar(texto_normalizado)

    patron_agave = (
        r"\b100\s*%\s*"
        r"(?:PURO\s*)?"
        r"(?:DE\s*)?AGAVE\b"
    )

    if re.search(patron_agave, texto):
        return {
            "estado": "Detectado",
            "valor": "100% de agave"
        }

    if confianza_ocr is not None and confianza_ocr < CONFIANZA_MINIMA:
        return {
            "estado": "Baja legibilidad",
            "valor": None
        }

    # Sin la leyenda 100 % puede ser un tequila (mixto):
    # se decide con la categoría declarada o por el revisor.
    if re.search(r"\bTEQUILA\b", texto):
        return {
            "estado": "Revisión manual",
            "valor": None
        }

    return {
        "estado": "No localizado",
        "valor": None
    }


# ==========================================
# ET-03: CLASE
# ==========================================

# Del más específico al más general: cada coincidencia se retira del
# texto para que "EXTRA AÑEJO" no cuente también como "AÑEJO".
# Exportación (NOM-006 5.2.2): Silver, Gold, Aged, Extra aged, Ultra aged.
_PATRONES_CLASE = [
    (r"\bEXTRA\s*ANEJO\b", "Extra añejo"),
    (r"\bULTRA\s*AGED\b", "Extra añejo"),
    (r"\bEXTRA\s*AGED\b", "Añejo"),
    (r"\bREPOSADO\b", "Reposado"),
    (r"\bANEJO\b", "Añejo"),
    (r"\bAGED\b", "Reposado"),
    (r"\bBLANCO\b|\bPLATA\b|\bSILVER\b", "Blanco"),
    (r"\bJOVEN\b|\bORO\b|\bGOLD\b", "Joven"),
]


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

    encontrados = []

    for patron, clase in _PATRONES_CLASE:
        if re.search(patron, texto):
            if clase not in encontrados:
                encontrados.append(clase)
            texto = re.sub(patron, " ", texto)

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

    return sin_texto(confianza_ocr)


# ==========================================
# ET-04: SABORIZANTE O COLORANTE
# ==========================================

def detectar_saborizante(
    texto_normalizado: str,
    confianza_ocr: Optional[float] = None,
    aditivos: Optional[str] = None
) -> dict:
    """
    ET-04: Leyenda de saborizantes, aromatizantes o colorantes.

    Solo aplica si el producto los lleva (NOM-006 6.1.1.1, 11.1 c),
    algo que la foto no puede saber: depende de lo declarado.
    """

    if aditivos == "no":
        return {
            "estado": "No aplica",
            "valor": None,
            "observacion": "Se declaró sin saborizantes ni colorantes.",
        }

    texto = normalizar(texto_normalizado)

    encontrados = re.findall(
        r"\b(SABORIZAD\w*|SABORIZANTE\w*|SABOR\b|AROMA\w*|COLORANTE\w*|"
        r"COLOR\s+CARAMELO|ABOCADO|EDULCORANTE\w*)",
        texto
    )

    if encontrados:
        return {
            "estado": "Detectado",
            "valor": ", ".join(sorted(set(encontrados))),
        }

    resultado = sin_texto(confianza_ocr)

    if aditivos == "si":
        resultado["observacion"] = (
            "Se declaró que lleva aditivos: la etiqueta debe indicarlo."
        )
        return resultado

    return {
        "estado": "Revisión manual",
        "valor": None,
        "observacion": (
            "Solo aplica si lleva saborizantes o colorantes: "
            "indícalo en los datos del producto."
        ),
    }


# ==========================================
# ET-05: CONTENIDO NETO
# ==========================================

# NOM-030 Tabla 3: el símbolo es mL/ml o L/l, sin plural ni punto.
_UNIDADES_VALIDAS = {"ML", "L"}


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
    Revisa el formato de NOM-030: menos de 1 L se escribe
    en mL y de 1 L en adelante en L (4.4.1, 4.4.2).
    """

    texto = normalizar(texto_normalizado)

    patron = (
        r"(?<![A-Z0-9])"
        r"(\d{1,4}(?:[.,]\d{1,3})?)"
        r"\s*(MLS?|LITROS?|LTS?|CL|L)"
        r"(?![A-Z0-9])"
    )

    coincidencias = re.findall(patron, texto)

    valores = []
    observaciones = []

    for cantidad, unidad in coincidencias:
        numero = float(cantidad.replace(",", "."))

        if unidad.startswith("M"):
            mililitros = numero
        elif unidad == "CL":
            mililitros = numero * 10
        else:
            mililitros = numero * 1000

        if not 50 <= mililitros <= 5000:
            continue

        valores.append(mililitros)

        if unidad not in _UNIDADES_VALIDAS:
            observaciones.append(
                f"El símbolo «{unidad}» no es de la Tabla 3 de NOM-030 (usar mL o L)."
            )
        elif unidad == "L" and mililitros < 1000:
            observaciones.append(
                "Menos de 1 L se declara en mL (NOM-030 4.4.1)."
            )
        elif unidad == "ML" and mililitros >= 1000:
            observaciones.append(
                "De 1 L en adelante se declara en L (NOM-030 4.4.2)."
            )

    valores_unicos = sorted(set(valores))

    if not valores_unicos:
        return sin_texto(confianza_ocr)

    resultado = {
        "estado": "Detectado" if len(valores_unicos) == 1 else "Revisión manual",
        "valor": ", ".join(f"{valor:g} mL" for valor in valores_unicos),
    }

    if observaciones:
        resultado["estado"] = "Revisión manual"
        resultado["observacion"] = " ".join(sorted(set(observaciones)))

    return resultado


# ==========================================
# ET-07: CONTENIDO ALCOHÓLICO
# ==========================================

def _porcentajes(patron: str, texto: str) -> list:
    return sorted({
        float(valor.replace(",", "."))
        for valor in re.findall(patron, texto)
        if 0 < float(valor.replace(",", ".")) <= 100
    })


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

    Un valor fuera de 35–55 % (NOM-006 Tabla 1) se toma como
    probable error de lectura, no como incumplimiento.
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

    valores_unicos = _porcentajes(patron, texto)

    if valores_unicos:
        en_rango = [
            v for v in valores_unicos
            if ALCOHOL_MINIMO <= v <= ALCOHOL_MAXIMO
        ]

        if not en_rango:
            return {
                "estado": "Baja legibilidad",
                "valor": ", ".join(f"{v:g}% Alc. Vol." for v in valores_unicos),
                "observacion": (
                    f"Fuera de {ALCOHOL_MINIMO}–{ALCOHOL_MAXIMO} % (NOM-006 Tabla 1): "
                    "probable error de lectura; verificar en la fotografía."
                ),
            }

        resultado = {
            "estado": "Detectado" if len(valores_unicos) == 1 else "Revisión manual",
            "valor": ", ".join(f"{v:g}% Alc. Vol." for v in valores_unicos),
        }

        # NOM-142 9.3.6.1 enumera las abreviaturas "% Alc. Vol." y variantes.
        if not re.search(r"%\s*ALC\.?\s*[/.-]?\s*VOL", texto):
            resultado["observacion"] = (
                "La abreviatura no es «% Alc. Vol.» (NOM-142 9.3.6.1)."
            )

        return resultado

    # Posible confusión OCR entre VOL y VAL.
    # Recuperamos el porcentaje, pero exigimos revisión manual.
    patron_val = (
        r"(?<![A-Z0-9])"
        r"(\d{1,2}(?:[.,]\d{1,2})?)"
        r"\s*%\s*"
        r"ALC\.?\s*[/.-]?\s*VAL\.?"
        r"(?![A-Z0-9])"
    )

    valores_val = _porcentajes(patron_val, texto)

    if valores_val:
        return {
            "estado": "Revisión manual",
            "valor": ", ".join(
                f"{valor:g}% Alc. Val. (verificar en fotografía)"
                for valor in valores_val
            )
        }

    # Posible omisión de la letra L por parte del OCR:
    # "38% Ac Vol." en lugar de "38% Alc. Vol."
    patron_ac_vol = (
        r"(?<![A-Z0-9])"
        r"(\d{1,2}(?:[.,]\d{1,2})?)"
        r"\s*%\s*"
        r"AC\.?\s*[/.-]?\s*VOL\.?"
        r"(?![A-Z0-9])"
    )

    valores_ac_vol = _porcentajes(patron_ac_vol, texto)

    if valores_ac_vol:
        return {
            "estado": "Revisión manual",
            "valor": ", ".join(
                f"{valor:g}% Ac. Vol. (verificar en fotografía)"
                for valor in valores_ac_vol
            )
        }

    return sin_texto(confianza_ocr)


# ==========================================
# ET-08: NOMBRE O RAZÓN SOCIAL
# ==========================================

_PRESENTACION_PRODUCTOR = (
    r"(?:ELABORADO|PRODUCIDO|ENVASADO|DESTILADO|EMBOTELLADO|FABRICADO)"
    r"(?:\s*Y\s*(?:ENVASADO|EMBOTELLADO))?\s*(?:POR|EN)\b"
)

_SOCIEDAD = (
    r"\bS\.?\s*A\.?\s*(?:P\.?\s*I\.?\s*)?(?:DE|D)\s*C\.?\s*V\b\.?"
    r"|\bS\.?\s*(?:P\.?\s*R\.?\s*)?DE\s*R\.?\s*L\b\.?(?:\s*(?:DE|D)\s*C\.?\s*V\b\.?)?"
    r"|\bS\.?\s*C\.?\s*DE\s*R\.?\s*L\b\.?"
    r"|\bS\.?\s*A\.?\s*S\b\.?"
)


def detectar_razon_social(
    texto_normalizado: str,
    confianza_ocr: Optional[float] = None
) -> dict:
    """
    ET-08: "Elaborado por / Envasado por" y la razón social
    (S.A. de C.V., S. de R.L., S.A.P.I. de C.V., ...).
    """

    texto = normalizar(texto_normalizado)

    completo = re.search(
        _PRESENTACION_PRODUCTOR + r"\s*:?\s*(.{3,100}?(?:" + _SOCIEDAD + r"))",
        texto
    )

    if completo:
        return {
            "estado": "Detectado",
            "valor": completo.group(1).strip(" ,.;:"),
        }

    sociedad = re.search(r"(.{0,60}?)(" + _SOCIEDAD + r")", texto)

    if sociedad:
        return {
            "estado": "Revisión manual",
            "valor": (sociedad.group(1) + sociedad.group(2)).strip(" ,.;:"),
            "observacion": "Se leyó una razón social sin «Elaborado/Envasado por».",
        }

    if re.search(_PRESENTACION_PRODUCTOR, texto):
        return {
            "estado": "Revisión manual",
            "valor": None,
            "observacion": "Se leyó «Elaborado/Envasado por», pero no la razón social.",
        }

    return sin_texto(confianza_ocr)


# ==========================================
# ET-09: DOMICILIO
# ==========================================

_ESTADOS_MEXICO = (
    "AGUASCALIENTES|BAJA CALIFORNIA(?: SUR)?|CAMPECHE|CHIAPAS|CHIHUAHUA|"
    "CIUDAD DE MEXICO|CDMX|COAHUILA|COLIMA|DURANGO|ESTADO DE MEXICO|"
    "GUANAJUATO|GUERRERO|HIDALGO|JALISCO|JAL\\.|MICHOACAN|MORELOS|NAYARIT|"
    "NUEVO LEON|OAXACA|PUEBLA|QUERETARO|QUINTANA ROO|SAN LUIS POTOSI|"
    "SINALOA|SONORA|TABASCO|TAMAULIPAS|TLAXCALA|VERACRUZ|YUCATAN|ZACATECAS"
)


def detectar_domicilio(
    texto_normalizado: str,
    confianza_ocr: Optional[float] = None
) -> dict:
    """
    ET-09: Domicilio del productor o envasador.

    NOM-142 9.3.2.1 pide calle, número, código postal,
    ciudad y entidad federativa. Se buscan el código postal
    y la entidad; con solo uno de los dos, revisión manual.
    """

    texto = normalizar(texto_normalizado)

    codigo_postal = re.search(r"\bC\.?\s*P\.?\s*:?\s*(\d{5})\b", texto)
    entidad = re.search(r"\b(" + _ESTADOS_MEXICO + r")", texto)

    partes = []
    if codigo_postal:
        partes.append(f"C.P. {codigo_postal.group(1)}")
    if entidad:
        partes.append(entidad.group(1).title().rstrip("."))

    if codigo_postal and entidad:
        return {"estado": "Detectado", "valor": ", ".join(partes)}

    if partes:
        return {
            "estado": "Revisión manual",
            "valor": ", ".join(partes),
            "observacion": (
                "Domicilio incompleto en la lectura: debe incluir calle, número, "
                "C.P. y entidad (NOM-142 9.3.2.1)."
            ),
        }

    return sin_texto(confianza_ocr)


# ==========================================
# ET-10: MARCA REGISTRADA
# ==========================================

def detectar_marca(
    texto_normalizado: str,
    confianza_ocr: Optional[float] = None,
    marca: Optional[str] = None
) -> dict:
    """
    ET-10: La marca no tiene un patrón: se busca la marca
    declarada en los datos del producto.
    """

    if not marca or not compactar(marca):
        return {
            "estado": "Revisión manual",
            "valor": None,
            "observacion": "Captura la marca en los datos del producto para buscarla.",
        }

    buscada = compactar(marca)
    texto = compactar(texto_normalizado)

    if buscada in texto:
        return {"estado": "Detectado", "valor": marca.strip()}

    # Lectura aproximada (una letra mal leída en una marca de 6 letras ≈ 0,83).
    if len(buscada) >= 4 and len(texto) >= len(buscada):
        mejor = max(
            SequenceMatcher(None, buscada, texto[i:i + len(buscada)]).ratio()
            for i in range(len(texto) - len(buscada) + 1)
        )
        if mejor >= 0.8:
            return {
                "estado": "Revisión manual",
                "valor": marca.strip(),
                "observacion": "Coincidencia aproximada con la marca declarada.",
            }

    return sin_texto(confianza_ocr)


# ==========================================
# ET-11: HECHO EN MÉXICO
# ==========================================

def detectar_origen(
    texto_normalizado: str,
    confianza_ocr: Optional[float] = None
) -> dict:
    """
    ET-11: "Hecho en México" u otras análogas (NOM-006 11.1 i).
    Para exportación se aceptan "Product of Mexico" y "Made in Mexico".
    """

    texto = normalizar(texto_normalizado)

    origen = re.search(
        r"\b(?:HECHO|PRODUCTO|ELABORADO(?:\s*Y\s*ENVASADO)?|"
        r"MANUFACTURADO|FABRICADO|PRODUCIDO|ENVASADO)\s*(?:EN|DE)\s*MEXICO\b"
        r"|\bPRODUCT\s+OF\s+MEXICO\b|\bMADE\s+IN\s+MEXICO\b",
        texto
    )

    if origen:
        return {"estado": "Detectado", "valor": origen.group(0)}

    return sin_texto(confianza_ocr)


# ==========================================
# ET-12: CONTRASEÑA OFICIAL (NOM)
# ==========================================

def detectar_contrasena_nom(
    texto_normalizado: str,
    confianza_ocr: Optional[float] = None
) -> dict:
    """
    ET-12: Contraseña oficial NOM con el número de registro
    del productor (NOM-006 10.4). No confunde la clave de una
    norma ("NOM-006-SCFI") con el registro.
    """

    texto = normalizar(texto_normalizado)

    registro = re.search(
        r"\bNOM\s*[-:.]?\s*(\d{3,4})\b(?!\s*-?\s*(?:SCFI|SSA))",
        texto
    )

    if registro:
        return {
            "estado": "Detectado",
            "valor": f"NOM {registro.group(1)}",
            "observacion": (
                "Verificar el diseño en la foto: letras NOM de al menos 2,5 mm, "
                "en negro, gris o blanco, sin sombras (NOM-106-SCFI-2017)."
            ),
        }

    if re.search(r"\bNOM\b", texto):
        return {
            "estado": "Revisión manual",
            "valor": None,
            "observacion": "Se leyó «NOM» sin el número de registro.",
        }

    return sin_texto(confianza_ocr)


# ==========================================
# ET-13: LOTE
# ==========================================

def detectar_lote(
    texto_normalizado: str,
    confianza_ocr: Optional[float] = None
) -> dict:
    """
    ET-13: Clave de lote precedida de LOTE, LOT, LT o L
    (NOM-142 9.3.4.3). La "L" sola se acepta solo seguida
    de un dígito, para no tomar letras de otras palabras.
    No hay formato oficial de la clave.
    """

    texto = normalizar(texto_normalizado)

    lote = re.search(
        r"\b(?:LOTE|LOT|LT)\s*[:.#-]?\s*(?=[A-Z0-9]*\d)[A-Z0-9][A-Z0-9/-]{2,}"
        r"|\bL[:.-]?\d[A-Z0-9/-]{3,}\b",
        texto
    )

    if lote:
        return {"estado": "Detectado", "valor": lote.group(0).strip()}

    if re.search(r"\bLOTE\b", texto):
        return {
            "estado": "Revisión manual",
            "valor": None,
            "observacion": "Se leyó «Lote» sin una clave legible.",
        }

    return sin_texto(confianza_ocr)


# ==========================================
# ET-14: LEYENDA PRECAUTORIA
# ==========================================

def detectar_leyenda_precautoria(
    texto_normalizado: str,
    confianza_ocr: Optional[float] = None
) -> dict:
    """
    ET-14: Texto exacto de NOM-142 9.3.7.2.1; no puede
    modificarse (9.4.1.1). Se compara sin espacios para
    tolerar renglones partidos.
    """

    frase = compactar(LEYENDA_PRECAUTORIA)
    texto = compactar(texto_normalizado)

    if frase in texto:
        return {"estado": "Detectado", "valor": LEYENDA_PRECAUTORIA}

    if len(texto) >= len(frase):
        mejor = max(
            SequenceMatcher(None, frase, texto[i:i + len(frase)]).ratio()
            for i in range(0, len(texto) - len(frase) + 1, 2)
        )
        if mejor >= 0.85:
            return {
                "estado": "Revisión manual",
                "valor": LEYENDA_PRECAUTORIA,
                "observacion": "Lectura aproximada: confirmar que el texto sea exacto.",
            }

    if "ABUSO" in texto and "NOCIVO" in texto:
        return {
            "estado": "Baja legibilidad",
            "valor": None,
            "observacion": "Se leyó parte de la leyenda; confirmar el texto completo.",
        }

    return sin_texto(confianza_ocr)


# ==========================================
# ET-15: SÍMBOLOS
# ==========================================

def detectar_simbolos(
    texto_normalizado: str,
    confianza_ocr: Optional[float] = None
) -> dict:
    """
    ET-15: Pictogramas de menores de edad, embarazo y conducción.
    Son imágenes: siempre los confirma el revisor.
    """

    menores = re.search(r"-\s*18\b|\+\s*18\b|\b18\s*\+", normalizar(texto_normalizado))

    return {
        "estado": "Revisión manual",
        "valor": "«-18» leído" if menores else None,
        "observacion": (
            "Confirmar en la foto los 3 símbolos: juntos de al menos 7 mm "
            "(3,5 mm si el envase es de 500 mL o menos), NOM-142 Apéndice A."
        ),
    }


# ==========================================
# ET-19: LISTA DE INGREDIENTES
# ==========================================

def detectar_ingredientes(
    texto_normalizado: str,
    confianza_ocr: Optional[float] = None,
    aditivos: Optional[str] = None
) -> dict:
    """
    ET-19: Obligatoria si después de destilar se añadieron
    ingredientes o aditivos (NOM-142 9.3.7.1).
    """

    if aditivos == "no":
        return {
            "estado": "No aplica",
            "valor": None,
            "observacion": "Se declaró sin ingredientes ni aditivos añadidos.",
        }

    texto = normalizar(texto_normalizado)
    lista = re.search(r"\bINGREDIENTES?\s*:?\s*(.{0,80})", texto)

    if lista:
        return {"estado": "Detectado", "valor": lista.group(0).strip()}

    resultado = sin_texto(confianza_ocr)

    if aditivos == "si":
        resultado["observacion"] = (
            "Se declaró que lleva aditivos: debe llevar la lista de ingredientes."
        )
        return resultado

    return {
        "estado": "Revisión manual",
        "valor": None,
        "observacion": (
            "Solo aplica si se añadieron ingredientes o aditivos: "
            "indícalo en los datos del producto."
        ),
    }


# ==========================================
# EVALUACIÓN DE UN REQUISITO
# ==========================================

def evaluar(
    codigo: str,
    texto_normalizado: str,
    confianza_ocr: Optional[float] = None,
    datos: Optional[dict] = None
) -> dict:
    """
    Evalúa un requisito sobre un texto.
    Devuelve {"estado", "valor", "observacion"}.
    """

    datos = datos or {}
    aditivos = datos.get("aditivos")

    if codigo == "ET-01":
        estado = detectar_denominacion(texto_normalizado, confianza_ocr)
        resultado = {
            "estado": estado,
            "valor": "TEQUILA" if estado == "Detectado" else None,
        }
    elif codigo == "ET-04":
        resultado = detectar_saborizante(texto_normalizado, confianza_ocr, aditivos)
    elif codigo == "ET-10":
        resultado = detectar_marca(texto_normalizado, confianza_ocr, datos.get("marca"))
    elif codigo == "ET-19":
        resultado = detectar_ingredientes(texto_normalizado, confianza_ocr, aditivos)
    else:
        resultado = _DETECTORES[codigo](texto_normalizado, confianza_ocr)

    resultado.setdefault("observacion", None)
    return resultado


_DETECTORES = {
    "ET-02": detectar_categoria,
    "ET-03": detectar_clase,
    "ET-05": detectar_contenido_neto,
    "ET-07": detectar_graduacion_alcoholica,
    "ET-08": detectar_razon_social,
    "ET-09": detectar_domicilio,
    "ET-11": detectar_origen,
    "ET-12": detectar_contrasena_nom,
    "ET-13": detectar_lote,
    "ET-14": detectar_leyenda_precautoria,
    "ET-15": detectar_simbolos,
}


# ==========================================
# COMPARAR CON LOS DATOS DECLARADOS
# ==========================================

def _agregar_observacion(resultado: dict, texto: str) -> None:
    anterior = resultado.get("observacion")
    resultado["observacion"] = f"{anterior} {texto}" if anterior else texto


def comparar_con_declarado(codigo: str, resultado: dict, datos: Optional[dict]) -> dict:
    """
    Compara lo leído con lo que se capturó en el formato.
    Una diferencia pasa a "Revisión manual"; lo declarado
    nunca sustituye a lo leído.
    """

    datos = datos or {}
    valor = resultado.get("valor")

    if codigo == "ET-02" and datos.get("categoria"):
        declarada = datos["categoria"]

        if declarada == "Tequila" and valor is None and resultado["estado"] == "Revisión manual":
            # Tequila (mixto): la denominación sola es su categoría.
            resultado.update(estado="Detectado", valor="Tequila")
            _agregar_observacion(resultado, "Categoría «Tequila» (no 100 % de agave), según lo declarado.")
        elif declarada == "Tequila" and valor == "100% de agave":
            resultado["estado"] = "Revisión manual"
            _agregar_observacion(resultado, "Se declaró «Tequila», pero la etiqueta dice 100 % de agave.")
        elif declarada == "100% de agave" and valor is None:
            _agregar_observacion(resultado, "Se declaró 100 % de agave: la leyenda debe aparecer.")

    elif codigo == "ET-03" and datos.get("clase"):
        declarada = datos["clase"]

        if valor is None:
            _agregar_observacion(resultado, f"Declarada: {declarada}.")
        elif normalizar(valor) != normalizar(declarada):
            resultado["estado"] = "Revisión manual"
            _agregar_observacion(resultado, f"Declarada: {declarada}; en la etiqueta: {valor}.")

    elif codigo == "ET-05" and datos.get("contenido_ml"):
        declarado = float(datos["contenido_ml"])
        texto_declarado = f"{declarado:g} mL"

        if valor is None:
            _agregar_observacion(resultado, f"Declarado: {texto_declarado}.")
        elif valor != texto_declarado:
            resultado["estado"] = "Revisión manual"
            _agregar_observacion(resultado, f"Declarado: {texto_declarado}; en la etiqueta: {valor}.")

    elif codigo == "ET-07" and datos.get("alcohol"):
        declarado = float(datos["alcohol"])
        leidos = [
            float(n) for n in re.findall(r"(\d+(?:\.\d+)?)%", valor or "")
        ]

        if not leidos:
            _agregar_observacion(resultado, f"Declarado: {declarado:g}% Alc. Vol.")
        elif any(abs(n - declarado) > 0.05 for n in leidos):
            resultado["estado"] = "Revisión manual"
            _agregar_observacion(resultado, f"Declarado: {declarado:g}% Alc. Vol.; en la etiqueta: {valor.rstrip('.')}.")

    return resultado


# ==========================================
# SUPERFICIE PRINCIPAL DE EXHIBICIÓN
# ==========================================

def revisar_superficie_principal(
    codigo: str,
    resultado: dict,
    imagenes_con_dato: list,
    vistas: Optional[list],
    destino: Optional[str]
) -> dict:
    """
    NOM-006 11.2.1 y marcas +/° del formato: ciertos datos deben
    estar en la superficie principal (la foto de la vista "frontal").

    imagenes_con_dato: números de foto (1, 2, ...) donde se leyó.
    vistas: vista de cada foto, en el mismo orden (o None).
    """

    if (
        not destino
        or not vistas
        or destino not in REQUISITOS[codigo]["superficie"]
        or resultado["estado"] != "Detectado"
    ):
        return resultado

    frontales = {
        indice + 1 for indice, vista in enumerate(vistas) if vista == "frontal"
    }

    if not frontales:
        _agregar_observacion(
            resultado,
            "Falta la foto frontal para confirmar que está en la superficie principal."
        )
    elif not frontales & set(imagenes_con_dato):
        resultado["estado"] = "Revisión manual"
        _agregar_observacion(
            resultado,
            "Se leyó fuera de la foto frontal: debe estar en la superficie "
            "principal de exhibición (NOM-006 11.2.1)."
        )

    return resultado
