
"""Pruebas del analizador multimagen y su trazabilidad."""

from unittest.mock import patch

from app.services.analizador import analizar_imagenes


def crear_resultado_ocr(texto, confianza=85):
    return {
        "texto": texto,
        "confianza": confianza,
        "version": "original",
        "psm": 11,
        "puntuacion": confianza,
    }


def test_evidencias_en_fotografias_diferentes():

    resultados_simulados = [
        crear_resultado_ocr(
            "TEQUILA REPOSADO"
        ),
        crear_resultado_ocr(
            "Contenido neto 750 ml"
        ),
        crear_resultado_ocr(
            "40% Alc. Vol."
        ),
    ]

    with patch(
        "app.services.analizador.extraer_texto",
        side_effect=resultados_simulados
    ):

        resultado = analizar_imagenes([
            "frontal.jpg",
            "posterior.jpg",
            "lateral.jpg",
        ])

    assert resultado["reglas"]["ET-01"]["estado"] == "Detectado"
    assert resultado["reglas"]["ET-03"]["valor"] == "Reposado"
    assert resultado["reglas"]["ET-05"]["valor"] == "750 mL"
    assert resultado["reglas"]["ET-07"]["valor"] == "40% Alc. Vol."

    assert resultado["evidencias"]["ET-01"][0]["numero_imagen"] == 1
    assert resultado["evidencias"]["ET-03"][0]["numero_imagen"] == 1
    assert resultado["evidencias"]["ET-05"][0]["numero_imagen"] == 2
    assert resultado["evidencias"]["ET-07"][0]["numero_imagen"] == 3


def test_sin_evidencia_no_inventa_valores():

    with patch(
        "app.services.analizador.extraer_texto",
        return_value=crear_resultado_ocr(
            "Texto ilegible",
            confianza=30
        )
    ):

        resultado = analizar_imagenes([
            "imagen.jpg"
        ])

    assert resultado["evidencias"]["ET-01"] == []
    assert resultado["evidencias"]["ET-05"] == []
    assert resultado["evidencias"]["ET-07"] == []

    assert resultado["reglas"]["ET-05"]["valor"] is None
    assert resultado["reglas"]["ET-07"]["valor"] is None
