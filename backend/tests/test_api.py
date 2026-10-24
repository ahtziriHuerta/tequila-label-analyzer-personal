"""Pruebas de la API con una base SQLite temporal (ver conftest.py).

El OCR se simula para no depender de Tesseract.
"""

from pathlib import Path
from unittest.mock import patch


# Una imagen PNG mínima; el contenido no importa
# porque el OCR está simulado.
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 32


def ocr_simulado(textos):
    """Devuelve un texto distinto por cada foto leída."""

    pendientes = iter(textos)

    def extraer(ruta):
        return {
            "texto": next(pendientes),
            "confianza": 80.0,
            "version": "original",
            "psm": 11,
            "puntuacion": 80.0,
        }

    return extraer


def fotos(*nombres):
    return [
        ("archivos", (nombre, PNG, "image/png"))
        for nombre in nombres
    ]


def crear_analisis(cliente, *textos, es_prueba=False):
    with patch(
        "app.services.analizador.extraer_texto",
        side_effect=ocr_simulado(textos)
    ):
        respuesta = cliente.post(
            "/analisis/imagenes",
            files=fotos(*[f"foto{i}.png" for i in range(len(textos))]),
            data={"es_prueba": "true"} if es_prueba else None
        )

    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()["id_analisis"]


def test_salud_informa_el_motor_ocr(cliente):
    datos = cliente.get("/salud").json()

    assert datos["estado"] == "ok"
    assert datos["ocr"] in ("gemini", "paddleocr", "tesseract")
    assert "ocr_disponible" in datos


def test_frontend_se_sirve_en_app(cliente):
    assert cliente.get("/", follow_redirects=False).headers["location"] == "/app/"

    respuesta = cliente.get("/app/")

    assert respuesta.status_code == 200
    assert "manifest.json" in respuesta.text


def test_historial_cuenta_detectados(cliente):
    crear_analisis(cliente, "TEQUILA REPOSADO")

    fila = cliente.get("/analisis/historial").json()["analisis"][0]

    assert fila["total_imagenes"] == 1
    # ET-01 (TEQUILA) y ET-03 (REPOSADO)
    assert fila["total_detectados"] == 2


def test_agregar_evidencia_solo_lee_la_foto_nueva(cliente):
    analisis_id = crear_analisis(cliente, "TEQUILA REPOSADO")

    lector = ocr_simulado(["Contenido neto 750 ml"])

    with patch(
        "app.services.analizador.extraer_texto",
        side_effect=lector
    ) as extraer:
        respuesta = cliente.post(
            f"/analisis/{analisis_id}/imagenes",
            files=fotos("posterior.png")
        )

    assert respuesta.status_code == 200, respuesta.text
    assert extraer.call_count == 1
    assert respuesta.json()["reglas"]["ET-05"]["estado"] == "Detectado"

    detalle = cliente.get(f"/analisis/{analisis_id}").json()

    assert len(detalle["imagenes"]) == 2
    # Las detecciones se reemplazan, no se duplican.
    codigos = [d["codigo_regla"] for d in detalle["detecciones"]]
    assert len(codigos) == len(set(codigos))

    et05 = next(d for d in detalle["detecciones"] if d["codigo_regla"] == "ET-05")
    assert et05["imagen_id"] == detalle["imagenes"][1]["id"]


def test_finalizar_bloquea_cambios(cliente):
    analisis_id = crear_analisis(cliente, "TEQUILA")

    respuesta = cliente.post(f"/analisis/{analisis_id}/finalizar")

    assert respuesta.status_code == 200
    assert cliente.get(f"/analisis/{analisis_id}").json()["analisis"]["estado"] == "Finalizado"

    assert cliente.post(f"/analisis/{analisis_id}/finalizar").status_code == 409
    assert cliente.post(
        f"/analisis/{analisis_id}/imagenes",
        files=fotos("otra.png")
    ).status_code == 409
    assert cliente.post(
        f"/analisis/{analisis_id}/revisiones",
        json={"codigo_regla": "ET-01", "resultado": "Presente"}
    ).status_code == 409


def test_eliminar_borra_registros_y_fotos(cliente, admin):
    analisis_id = crear_analisis(cliente, "TEQUILA", "750 ml")

    rutas = [
        Path(i["ruta_archivo"])
        for i in cliente.get(f"/analisis/{analisis_id}").json()["imagenes"]
    ]
    assert all(ruta.is_file() for ruta in rutas)

    cliente.post(
        f"/analisis/{analisis_id}/revisiones",
        json={"codigo_regla": "ET-01", "resultado": "Presente"}
    )

    # Solo un administrador borra.
    assert cliente.delete(f"/analisis/{analisis_id}").status_code == 403

    assert admin.delete(f"/analisis/{analisis_id}").status_code == 204
    assert cliente.get(f"/analisis/{analisis_id}").status_code == 404
    assert not any(ruta.exists() for ruta in rutas)
    assert admin.delete(f"/analisis/{analisis_id}").status_code == 404


# ==========================================
# PERMISOS
# ==========================================

def test_cada_analista_ve_solo_sus_analisis(cliente, otro_analista):
    propio = crear_analisis(cliente, "TEQUILA")
    ajeno = crear_analisis(otro_analista, "TEQUILA")

    ids = [a["id"] for a in cliente.get("/analisis/historial").json()["analisis"]]
    assert ids == [propio]

    # El análisis y las fotos de otro responden igual que si no existieran.
    assert cliente.get(f"/analisis/{ajeno}").status_code == 404
    assert cliente.get(f"/analisis/{ajeno}/revisiones").status_code == 404
    assert cliente.post(f"/analisis/{ajeno}/finalizar").status_code == 404
    imagen = otro_analista.get(f"/analisis/{ajeno}").json()["imagenes"][0]["id"]
    assert cliente.get(f"/imagenes/{imagen}").status_code == 404
    assert otro_analista.get(f"/imagenes/{imagen}").status_code == 200


def test_pruebas_son_del_equipo_y_no_cuentan_como_propias(cliente, otro_analista):
    prueba = crear_analisis(otro_analista, "TEQUILA", es_prueba=True)

    assert cliente.get("/analisis/historial").json()["analisis"] == []
    otras = cliente.get("/analisis/historial?ambito=pruebas").json()["analisis"]
    assert [a["id"] for a in otras] == [prueba]
    assert otras[0]["es_prueba"] == 1

    # Cualquier analista puede verlas y revisarlas.
    assert cliente.get(f"/analisis/{prueba}").status_code == 200
    assert cliente.post(
        f"/analisis/{prueba}/revisiones",
        json={"codigo_regla": "ET-01", "resultado": "Presente"}
    ).status_code == 201


def test_revision_queda_a_nombre_de_quien_la_hace(cliente, otro_analista):
    prueba = crear_analisis(otro_analista, "TEQUILA", es_prueba=True)

    revision = cliente.post(
        f"/analisis/{prueba}/revisiones",
        json={"codigo_regla": "ET-01", "resultado": "Presente"}
    ).json()["revision"]

    assert revision["usuario"] == "Analista Uno"


def test_admin_ve_todos_y_filtra_por_usuario(cliente, otro_analista, admin):
    uno = crear_analisis(cliente, "TEQUILA")
    dos = crear_analisis(otro_analista, "TEQUILA")

    assert cliente.get("/analisis/historial?ambito=todos").status_code == 403

    datos = admin.get("/analisis/historial?ambito=todos").json()
    assert {a["id"] for a in datos["analisis"]} == {uno, dos}
    assert {u["nombre"] for u in datos["usuarios"]} == {"Analista Uno", "Analista Dos"}

    id_dos = next(u["id"] for u in datos["usuarios"] if u["nombre"] == "Analista Dos")
    filtrado = admin.get(f"/analisis/historial?ambito=todos&usuario_id={id_dos}").json()
    assert [a["id"] for a in filtrado["analisis"]] == [dos]
    assert admin.get(f"/analisis/{uno}").status_code == 200


def test_sin_sesion_no_hay_datos(anonimo):
    for ruta in ("/analisis/historial", "/analisis/1", "/imagenes/1"):
        assert anonimo.get(ruta).status_code == 401
    assert anonimo.post("/analisis/imagenes", files=fotos("a.png")).status_code == 401
    # La interfaz y /salud siguen siendo públicas.
    assert anonimo.get("/app/").status_code == 200
    assert anonimo.get("/salud").status_code == 200


def test_respuestas_privadas_no_se_guardan_en_cache(cliente):
    assert cliente.get("/analisis/historial").headers["cache-control"] == "no-store"
