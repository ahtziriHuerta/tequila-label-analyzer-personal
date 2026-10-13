from app.services.reglas import (
    normalizar,
    detectar_denominacion,
    detectar_categoria,
    detectar_contenido_neto,
    detectar_clase,
    detectar_graduacion_alcoholica,
)

def test_normalizar_quita_acentos_y_espacios():
    assert normalizar("  Hecho   en México ") == "HECHO EN MEXICO"


def test_detecta_tequila():
    assert detectar_denominacion(normalizar("Tequila Reposado")) == "Detectado"

from app.services.reglas import (
    detectar_contenido_neto,
    detectar_graduacion_alcoholica,
)


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
    resultado = detectar_clase("TEQUILA BLANCO REPOSADO")

    assert resultado["estado"] == "Revisión manual"


def test_clase_sin_coincidencia_parcial():
    resultado = detectar_clase("PRODUCTO REPOSADOS")

    assert resultado["estado"] == "No localizado"