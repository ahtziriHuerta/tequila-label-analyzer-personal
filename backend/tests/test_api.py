"""Pruebas de la API con una base SQLite temporal.

No tocan database/tequila.db ni backend/uploads: cada prueba
usa una copia vacía del esquema y una carpeta temporal.
El OCR se simula para no depender de Tesseract.
"""

import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

import app.main as main
from app.routers import analisis


ESQUEMA = (
    Path(__file__).resolve().parents[2]
    / "database"
    / "schema.sql"
)

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


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    base = tmp_path / "tequila.db"
    uploads = tmp_path / "uploads"
    uploads.mkdir()

    with sqlite3.connect(base) as conexion:
        conexion.executescript(
            ESQUEMA.read_text(encoding="utf-8")
        )

    monkeypatch.setattr(analisis, "DATABASE_PATH", base)
    monkeypatch.setattr(analisis, "UPLOADS_DIR", uploads)
    monkeypatch.setattr(main, "DATABASE_PATH", base)
    monkeypatch.setattr(main, "UPLOADS_DIR", uploads.resolve())

    return TestClient(main.app)


def fotos(*nombres):
    return [
        ("archivos", (nombre, PNG, "image/png"))
        for nombre in nombres
    ]


def crear_analisis(cliente, *textos):
    with patch(
        "app.services.analizador.extraer_texto",
        side_effect=ocr_simulado(textos)
    ):
        respuesta = cliente.post(
            "/analisis/imagenes",
            files=fotos(*[f"foto{i}.png" for i in range(len(textos))])
        )

    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()["id_analisis"]


def test_salud_informa_el_motor_ocr(cliente):
    datos = cliente.get("/salud").json()

    assert datos["estado"] == "ok"
    assert datos["ocr"] == "tesseract"
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


def test_eliminar_borra_registros_y_fotos(cliente):
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

    assert cliente.delete(f"/analisis/{analisis_id}").status_code == 204
    assert cliente.get(f"/analisis/{analisis_id}").status_code == 404
    assert not any(ruta.exists() for ruta in rutas)
    assert cliente.delete(f"/analisis/{analisis_id}").status_code == 404
