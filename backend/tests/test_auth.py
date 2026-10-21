"""Inicio de sesión, contraseñas, sesiones y actualización de bases anteriores."""

import sqlite3

from fastapi.testclient import TestClient

import app.main as main
from app import basedatos, usuarios_cli
from app.routers.auth import CREDENCIALES_INVALIDAS
from app.services import seguridad
from tests.conftest import CONTRASENA, CUENTAS, cliente_de


CORREO = CUENTAS["analista"][1]


def entrar(cliente, correo=CORREO, contrasena=CONTRASENA):
    return cliente.post("/auth/entrar", json={"correo": correo, "contrasena": contrasena})


def test_entrar_abre_sesion_con_cookie_httponly(anonimo):
    respuesta = entrar(anonimo, correo="  Analista@Ejemplo.MX ")

    assert respuesta.status_code == 200
    assert respuesta.json()["usuario"]["correo"] == CORREO
    assert "contrasena_hash" not in respuesta.json()["usuario"]

    cookie = respuesta.headers["set-cookie"]
    assert cookie.startswith(f"{seguridad.NOMBRE_COOKIE}=")
    assert "HttpOnly" in cookie and "SameSite=lax" in cookie

    assert anonimo.get("/auth/yo").json()["usuario"]["nombre"] == "Analista Uno"


def test_error_no_revela_si_el_correo_existe(anonimo):
    mala_contrasena = entrar(anonimo, contrasena="equivocada")
    correo_inexistente = entrar(anonimo, correo="nadie@ejemplo.mx")

    assert mala_contrasena.status_code == correo_inexistente.status_code == 401
    assert mala_contrasena.json()["detail"] == correo_inexistente.json()["detail"] == CREDENCIALES_INVALIDAS


def test_bloqueo_tras_cinco_intentos(anonimo):
    for _ in range(seguridad.MAX_INTENTOS):
        assert entrar(anonimo, contrasena="equivocada").status_code == 401

    # Bloqueada aunque ahora la contraseña sea correcta.
    assert entrar(anonimo).status_code == 429


def test_bloqueo_por_ip_con_correos_inexistentes(anonimo):
    for i in range(seguridad.MAX_FALLOS_POR_IP):
        entrar(anonimo, correo=f"nadie{i}@ejemplo.mx")

    assert entrar(anonimo).status_code == 429


def test_salir_invalida_la_sesion(cliente):
    cookie = cliente.cookies.get(seguridad.NOMBRE_COOKIE)

    assert cliente.post("/auth/salir").status_code == 204

    # Aunque alguien conservara la cookie, el servidor ya no la acepta.
    copia = TestClient(main.app, cookies={seguridad.NOMBRE_COOKIE: cookie})
    assert copia.get("/auth/yo").status_code == 401


def test_sesion_vencida(cliente, base):
    with sqlite3.connect(base) as conexion:
        conexion.execute("UPDATE sesiones SET expira = '2000-01-01 00:00:00'")

    assert cliente.get("/analisis/historial").status_code == 401


def test_cuenta_desactivada_no_entra_ni_conserva_sesion(cliente, base):
    with sqlite3.connect(base) as conexion:
        conexion.execute("UPDATE usuarios SET activo = 0 WHERE correo = ?", (CORREO,))

    assert cliente.get("/auth/yo").status_code == 401
    assert entrar(TestClient(main.app)).status_code == 401


def test_contrasena_temporal_obliga_a_cambiarla(anonimo, base):
    with sqlite3.connect(base) as conexion:
        conexion.execute("UPDATE usuarios SET debe_cambiar_contrasena = 1 WHERE correo = ?", (CORREO,))

    assert entrar(anonimo).json()["usuario"]["debe_cambiar_contrasena"] is True
    assert anonimo.get("/analisis/historial").status_code == 403

    def cambiar(actual, nueva):
        return anonimo.post("/auth/cambiar-contrasena", json={"actual": actual, "nueva": nueva})

    assert cambiar("equivocada", "una-contrasena-nueva").status_code == 400
    assert cambiar(CONTRASENA, "corta").status_code == 400
    assert cambiar(CONTRASENA, CONTRASENA).status_code == 400

    respuesta = cambiar(CONTRASENA, "una-contrasena-nueva")
    assert respuesta.status_code == 200
    assert respuesta.json()["usuario"]["debe_cambiar_contrasena"] is False
    assert anonimo.get("/analisis/historial").status_code == 200


def test_cambiar_contrasena_cierra_las_otras_sesiones(base):
    celular = cliente_de("analista")
    pc = cliente_de("analista")

    pc.post("/auth/cambiar-contrasena", json={"actual": CONTRASENA, "nueva": "una-contrasena-nueva"})

    assert pc.get("/auth/yo").status_code == 200
    assert celular.get("/auth/yo").status_code == 401


def test_rechaza_peticiones_de_otro_sitio(cliente):
    respuesta = cliente.post(
        "/auth/salir",
        headers={"Origin": "https://sitio-malicioso.example"}
    )
    assert respuesta.status_code == 403


def test_cli_crea_cuenta_con_contrasena_temporal(base, capsys):
    usuarios_cli.main(["crear", "--nombre", "Nueva", "--correo", "Nueva@Ejemplo.mx", "--rol", "administrador"])

    salida = capsys.readouterr().out
    temporal = salida.split("Contraseña temporal: ")[1].split()[0]

    respuesta = entrar(TestClient(main.app), correo="nueva@ejemplo.mx", contrasena=temporal)
    assert respuesta.status_code == 200
    assert respuesta.json()["usuario"]["rol"] == "administrador"
    assert respuesta.json()["usuario"]["debe_cambiar_contrasena"] is True


def test_actualiza_bases_anteriores_al_login(tmp_path, monkeypatch):
    """Una base con el esquema viejo gana las columnas nuevas y sus análisis pasan a pruebas."""

    ruta = tmp_path / "vieja.db"
    with sqlite3.connect(ruta) as conexion:
        conexion.executescript(
            """
            CREATE TABLE usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT NOT NULL,
                correo TEXT NOT NULL UNIQUE, fecha_registro TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE analisis (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario_id INTEGER NOT NULL,
                estado TEXT NOT NULL DEFAULT 'Pendiente', fecha_creacion TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE imagenes (id INTEGER PRIMARY KEY AUTOINCREMENT, analisis_id INTEGER NOT NULL,
                nombre_archivo TEXT NOT NULL, ruta_archivo TEXT NOT NULL, texto_ocr TEXT, confianza_ocr REAL,
                fecha_carga TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
            INSERT INTO usuarios (nombre, correo) VALUES ('Usuario de prueba', 'sistema@tequila.local');
            INSERT INTO analisis (usuario_id) VALUES (1), (1);
            """
        )
    monkeypatch.setattr(basedatos, "DATABASE_PATH", ruta)

    basedatos.asegurar_esquema()
    basedatos.asegurar_esquema()  # repetirlo no cambia nada

    with sqlite3.connect(ruta) as conexion:
        assert conexion.execute("SELECT COUNT(*) FROM analisis WHERE es_prueba = 1").fetchone()[0] == 2
        assert conexion.execute("SELECT contrasena_hash, rol FROM usuarios").fetchone() == (None, "analista")
        conexion.execute("SELECT motor_ocr FROM imagenes")
        conexion.execute("SELECT COUNT(*) FROM sesiones")
        conexion.execute("SELECT COUNT(*) FROM evidencias")
        # Los análisis nuevos ya no se marcan como prueba al reiniciar.
        conexion.execute("INSERT INTO analisis (usuario_id) VALUES (1)")

    basedatos.asegurar_esquema()
    with sqlite3.connect(ruta) as conexion:
        assert conexion.execute("SELECT es_prueba FROM analisis ORDER BY id DESC").fetchone()[0] == 0
