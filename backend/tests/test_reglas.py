from app.services.reglas import normalizar, detectar_denominacion


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