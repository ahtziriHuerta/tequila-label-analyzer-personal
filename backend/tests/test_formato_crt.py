"""Reglas del formato CRT (MO-RV/20) y de las normas a las que remite."""

import json
from unittest.mock import patch

from app.services.analizador import analizar_imagenes
from app.services.reglas import (
    comparar_con_declarado,
    detectar_categoria,
    detectar_clase,
    detectar_contenido_neto,
    detectar_contrasena_nom,
    detectar_denominacion,
    detectar_domicilio,
    detectar_graduacion_alcoholica,
    detectar_ingredientes,
    detectar_leyenda_precautoria,
    detectar_lote,
    detectar_marca,
    detectar_origen,
    detectar_razon_social,
    detectar_saborizante,
    normalizar,
)
from tests.test_api import fotos, ocr_simulado


# Contraetiqueta real (Don Ramón), leída con PaddleOCR.
TRASERA = normalizar(
    "NOM 1417 CRT ELABORADOYENVASADO POR: INDUSTRIALIZADORAINTEGRAL "
    "DELAGAVE,S.A.P.I.DEC.V. PERIFERICO SUR 7750, STA, MARIA TEQUEPEXPAN, "
    "TLAQUEPAQUE, JALISCO, MÉXICO C.P 45601 R.F.C.IHA-960717QR6 HECHO EN "
    "MÉXICO EL ABUSO EN EL CONSUMO DE ESTE PRODUCTO ES NOCIVO PARA LA SALUD "
    "-18 TDR PLATA PUNTA DIAMANTE 750 ml/NAC_MXV01 L3DRB0904269"
)


# ==========================================
# NOM-006
# ==========================================

def test_tequila_del_domicilio_no_es_denominacion():
    assert detectar_denominacion("CALLE 5, TEQUILA, JAL. C.P. 46400") == "No localizado"
    assert detectar_denominacion("CONSEJO REGULADOR DEL TEQUILA") == "No localizado"
    assert detectar_denominacion("TEQUILA REPOSADO HECHO EN TEQUILA, JALISCO") == "Detectado"


def test_categoria_acepta_las_cuatro_leyendas():
    for texto in ("100% PURO DE AGAVE", "100% PURO AGAVE", "100% AGAVE AZUL"):
        assert detectar_categoria(texto)["valor"] == "100% de agave"


def test_clases_de_exportacion():
    assert detectar_clase("TEQUILA SILVER")["valor"] == "Blanco"
    assert detectar_clase("TEQUILA GOLD")["valor"] == "Joven"
    assert detectar_clase("TEQUILA AGED")["valor"] == "Reposado"
    assert detectar_clase("TEQUILA EXTRA AGED")["valor"] == "Añejo"
    assert detectar_clase("TEQUILA ULTRA AGED")["valor"] == "Extra añejo"


def test_alcohol_fuera_de_la_tabla_1_es_probable_error_de_lectura():
    resultado = detectar_graduacion_alcoholica("88% ALC. VOL.", confianza_ocr=90)

    assert resultado["estado"] == "Baja legibilidad"
    assert "probable error" in resultado["observacion"]


def test_saborizante_e_ingredientes_no_aplican_sin_aditivos():
    assert detectar_saborizante("TEQUILA", aditivos="no")["estado"] == "No aplica"
    assert detectar_ingredientes("TEQUILA", aditivos="no")["estado"] == "No aplica"
    assert detectar_saborizante("TEQUILA", aditivos="no_se")["estado"] == "Revisión manual"
    assert detectar_saborizante("TEQUILA CON SABOR A MANGO")["estado"] == "Detectado"


# ==========================================
# NOM-030
# ==========================================

def test_contenido_con_simbolo_no_valido_pide_revision():
    resultado = detectar_contenido_neto("CONT. NET. 750 MLS")

    assert resultado["estado"] == "Revisión manual"
    assert "Tabla 3" in resultado["observacion"]


def test_contenido_menor_a_un_litro_va_en_mililitros():
    resultado = detectar_contenido_neto("CONTENIDO 0,75 L")

    assert resultado["valor"] == "750 mL"
    assert resultado["estado"] == "Revisión manual"
    assert "4.4.1" in resultado["observacion"]


# ==========================================
# CONTRAETIQUETA: NOM-142 Y CONTRASEÑA
# ==========================================

def test_contraetiqueta_real():
    assert detectar_razon_social(TRASERA)["estado"] == "Detectado"
    assert "INDUSTRIALIZADORA" in detectar_razon_social(TRASERA)["valor"]
    assert detectar_domicilio(TRASERA) == {"estado": "Detectado", "valor": "C.P. 45601, Jalisco"}
    assert detectar_origen(TRASERA)["estado"] == "Detectado"
    assert detectar_contrasena_nom(TRASERA)["valor"] == "NOM 1417"
    assert detectar_lote(TRASERA)["valor"] == "L3DRB0904269"
    assert detectar_leyenda_precautoria(TRASERA)["estado"] == "Detectado"


def test_clave_de_norma_no_es_contrasena():
    assert detectar_contrasena_nom("CUMPLE NOM-006-SCFI-2012")["estado"] == "Revisión manual"


def test_leyenda_incompleta():
    assert detectar_leyenda_precautoria("EL ABUSO ES NOCIVO")["estado"] == "Baja legibilidad"


def test_marca_declarada():
    assert detectar_marca("DON RAMON TEQUILA", marca="Don Ramón")["estado"] == "Detectado"
    assert detectar_marca("DON RAMDN TEQUILA", marca="Don Ramón")["estado"] == "Revisión manual"
    assert detectar_marca("TEQUILA")["estado"] == "Revisión manual"


# ==========================================
# DATOS DECLARADOS Y SUPERFICIE PRINCIPAL
# ==========================================

def test_diferencia_con_lo_declarado_pide_revision():
    resultado = comparar_con_declarado(
        "ET-07",
        {"estado": "Detectado", "valor": "38% Alc. Vol.", "observacion": None},
        {"alcohol": 40}
    )

    assert resultado["estado"] == "Revisión manual"
    assert "Declarado: 40%" in resultado["observacion"]


def test_tequila_mixto_declarado():
    resultado = comparar_con_declarado(
        "ET-02",
        {"estado": "Revisión manual", "valor": None, "observacion": None},
        {"categoria": "Tequila"}
    )

    assert resultado["estado"] == "Detectado"
    assert resultado["valor"] == "Tequila"


def ocr(texto):
    return {"texto": texto, "confianza": 90, "version": "original", "psm": 6, "puntuacion": 90}


def test_dato_obligatorio_fuera_de_la_foto_frontal():
    with patch(
        "app.services.analizador.extraer_texto",
        side_effect=[ocr("DON RAMON"), ocr("TEQUILA PLATA 100% DE AGAVE 750 ml 35% Alc. Vol.")]
    ):
        resultado = analizar_imagenes(
            ["frontal.jpg", "posterior.jpg"],
            vistas=["frontal", "posterior"],
            datos={"destino": "nacional", "marca": "Don Ramón"}
        )

    reglas = resultado["reglas"]
    assert reglas["ET-10"]["estado"] == "Detectado"         # la marca sí está al frente
    assert reglas["ET-01"]["estado"] == "Revisión manual"   # "Tequila" solo atrás
    assert "superficie principal" in reglas["ET-01"]["observacion"]
    # Para nacional el contenido también va al frente (marca + del formato).
    assert reglas["ET-05"]["estado"] == "Revisión manual"


def test_exportacion_no_exige_contenido_al_frente():
    with patch(
        "app.services.analizador.extraer_texto",
        side_effect=[ocr("TEQUILA"), ocr("750 ml")]
    ):
        resultado = analizar_imagenes(
            ["frontal.jpg", "posterior.jpg"],
            vistas=["frontal", "posterior"],
            datos={"destino": "exportacion"}
        )

    assert resultado["reglas"]["ET-05"]["estado"] == "Detectado"


# ==========================================
# API
# ==========================================

DATOS = {
    "destino": "nacional",
    "marca": "Don Ramón",
    "categoria": "100% de agave",
    "clase": "Blanco",
    "contenido_ml": 750,
    "alcohol": 35,
    "aditivos": "no",
}


def crear_con_datos(cliente, datos=DATOS):
    with patch(
        "app.services.analizador.extraer_texto",
        side_effect=ocr_simulado(["TEQUILA PLATA DON RAMON 100% DE AGAVE 35% Alc. Vol. 750 ml", TRASERA])
    ):
        respuesta = cliente.post(
            "/analisis/imagenes",
            files=fotos("frente.png", "atras.png"),
            data={"datos": json.dumps(datos), "vistas": json.dumps(["frontal", "posterior"])}
        )

    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()["id_analisis"]


def test_analisis_guarda_datos_vistas_y_15_requisitos(cliente):
    analisis_id = crear_con_datos(cliente)

    detalle = cliente.get(f"/analisis/{analisis_id}").json()

    assert detalle["analisis"]["marca"] == "Don Ramón"
    assert detalle["analisis"]["destino"] == "nacional"
    assert [i["vista"] for i in detalle["imagenes"]] == ["frontal", "posterior"]

    estados = {d["codigo_regla"]: d["estado"] for d in detalle["detecciones"]}
    assert len(estados) == 15
    assert estados["ET-04"] == "No aplica"
    assert estados["ET-19"] == "No aplica"
    assert estados["ET-10"] == "Detectado"
    assert estados["ET-12"] == "Detectado"


def test_datos_no_validos(cliente):
    with patch("app.services.analizador.extraer_texto", side_effect=ocr_simulado(["TEQUILA"])):
        respuesta = cliente.post(
            "/analisis/imagenes",
            files=fotos("a.png"),
            data={"datos": json.dumps({"clase": "Platino"})}
        )

    assert respuesta.status_code == 422


def test_cambiar_datos_reevalua_sin_repetir_ocr(cliente):
    analisis_id = crear_con_datos(cliente, {**DATOS, "alcohol": None})

    with patch("app.services.analizador.extraer_texto") as extraer:
        respuesta = cliente.put(f"/analisis/{analisis_id}/datos", json={**DATOS, "alcohol": 40})

    assert respuesta.status_code == 200, respuesta.text
    assert extraer.call_count == 0
    assert respuesta.json()["reglas"]["ET-07"]["estado"] == "Revisión manual"

    detalle = cliente.get(f"/analisis/{analisis_id}").json()
    assert detalle["analisis"]["alcohol"] == 40
    et07 = next(d for d in detalle["detecciones"] if d["codigo_regla"] == "ET-07")
    assert "Declarado: 40%" in et07["observacion"]


def test_dictamen_del_inspector(cliente):
    analisis_id = crear_con_datos(cliente)

    sin_correcta = cliente.post(
        f"/analisis/{analisis_id}/dictamen",
        json={"codigo_regla": "ET-14", "cumple": "NO"}
    )
    assert sin_correcta.status_code == 422

    respuesta = cliente.post(
        f"/analisis/{analisis_id}/dictamen",
        json={
            "codigo_regla": "ET-14",
            "cumple": "NO",
            "informacion_incorrecta": "EL ABUSO ES NOCIVO",
            "informacion_correcta": "EL ABUSO EN EL CONSUMO DE ESTE PRODUCTO ES NOCIVO PARA LA SALUD",
        }
    )
    assert respuesta.status_code == 201, respuesta.text

    cliente.post(f"/analisis/{analisis_id}/dictamen", json={"codigo_regla": "ET-04", "cumple": "NA"})

    dictamenes = cliente.get(f"/analisis/{analisis_id}").json()["dictamenes"]
    assert [d["codigo_regla"] for d in dictamenes] == ["ET-04", "ET-14"]
    assert dictamenes[1]["usuario"] == "Analista Uno"

    cliente.post(f"/analisis/{analisis_id}/finalizar")
    cerrado = cliente.post(
        f"/analisis/{analisis_id}/dictamen",
        json={"codigo_regla": "ET-01", "cumple": "SI"}
    )
    assert cerrado.status_code == 409
