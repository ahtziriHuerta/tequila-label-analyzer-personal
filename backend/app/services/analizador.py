
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


def analizar_imagenes(
    rutas_imagenes: list,
    ocr_previo: dict | None = None
) -> dict:
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

    ocr_previo: resultados de OCR ya guardados ({ruta: resultado}).
    Al agregar evidencia solo se lee la foto nueva; las demás
    reutilizan su texto en lugar de volver a pasar por Tesseract.
    """

    ocr_previo = ocr_previo or {}

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

        confianzas.append(resultado["confianza"])

    # ==========================================
    # 2. EVIDENCIAS TEXTUALES POR FOTOGRAFÍA
    # ==========================================

    evidencias = {}

    terminos_por_regla = {
        "ET-01": [
            "TEQUILA",
        ],
        "ET-02": [
            "100% DE AGAVE",
            "100 % DE AGAVE",
            "100% AGAVE",
            "100 % AGAVE",
        ],
        "ET-03": [
            "EXTRA ANEJO",
            "REPOSADO",
            "ANEJO",
            "BLANCO",
            "PLATA",
            "JOVEN",
            "ORO",
        ],
    }

    for codigo, terminos in terminos_por_regla.items():

        evidencias[codigo] = []

        for indice, imagen in enumerate(resultados_imagenes):

            texto_imagen = imagen["texto_normalizado"]

            encontrados = [
                termino
                for termino in terminos
                if termino in texto_imagen
            ]

            if encontrados:

                evidencias[codigo].append({
                    "numero_imagen": indice + 1,
                    "archivo": imagen["archivo"],
                    "texto_detectado": encontrados,
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
