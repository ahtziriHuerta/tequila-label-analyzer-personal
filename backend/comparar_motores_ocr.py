"""Compara motores de lectura sobre las mismas botellas: PaddleOCR, Tesseract,
Gemini y ChatGPT (OpenAI).

Es un script de PRUEBAS: no lo usa la aplicación.

Cada motor lee las mismas fotos y su texto pasa por el MISMO motor de reglas
de la herramienta (ET-01, 02, 03, 05 y 07). Así se compara solo al "lector".
Gemini y ChatGPT, además, devuelven los campos ya separados (denominación,
categoría, clase...); eso aparece como "<motor> · campos" en el informe.

Organización de la carpeta de entrada:

    carpeta/
        botella-01/  foto1.jpg  foto2.jpg     <- una subcarpeta por botella
        botella-02/  ...
        suelta.jpg                            <- una foto suelta = una botella
        referencia.json                       <- lo que de verdad dice cada etiqueta

La primera vez se crea referencia.json con "?" en cada campo. Llénalo viendo
las fotos: el valor tal como lo da la herramienta ("TEQUILA", "100% de agave",
"Reposado", "750 mL", "40% Alc. Vol.") o null si la etiqueta NO lo trae.
Los campos con "?" no se califican.

Claves de API: variables GEMINI_API_KEY y OPENAI_API_KEY, o en backend/.env
(que no se sube a git). Un motor sin clave se omite.
Modelos: GEMINI_MODEL y OPENAI_MODEL (ver valores por defecto abajo).

Uso, desde backend/:

    ..\\.venv\\Scripts\\python.exe comparar_motores_ocr.py ..\\pruebas-locales\\comparacion
    ... --motores paddle,gemini     solo esos motores
    ... --repetir                   vuelve a leer aunque ya haya resultados

Las lecturas se guardan en <carpeta>/resultados/lecturas.json: si se corta o
se vuelve a correr, no se pagan otra vez las fotos ya leídas.
Resultados: resultados/informe.md y resultados/comparacion.csv.
"""

from __future__ import annotations

import argparse
import base64
import csv
import io
import json
import os
import re
import sys
import time
from pathlib import Path

BACKEND = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND))
os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")

import httpx  # noqa: E402
from dotenv import load_dotenv  # noqa: E402
from PIL import Image, ImageOps  # noqa: E402

from app.services.analizador import analizar_imagenes  # noqa: E402
from app.services.reglas import (  # noqa: E402
    detectar_categoria,
    detectar_clase,
    detectar_contenido_neto,
    detectar_denominacion,
    detectar_graduacion_alcoholica,
    normalizar,
)

load_dotenv(BACKEND / ".env")

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini")

MOTORES = ("paddle", "tesseract", "gemini", "openai")
REGLAS = {
    "ET-01": "Denominación",
    "ET-02": "Categoría",
    "ET-03": "Clase",
    "ET-05": "Contenido neto",
    "ET-07": "Graduación alcohólica",
}
EXTENSIONES = {".jpg", ".jpeg", ".png", ".webp"}
LADO_MAXIMO_API = 2048  # las APIs reducen la foto de todos modos; así se envía menos

PROMPT = """Eres un lector de etiquetas de tequila para una herramienta de verificación de la NOM-006.

Devuelve SOLO un objeto JSON con esta forma:
{
  "texto": "todo el texto visible en la imagen, transcrito LITERALMENTE",
  "campos": {
    "denominacion": "...",
    "categoria": "...",
    "clase": "...",
    "contenido_neto": "...",
    "graduacion_alcoholica": "..."
  }
}

Reglas estrictas:
- Copia el texto EXACTAMENTE como está impreso, aunque tenga errores de ortografía, números raros o esté incompleto. NO corrijas, NO completes, NO adivines.
- Cada campo es el fragmento literal de la etiqueta donde aparece ese dato (por ejemplo "TEQUILA", "100% DE AGAVE", "REPOSADO", "750 ml", "40% Alc. Vol.").
- Si un dato no se ve o no se puede leer con certeza, pon null. Nunca lo deduzcas por la marca, el color de la botella ni por lo que "debería" decir.
"""


# ==========================================
# MOTORES
# ==========================================

_paddle = None


def leer_paddle(ruta: Path) -> dict:
    """PaddleOCR con la misma configuración que el backend con el arreglo de
    velocidad (detección limitada a 1920 px; lee los recortes a tamaño completo)."""

    global _paddle
    if _paddle is None:
        from paddleocr import PaddleOCR

        _paddle = PaddleOCR(
            lang="es",
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            enable_mkldnn=False,
            text_det_limit_type="max",
            text_det_limit_side_len=1920,
        )

    textos, confianzas = [], []
    for resultado in _paddle.predict(str(ruta)):
        datos = resultado.json
        datos = datos.get("res", datos)
        for texto, confianza in zip(datos.get("rec_texts", []), datos.get("rec_scores", [])):
            texto = str(texto).strip()
            if texto:
                textos.append(texto)
                confianzas.append(float(confianza) * 100)

    return {
        "texto": " ".join(textos),
        "confianza": round(sum(confianzas) / len(confianzas), 2) if confianzas else 0.0,
    }


def leer_tesseract(ruta: Path) -> dict:
    from app.services.ocr import extraer_texto

    resultado = extraer_texto(str(ruta))
    return {"texto": resultado["texto"], "confianza": resultado["confianza"]}


def imagen_base64(ruta: Path) -> str:
    """JPEG derecho (según EXIF) y con el lado mayor a LADO_MAXIMO_API."""

    with Image.open(ruta) as imagen:
        imagen = ImageOps.exif_transpose(imagen).convert("RGB")
        imagen.thumbnail((LADO_MAXIMO_API, LADO_MAXIMO_API))
        bufer = io.BytesIO()
        imagen.save(bufer, format="JPEG", quality=90)
    return base64.b64encode(bufer.getvalue()).decode("ascii")


def interpretar_json(texto: str) -> dict:
    """Acepta el JSON aunque venga envuelto en ```json ... ```."""

    texto = texto.strip()
    texto = re.sub(r"^```(?:json)?\s*|\s*```$", "", texto)
    datos = json.loads(texto)
    return {
        "texto": str(datos.get("texto") or ""),
        "campos": datos.get("campos") or {},
        # Los modelos no dan una confianza comparable; 100 evita que las reglas
        # marquen "Baja legibilidad" por un número que no significa nada aquí.
        "confianza": 100.0,
    }


def leer_gemini(ruta: Path) -> dict:
    cuerpo = {
        "contents": [{
            "parts": [
                {"inline_data": {"mime_type": "image/jpeg", "data": imagen_base64(ruta)}},
                {"text": PROMPT},
            ],
        }],
        "generationConfig": {"responseMimeType": "application/json"},
    }
    if os.getenv("GEMINI_TEMPERATURE"):
        cuerpo["generationConfig"]["temperature"] = float(os.environ["GEMINI_TEMPERATURE"])

    respuesta = httpx.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent",
        headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"]},
        json=cuerpo,
        timeout=180,
    )
    respuesta.raise_for_status()
    partes = respuesta.json()["candidates"][0]["content"]["parts"]
    return interpretar_json("".join(p.get("text", "") for p in partes))


def leer_openai(ruta: Path) -> dict:
    cuerpo = {
        "model": OPENAI_MODEL,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": PROMPT},
                {"type": "image_url", "image_url": {
                    "url": f"data:image/jpeg;base64,{imagen_base64(ruta)}",
                    "detail": "high",
                }},
            ],
        }],
        "response_format": {"type": "json_object"},
    }
    # Los modelos de razonamiento solo aceptan la temperatura por defecto.
    if os.getenv("OPENAI_TEMPERATURE"):
        cuerpo["temperature"] = float(os.environ["OPENAI_TEMPERATURE"])

    respuesta = httpx.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
        json=cuerpo,
        timeout=180,
    )
    respuesta.raise_for_status()
    return interpretar_json(respuesta.json()["choices"][0]["message"]["content"])


LECTORES = {
    "paddle": leer_paddle,
    "tesseract": leer_tesseract,
    "gemini": leer_gemini,
    "openai": leer_openai,
}


def nombre_motor(motor: str) -> str:
    """Incluye el modelo para no mezclar resultados si se cambia GEMINI_MODEL."""

    return {"gemini": f"gemini:{GEMINI_MODEL}", "openai": f"openai:{OPENAI_MODEL}"}.get(motor, motor)


def motor_disponible(motor: str) -> str | None:
    """Devuelve el motivo por el que no se puede usar, o None."""

    if motor == "gemini" and not os.getenv("GEMINI_API_KEY"):
        return "falta GEMINI_API_KEY"
    if motor == "openai" and not os.getenv("OPENAI_API_KEY"):
        return "falta OPENAI_API_KEY"
    if motor == "paddle":
        import importlib.util

        if importlib.util.find_spec("paddleocr") is None:
            return "PaddleOCR no está instalado"
    return None


# ==========================================
# BOTELLAS Y REFERENCIA
# ==========================================

def buscar_botellas(carpeta: Path) -> dict[str, list[Path]]:
    botellas = {}
    for elemento in sorted(carpeta.iterdir()):
        if elemento.is_dir() and elemento.name != "resultados":
            fotos = sorted(f for f in elemento.iterdir() if f.suffix.lower() in EXTENSIONES)
            if fotos:
                botellas[elemento.name] = fotos
        elif elemento.suffix.lower() in EXTENSIONES:
            botellas[elemento.stem] = [elemento]
    return botellas


def cargar_referencia(carpeta: Path, botellas: dict) -> dict:
    """Crea o completa referencia.json; nunca borra lo que ya se llenó."""

    archivo = carpeta / "referencia.json"
    referencia = json.loads(archivo.read_text("utf-8")) if archivo.exists() else {}

    cambio = False
    for botella, fotos in botellas.items():
        if botella not in referencia:
            referencia[botella] = {"_fotos": [f.name for f in fotos], **{r: "?" for r in REGLAS}}
            cambio = True
    if cambio:
        archivo.write_text(json.dumps(referencia, ensure_ascii=False, indent=2), "utf-8")
        print(f"Plantilla de referencia actualizada: {archivo}")
    return referencia


# ==========================================
# COMPARACIÓN
# ==========================================

def numeros(valor: str) -> list[float]:
    return sorted({float(n.replace(",", ".")) for n in re.findall(r"\d+(?:[.,]\d+)?", valor)})


def calificar(regla: str, esperado, obtenido) -> str:
    """ok · error (dio un valor equivocado) · parcial (entre varios) · falta · sin_ref"""

    if esperado == "?":
        return "sin_ref"
    if esperado is None:
        return "ok" if obtenido is None else "error"
    if obtenido is None:
        return "falta"

    if regla in ("ET-05", "ET-07"):
        esperados, obtenidos = numeros(str(esperado)), numeros(str(obtenido))
    else:
        esperados = [normalizar(str(esperado))]
        obtenidos = [normalizar(v) for v in str(obtenido).split(",")]

    if obtenidos == esperados:
        return "ok"
    if set(esperados) <= set(obtenidos):
        return "parcial"
    return "error"


def valores_por_reglas(fotos: list[Path], lecturas: dict) -> dict:
    """Pasa el texto de cada foto por el motor de reglas de la herramienta."""

    ocr_previo = {
        str(foto): {
            "texto": lecturas[foto.name]["texto"],
            "confianza": lecturas[foto.name]["confianza"],
            "version": "comparacion",
            "psm": 0,
            "puntuacion": lecturas[foto.name]["confianza"],
        }
        for foto in fotos
    }
    reglas = analizar_imagenes([str(f) for f in fotos], ocr_previo=ocr_previo)["reglas"]
    return {codigo: reglas[codigo]["valor"] for codigo in REGLAS}


def valores_por_campos(fotos: list[Path], lecturas: dict) -> dict:
    """Usa los campos que separó el modelo, llevados al mismo formato que las reglas."""

    claves = {
        "ET-01": ("denominacion", lambda t: "TEQUILA" if detectar_denominacion(t) == "Detectado" else None),
        "ET-02": ("categoria", lambda t: detectar_categoria(t)["valor"]),
        "ET-03": ("clase", lambda t: detectar_clase(t)["valor"]),
        "ET-05": ("contenido_neto", lambda t: detectar_contenido_neto(t)["valor"]),
        "ET-07": ("graduacion_alcoholica", lambda t: detectar_graduacion_alcoholica(t)["valor"]),
    }
    valores = {}
    for codigo, (clave, a_formato) in claves.items():
        fragmentos = [
            str(lecturas[f.name]["campos"].get(clave))
            for f in fotos
            if lecturas[f.name].get("campos", {}).get(clave)
        ]
        valores[codigo] = a_formato(normalizar(" ".join(fragmentos))) if fragmentos else None
    return valores


# ==========================================
# PROGRAMA
# ==========================================

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("carpeta", type=Path)
    parser.add_argument("--motores", default=",".join(MOTORES))
    parser.add_argument("--repetir", action="store_true")
    args = parser.parse_args()

    carpeta = args.carpeta.resolve()
    salida = carpeta / "resultados"
    salida.mkdir(parents=True, exist_ok=True)
    archivo_lecturas = salida / "lecturas.json"

    botellas = buscar_botellas(carpeta)
    if not botellas:
        sys.exit(f"No hay fotos en {carpeta}")
    referencia = cargar_referencia(carpeta, botellas)
    total_fotos = sum(len(f) for f in botellas.values())
    print(f"{len(botellas)} botellas, {total_fotos} fotos")

    lecturas = json.loads(archivo_lecturas.read_text("utf-8")) if archivo_lecturas.exists() else {}

    motores = []
    for motor in [m.strip() for m in args.motores.split(",") if m.strip()]:
        if motor not in LECTORES:
            sys.exit(f"Motor desconocido: {motor} (opciones: {', '.join(MOTORES)})")
        motivo = motor_disponible(motor)
        if motivo:
            print(f"- Se omite {motor}: {motivo}")
        else:
            motores.append(motor)

    # 1. Leer cada foto con cada motor (guardando después de cada una)
    for motor in motores:
        nombre = nombre_motor(motor)
        guardadas = lecturas.setdefault(nombre, {})
        print(f"\n== {nombre} ==")
        for botella, fotos in botellas.items():
            for foto in fotos:
                previa = guardadas.get(foto.name)
                if previa and not previa.get("error") and not args.repetir:
                    continue
                inicio = time.perf_counter()
                try:
                    resultado = LECTORES[motor](foto)
                except Exception as error:  # se anota y se sigue con la siguiente
                    resultado = {"texto": "", "confianza": 0.0, "error": f"{type(error).__name__}: {error}"[:300]}
                resultado["segundos"] = round(time.perf_counter() - inicio, 1)
                guardadas[foto.name] = resultado
                archivo_lecturas.write_text(json.dumps(lecturas, ensure_ascii=False, indent=1), "utf-8")
                estado = resultado.get("error") or f"{len(resultado['texto'])} caracteres"
                print(f"  {botella}/{foto.name}: {resultado['segundos']} s - {estado}")

    # 2. Calificar contra la referencia
    columnas = []  # (etiqueta, motor, función)
    for nombre in lecturas:
        columnas.append((nombre, nombre, valores_por_reglas))
        if nombre.startswith(("gemini", "openai")):
            columnas.append((f"{nombre} · campos", nombre, valores_por_campos))

    filas = []
    for botella, fotos in botellas.items():
        for etiqueta, nombre, funcion in columnas:
            leidas = lecturas[nombre]
            if not all(f.name in leidas for f in fotos):
                continue
            valores = funcion(fotos, leidas)
            for codigo in REGLAS:
                esperado = referencia[botella].get(codigo, "?")
                filas.append({
                    "botella": botella,
                    "motor": etiqueta,
                    "regla": codigo,
                    "esperado": esperado,
                    "obtenido": valores[codigo],
                    "resultado": calificar(codigo, esperado, valores[codigo]),
                })

    with open(salida / "comparacion.csv", "w", newline="", encoding="utf-8-sig") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=list(filas[0]) if filas else ["botella"])
        escritor.writeheader()
        escritor.writerows(filas)

    escribir_informe(salida / "informe.md", botellas, columnas, lecturas, filas)
    print(f"\nInforme: {salida / 'informe.md'}")


def escribir_informe(archivo: Path, botellas, columnas, lecturas, filas) -> None:
    marcas = {"ok": "✅", "error": "❌", "parcial": "🟡", "falta": "⬜", "sin_ref": ""}
    lineas = [
        "# Comparación de motores de lectura",
        "",
        "✅ correcto · ❌ valor equivocado · 🟡 el correcto entre varios · ⬜ no lo encontró · "
        "sin marca = falta llenar la referencia.",
        "",
        "Un ❌ es peor que un ⬜: la herramienta daría por bueno un dato equivocado.",
        "",
        "## Resumen",
        "",
        "| Motor | ✅ | ❌ | 🟡 | ⬜ | Calificados | s/foto | Fotos con error |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for etiqueta, nombre, _ in columnas:
        propias = [f for f in filas if f["motor"] == etiqueta and f["resultado"] != "sin_ref"]
        cuenta = {r: sum(f["resultado"] == r for f in propias) for r in marcas}
        tiempos = [l["segundos"] for l in lecturas[nombre].values() if not l.get("error")]
        errores = sum(1 for l in lecturas[nombre].values() if l.get("error"))
        promedio = f"{sum(tiempos) / len(tiempos):.1f}" if tiempos else "—"
        lineas.append(
            f"| {etiqueta} | {cuenta['ok']} | {cuenta['error']} | {cuenta['parcial']} | "
            f"{cuenta['falta']} | {len(propias)} | {promedio} | {errores} |"
        )

    lineas += ["", "## Por botella"]
    etiquetas = [c[0] for c in columnas]
    for botella, fotos in botellas.items():
        lineas += [
            "",
            f"### {botella}",
            "",
            "Fotos: " + ", ".join(f.name for f in fotos),
            "",
            "| Regla | Referencia | " + " | ".join(etiquetas) + " |",
            "|---|---|" + "---|" * len(etiquetas),
        ]
        for codigo, requisito in REGLAS.items():
            celdas = []
            esperado = "?"
            for etiqueta in etiquetas:
                fila = next(
                    (f for f in filas if f["botella"] == botella and f["motor"] == etiqueta and f["regla"] == codigo),
                    None,
                )
                if fila is None:
                    celdas.append("—")
                    continue
                esperado = fila["esperado"]
                celdas.append(f"{marcas[fila['resultado']]} {fila['obtenido'] or '·'}".strip())
            referencia = "null" if esperado is None else esperado
            lineas.append(f"| {codigo} {requisito} | {referencia} | " + " | ".join(celdas) + " |")

        fallos = [
            f"- {nombre} · {foto.name}: {lecturas[nombre][foto.name]['error']}"
            for nombre in lecturas
            for foto in fotos
            if lecturas[nombre].get(foto.name, {}).get("error")
        ]
        if fallos:
            lineas += ["", "Errores al leer:", *fallos]

    archivo.write_text("\n".join(lineas) + "\n", "utf-8")


if __name__ == "__main__":
    main()
