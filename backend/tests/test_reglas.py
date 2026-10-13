
from app.services.reglas import (
    normalizar,
    detectar_denominacion,
    detectar_categoria,
    detectar_contenido_neto,
    detectar_clase,
    detectar_graduacion_alcoholica,
)


# ==========================================
# NORMALIZACION
# ==========================================

def test_normalizar_quita_acentos_y_espacios():
    assert normalizar("  Hecho   en México ") == "HECHO EN MEXICO"


# ==========================================
# ET-01: DENOMINACION
# ==========================================

def test_detecta_tequila():
    assert detectar_denominacion(
        normalizar("Tequila Reposado")
    ) == "Detectado"


def test_denominacion_palabra_completa():
    assert detectar_denominacion("TEQUILA") == "Detectado"
    assert detectar_denominacion("TEQUILA REPOSADO") == "Detectado"
    assert detectar_denominacion("NOTEQUILA") == "No localizado"
    assert detectar_denominacion("TEQUILAZO") == "No localizado"


def test_denominacion_baja_legibilidad():
    assert detectar_denominacion(
        "ETIQUETA ILEGIBLE",
        confianza_ocr=35
    ) == "Baja legibilidad"


# ==========================================
# ET-02: CATEGORIA
# ==========================================

def test_categoria_100_agave():
    variantes = [
        "TEQUILA 100% DE AGAVE",
        "TEQUILA 100 % AGAVE",
        "100% AGAVE",
        "100 % DE AGAVE",
    ]

    for texto in variantes:
        resultado = detectar_categoria(texto)

        assert resultado["estado"] == "Detectado"
        assert resultado["valor"] == "100% de agave"


def test_categoria_sin_declaracion():
    resultado = detectar_categoria("TEQUILA REPOSADO")

    assert resultado["estado"] == "Revisión manual"
    assert resultado["valor"] is None


def test_categoria_baja_legibilidad():
    resultado = detectar_categoria(
        "T3QU1LA",
        confianza_ocr=35
    )

    assert resultado["estado"] == "Baja legibilidad"


def test_categoria_no_localizada():
    resultado = detectar_categoria(
        "PRODUCTO SIN INFORMACION"
    )

    assert resultado["estado"] == "No localizado"


# ==========================================
# ET-03: CLASE
# ==========================================

def test_clases_tequila():
    casos = {
        "TEQUILA BLANCO": "Blanco",
        "TEQUILA PLATA": "Blanco",
        "TEQUILA ORO": "Joven",
        "TEQUILA JOVEN": "Joven",
        "TEQUILA REPOSADO": "Reposado",
        "TEQUILA AÑEJO": "Añejo",
        "TEQUILA EXTRA AÑEJO": "Extra añejo",
    }

    for texto, esperado in casos.items():
        resultado = detectar_clase(texto)

        assert resultado["estado"] == "Detectado"
        assert resultado["valor"] == esperado


def test_clases_diferentes():
    resultado = detectar_clase(
        "TEQUILA BLANCO REPOSADO"
    )

    assert resultado["estado"] == "Revisión manual"


def test_clase_sin_coincidencia_parcial():
    resultado = detectar_clase(
        "PRODUCTO REPOSADOS"
    )

    assert resultado["estado"] == "No localizado"


# ==========================================
# ET-05: CONTENIDO NETO
# ==========================================

def test_contenido_neto_mililitros():
    resultado = detectar_contenido_neto(
        normalizar("Contenido neto 750 ml"),
        confianza_ocr=85
    )

    assert resultado["estado"] == "Detectado"
    assert resultado["valor"] == "750 mL"


def test_contenido_neto_litros():
    resultado = detectar_contenido_neto(
        normalizar("Contenido 1 L"),
        confianza_ocr=85
    )

    assert resultado["valor"] == "1000 mL"


def test_contenido_neto_abreviado():
    resultado = detectar_contenido_neto(
        normalizar("Cont. Net. 700 ml"),
        confianza_ocr=85
    )

    assert resultado["estado"] == "Detectado"
    assert resultado["valor"] == "700 mL"


def test_contenidos_netos_diferentes():
    resultado = detectar_contenido_neto(
        normalizar("Contenido neto 750 ml y 1 L"),
        confianza_ocr=85
    )

    assert resultado["estado"] == "Revisión manual"
    assert "750 mL" in resultado["valor"]
    assert "1000 mL" in resultado["valor"]


def test_contenido_neto_no_coincidencia_parcial():
    resultado = detectar_contenido_neto(
        normalizar("LOTE 750 ML2026"),
        confianza_ocr=85
    )

    assert resultado["estado"] == "No localizado"


# ==========================================
# ET-07: GRADUACION ALCOHOLICA
# ==========================================

def test_graduacion_alcoholica():
    resultado = detectar_graduacion_alcoholica(
        normalizar("40% Alc. Vol."),
        confianza_ocr=85
    )

    assert resultado["estado"] == "Detectado"
    assert resultado["valor"] == "40% Alc. Vol."


def test_no_confundir_agave_con_alcohol():
    resultado = detectar_graduacion_alcoholica(
        normalizar("100% de agave"),
        confianza_ocr=85
    )

    assert resultado["estado"] == "No localizado"


def test_graduaciones_diferentes():
    resultado = detectar_graduacion_alcoholica(
        normalizar("38% Alc. Vol. y 40% Alc. Vol."),
        confianza_ocr=85
    )

    assert resultado["estado"] == "Revisión manual"




def test_graduacion_formatos_adicionales():
    casos = [
        ("38 % ALC/VOL", "38% Alc. Vol."),
        ("35% VOL", "35% Alc. Vol."),
        ("40% de alcohol", "40% Alc. Vol."),
    ]

    for texto, esperado in casos:
        resultado = detectar_graduacion_alcoholica(
            normalizar(texto),
            confianza_ocr=85
        )

        assert resultado["estado"] == "Detectado"
        assert resultado["valor"] == esperado


def test_graduacion_no_coincidencia_parcial():
    resultado = detectar_graduacion_alcoholica(
        normalizar("40% ALC/VOL2026"),
        confianza_ocr=85
    )

    assert resultado["estado"] == "No localizado"


def test_graduacion_baja_legibilidad():
    resultado = detectar_graduacion_alcoholica(
        normalizar("ETIQUETA BORROSA"),
        confianza_ocr=35
    )

    assert resultado["estado"] == "Baja legibilidad"


def test_graduacion_valores_iguales():
    resultado = detectar_graduacion_alcoholica(
        normalizar("40% Alc. Vol. 40% Alc. Vol."),
        confianza_ocr=85
    )

    assert resultado["estado"] == "Detectado"
    assert resultado["valor"] == "40% Alc. Vol."
