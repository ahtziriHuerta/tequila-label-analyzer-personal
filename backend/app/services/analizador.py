from __future__ import annotations

"""Servicio para analizar múltiples imágenes de una misma botella."""

import os

from app.services.ocr import extraer_texto as extraer_texto_tesseract
from app.services.reglas import (
    REQUISITOS,
    comparar_con_declarado,
    evaluar,
    normalizar,
    revisar_superficie_principal,
)


# ==========================================
# MOTORES DE LECTURA
# ==========================================

def cadena_motores() -> list[str]:
    """
    Orden en que se intenta leer cada foto; si uno falla, sigue el próximo.

    OCR_MOTOR (backend/.env) elige el primero: "gemini", "paddle" o
    "tesseract". Sin OCR_MOTOR: Gemini si hay GEMINI_API_KEY, si no Paddle.
    """

    from app.services.gemini_ocr import gemini_configurado

    preferido = os.getenv("OCR_MOTOR", "").strip().lower()
    if preferido not in ("gemini", "paddle", "tesseract"):
        preferido = "gemini" if gemini_configurado() else "paddle"

    cadena = {
        "gemini": ["gemini", "paddle", "tesseract"],
        "paddle": ["paddle", "tesseract"],
        "tesseract": ["tesseract"],
    }[preferido]

    if "gemini" in cadena and not gemini_configurado():
        cadena.remove("gemini")

    return cadena


def _leer_con(motor: str, ruta):
    if motor == "gemini":
        from app.services.gemini_ocr import extraer_texto_gemini
        return extraer_texto_gemini(ruta)
    if motor == "paddle":
        from app.services.paddle_ocr import extraer_texto_paddle
        return extraer_texto_paddle(ruta)
    return extraer_texto_tesseract(ruta)


def extraer_texto(ruta):
    """Lee la foto con el primer motor de la cadena que funcione."""

    cadena = cadena_motores()
    for motor in cadena:
        try:
            return _leer_con(motor, ruta)
        except Exception as error:
            if motor == cadena[-1]:
                raise
            print(f"{motor} falló ({error}); se usa el siguiente motor.")


# ==========================================
# ANÁLISIS
# ==========================================

def analizar_imagenes(
    rutas_imagenes: list,
    ocr_previo: dict | None = None,
    vistas: list | None = None,
    datos: dict | None = None
) -> dict:
    """
    Analiza múltiples fotografías de una misma botella.

    - Ejecuta OCR por fotografía.
    - Conserva el texto y la confianza de cada imagen.
    - Identifica evidencias por fotografía.
    - Combina los textos obtenidos.
    - Ejecuta el motor de reglas (formato MO-RV/20 del CRT).
    - Compara con los datos declarados y revisa qué datos
      están en la superficie principal (foto frontal).
    - Devuelve los resultados para FastAPI y el frontend.

    Los resultados representan detecciones automáticas,
    no una certificación de cumplimiento normativo.

    ocr_previo: resultados de OCR ya guardados ({ruta: resultado}).
    Al agregar evidencia solo se lee la foto nueva; las demás
    reutilizan su texto en lugar de volver a pasar por el OCR.

    vistas: vista de cada foto ("frontal", "posterior", ...),
    en el mismo orden que rutas_imagenes.

    datos: datos declarados del formato (destino, categoría,
    clase, contenido_ml, alcohol, marca, aditivos...).
    """

    ocr_previo = ocr_previo or {}
    datos = datos or {}

    resultados_imagenes = []
    textos = []
    confianzas = []

    # ==========================================
    # 1. PROCESAR FOTOGRAFÍAS
    # ==========================================

    for ruta in rutas_imagenes:

        resultado = (
            ocr_previo.get(ruta)
            or extraer_texto(ruta)
        )

        resultados_imagenes.append({
            "archivo": ruta,
            "texto": resultado["texto"],
            "texto_normalizado": normalizar(resultado["texto"]),
            "confianza": resultado["confianza"],
            "version": resultado["version"],
            "psm": resultado["psm"],
            "puntuacion": resultado["puntuacion"],
        })

        if resultado["texto"]:
            textos.append(resultado["texto"])

        # Gemini no da confianza (None): no cuenta para el máximo.
        if resultado["confianza"] is not None:
            confianzas.append(resultado["confianza"])

    # ==========================================
    # 2. EVIDENCIAS POR FOTOGRAFÍA
    # ==========================================

    evidencias = {codigo: [] for codigo in REQUISITOS}

    for indice, imagen in enumerate(resultados_imagenes):
        for codigo in REQUISITOS:
            deteccion = evaluar(
                codigo,
                imagen["texto_normalizado"],
                confianza_ocr=imagen["confianza"],
                datos=datos
            )

            # Se guarda evidencia cuando la foto aporta un valor.
            if deteccion["valor"] is not None:
                evidencias[codigo].append({
                    "numero_imagen": indice + 1,
                    "archivo": imagen["archivo"],
                    "valor_detectado": deteccion["valor"],
                    "estado": deteccion["estado"],
                })

    # ==========================================
    # 3. COMBINAR TEXTOS
    # ==========================================

    texto_global = " ".join(textos)

    texto_normalizado = normalizar(texto_global)

    confianza_maxima = (
        max(confianzas)
        if confianzas
        else None
    )

    # ==========================================
    # 4. EJECUTAR MOTOR DE REGLAS
    # ==========================================

    reglas = {}

    for codigo, requisito in REQUISITOS.items():
        resultado = evaluar(
            codigo,
            texto_normalizado,
            confianza_ocr=confianza_maxima,
            datos=datos
        )

        resultado = comparar_con_declarado(codigo, resultado, datos)

        # Un tequila (mixto) muestra su categoría con la palabra "Tequila".
        fuente = (
            "ET-01"
            if codigo == "ET-02" and resultado["valor"] == "Tequila"
            else codigo
        )

        resultado = revisar_superficie_principal(
            codigo,
            resultado,
            [
                e["numero_imagen"] for e in evidencias[fuente]
                if e["estado"] == "Detectado"
            ],
            vistas,
            datos.get("destino")
        )

        reglas[codigo] = {
            "requisito": requisito["requisito"],
            "valor": resultado["valor"],
            "estado": resultado["estado"],
            "observacion": resultado.get("observacion"),
        }

    # ==========================================
    # 5. CONSTRUIR RESULTADO FINAL
    # ==========================================

    return {
        "imagenes": resultados_imagenes,

        "evidencias": evidencias,

        "texto_global": texto_global,

        "texto_normalizado": texto_normalizado,

        "confianza_maxima": confianza_maxima,

        "reglas": reglas,
    }
