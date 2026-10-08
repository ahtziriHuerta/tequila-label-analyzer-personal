"""RF-05: preprocesamiento adaptativo de imágenes para OCR."""

import cv2


def preprocesar(ruta_imagen: str) -> dict:
    """
    Genera diferentes versiones de una imagen para OCR.

    No modifica la imagen original.
    Permite que el OCR decida posteriormente qué
    procesamiento funciona mejor para cada botella.
    """

    imagen = cv2.imread(ruta_imagen)

    if imagen is None:
        raise ValueError(
            f"No se pudo abrir la imagen: {ruta_imagen}"
        )

    versiones = {}

    # -----------------------------------------
    # 1. ORIGINAL
    # -----------------------------------------
    versiones["original"] = imagen

    # -----------------------------------------
    # 2. ESCALA DE GRISES
    # -----------------------------------------
    gris = cv2.cvtColor(
        imagen,
        cv2.COLOR_BGR2GRAY
    )

    versiones["gris"] = gris

    # -----------------------------------------
    # 3. CLAHE
    # Mejora contraste local.
    # Útil para vidrio, reflejos y letras tenues.
    # -----------------------------------------
    clahe = cv2.createCLAHE(
        clipLimit=2.5,
        tileGridSize=(8, 8)
    )

    versiones["clahe"] = clahe.apply(gris)

    # -----------------------------------------
    # 4. NITIDEZ
    # Resalta bordes sin binarizar la imagen.
    # -----------------------------------------
    suavizada = cv2.GaussianBlur(
        versiones["clahe"],
        (0, 0),
        2
    )

    versiones["nitida"] = cv2.addWeighted(
        versiones["clahe"],
        1.8,
        suavizada,
        -0.8,
        0
    )

    # -----------------------------------------
    # 5. UMBRAL ADAPTATIVO
    # Puede ayudar en etiquetas impresas.
    # -----------------------------------------
    versiones["adaptativa"] = cv2.adaptiveThreshold(
        gris,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        7
    )

    return versiones