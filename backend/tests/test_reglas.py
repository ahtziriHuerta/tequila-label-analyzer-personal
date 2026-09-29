from app.services.reglas import normalizar, detectar_denominacion


def test_normalizar_quita_acentos_y_espacios():
    assert normalizar("  Hecho   en México ") == "HECHO EN MEXICO"


def test_detecta_tequila():
    assert detectar_denominacion(normalizar("Tequila Reposado")) == "Detectado"
