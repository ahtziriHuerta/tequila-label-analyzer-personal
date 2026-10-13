
"""Servicio para analizar múltiples imágenes de una misma botella."""

from app.services.ocr import extraer_texto
from app.services.reglas import (
    normalizar,
    detectar_denominacion,
    detectar_categoria,
    detectar_clase,
    detectar_contenido_neto,
    detectar_graduacion_alcoholica,
)


def analizar_imagenes(rutas_imagenes: list) -> dict:
    """
    Analiza múltiples fotografías de una misma botella.

    - Ejecuta OCR por fotografía.
    - Conserva el texto y la confianza de cada imagen.
    - Identifica evidencias por fotografía.
    - Combina los textos obtenidos.
    - Ejecuta el motor de reglas.
    - Devuelve los resultados para FastAPI y el frontend.

    Los resultados representan detecciones automáticas,
    no una certificación de cumplimiento normativo.
    """

    resultados_imagenes = []
    textos = []
    confianzas = []

    # ==========================================
    # 1. PROCESAR FOTOGRAFÍAS
    # ==========================================

    for ruta in rutas_imagenes:

        resultado = extraer_texto(ruta)

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

        confianzas.append(resultado["confianza"])

 
    # ==========================================
    # 2. EVIDENCIAS TEXTUALES POR FOTOGRAFÍA
    # ==========================================

    evidencias = {
        "ET-01": [],
        "ET-02": [],
        "ET-03": [],
    }

    funciones_textuales = {
        "ET-01": detectar_denominacion,
        "ET-02": detectar_categoria,
        "ET-03": detectar_clase,
    }

    for indice, imagen in enumerate(resultados_imagenes):
        texto_imagen = imagen["texto_normalizado"]
        confianza = imagen["confianza"]

        for codigo, funcion in funciones_textuales.items():
            deteccion = funcion(
                texto_imagen,
                confianza_ocr=confianza
            )

            if codigo == "ET-01":
                estado = deteccion
                valor = "TEQUILA" if estado == "Detectado" else None
            else:
                estado = deteccion["estado"]
                valor = deteccion["valor"]

            if estado == "Detectado" or (
                estado == "Revisión manual" and valor is not None
            ):
                evidencias[codigo].append({
                    "numero_imagen": indice + 1,
                    "archivo": imagen["archivo"],
                    "valor_detectado": valor,
                    "estado": estado,
                })
 

    # ==========================================
    # 3. EVIDENCIAS DE VALORES NUMÉRICOS
    # ==========================================

    funciones_numericas = {
        "ET-05": detectar_contenido_neto,
        "ET-07": detectar_graduacion_alcoholica,
    }

    for codigo, funcion in funciones_numericas.items():

        evidencias[codigo] = []

        for indice, imagen in enumerate(resultados_imagenes):

            deteccion = funcion(
                imagen["texto_normalizado"],
                confianza_ocr=imagen["confianza"]
            )

            # Guardamos evidencia cuando la función
            # identifica uno o varios valores.
            if deteccion["valor"] is not None:

                evidencias[codigo].append({
                    "numero_imagen": indice + 1,
                    "archivo": imagen["archivo"],
                    "valor_detectado": deteccion["valor"],
                    "estado": deteccion["estado"],
                })

    # ==========================================
    # 4. COMBINAR TEXTOS
    # ==========================================

    texto_global = " ".join(textos)

    texto_normalizado = normalizar(texto_global)

    confianza_maxima = (
        max(confianzas)
        if confianzas
        else 0.0
    )

    # ==========================================
    # 5. EJECUTAR MOTOR DE REGLAS
    # ==========================================

    et_01 = detectar_denominacion(
        texto_normalizado,
        confianza_ocr=confianza_maxima
    )

    et_02 = detectar_categoria(
        texto_normalizado,
        confianza_ocr=confianza_maxima
    )

    et_03 = detectar_clase(
        texto_normalizado,
        confianza_ocr=confianza_maxima
    )

    et_05 = detectar_contenido_neto(
        texto_normalizado,
        confianza_ocr=confianza_maxima
    )

    et_07 = detectar_graduacion_alcoholica(
        texto_normalizado,
        confianza_ocr=confianza_maxima
    )

    # ==========================================
    # 6. CONSTRUIR RESULTADO FINAL
    # ==========================================

    return {
        "imagenes": resultados_imagenes,

        "evidencias": evidencias,

        "texto_global": texto_global,

        "texto_normalizado": texto_normalizado,

        "confianza_maxima": confianza_maxima,

        "reglas": {
            "ET-01": {
                "requisito": "Denominación",
                "valor": (
                    "TEQUILA"
                    if et_01 == "Detectado"
                    else None
                ),
                "estado": et_01,
            },

            "ET-02": {
                "requisito": "Categoría",
                "valor": et_02["valor"],
                "estado": et_02["estado"],
            },

            "ET-03": {
                "requisito": "Clase",
                "valor": et_03["valor"],
                "estado": et_03["estado"],
            },

            "ET-05": {
                "requisito": "Contenido neto",
                "valor": et_05["valor"],
                "estado": et_05["estado"],
            },

            "ET-07": {
                "requisito": "Graduación alcohólica",
                "valor": et_07["valor"],
                "estado": et_07["estado"],
            },
        },
    }
