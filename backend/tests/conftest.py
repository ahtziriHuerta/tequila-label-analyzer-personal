"""Base SQLite temporal y cuentas de prueba para las pruebas de la API.

No tocan database/tequila.db ni backend/uploads: cada prueba
usa una copia vacía del esquema y una carpeta temporal.
"""

import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.main as main
from app import basedatos
from app.routers import analisis
from app.services import seguridad


ESQUEMA = (
    Path(__file__).resolve().parents[2]
    / "database"
    / "schema.sql"
)

CONTRASENA = "contrasena-de-prueba"

CUENTAS = {
    "analista": ("Analista Uno", "analista@ejemplo.mx", seguridad.ROL_ANALISTA),
    "analista2": ("Analista Dos", "analista2@ejemplo.mx", seguridad.ROL_ANALISTA),
    "admin": ("Admin", "admin@ejemplo.mx", seguridad.ROL_ADMIN),
}


@pytest.fixture
def base(tmp_path, monkeypatch):
    """Base temporal con las cuentas de CUENTAS (contraseña CONTRASENA)."""

    ruta = tmp_path / "tequila.db"
    uploads = tmp_path / "uploads"
    uploads.mkdir()

    with sqlite3.connect(ruta) as conexion:
        conexion.executescript(ESQUEMA.read_text(encoding="utf-8"))
        hash_ = seguridad.cifrar(CONTRASENA)
        for nombre, correo, rol in CUENTAS.values():
            conexion.execute(
                "INSERT INTO usuarios (nombre, correo, rol, contrasena_hash) VALUES (?, ?, ?, ?)",
                (nombre, correo, rol, hash_)
            )

    monkeypatch.setattr(basedatos, "DATABASE_PATH", ruta)
    monkeypatch.setattr(analisis, "UPLOADS_DIR", uploads)
    monkeypatch.setattr(main, "UPLOADS_DIR", uploads.resolve())
    seguridad.reiniciar_fallos_ip()

    return ruta


def cliente_de(cuenta):
    """Cliente con la sesión iniciada; cada uno guarda sus propias cookies."""

    cliente = TestClient(main.app)
    respuesta = cliente.post(
        "/auth/entrar",
        json={"correo": CUENTAS[cuenta][1], "contrasena": CONTRASENA}
    )
    assert respuesta.status_code == 200, respuesta.text
    return cliente


@pytest.fixture
def cliente(base):
    """Sesión de un analista (el caso más común)."""
    return cliente_de("analista")


@pytest.fixture
def admin(base):
    return cliente_de("admin")


@pytest.fixture
def otro_analista(base):
    return cliente_de("analista2")


@pytest.fixture
def anonimo(base):
    return TestClient(main.app)
