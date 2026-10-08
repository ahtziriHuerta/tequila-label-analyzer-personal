import cv2
import pytesseract

ARCHIVO = "prueba1.jpeg"

imagen = cv2.imread(ARCHIVO)

if imagen is None:
    raise ValueError(f"No se pudo abrir {ARCHIVO}")

alto, ancho = imagen.shape[:2]

print("Resolución original:", ancho, "x", alto)

# Nos concentramos en la zona central/superior,
# donde normalmente se encuentra el texto principal.
x1 = int(ancho * 0.15)
x2 = int(ancho * 0.85)

y1 = int(alto * 0.10)
y2 = int(alto * 0.60)

recorte = imagen[y1:y2, x1:x2]

# Aumentar tamaño
recorte = cv2.resize(
    recorte,
    None,
    fx=3,
    fy=3,
    interpolation=cv2.INTER_CUBIC
)

# Escala de grises
gris = cv2.cvtColor(
    recorte,
    cv2.COLOR_BGR2GRAY
)

# Contraste local
clahe = cv2.createCLAHE(
    clipLimit=4.0,
    tileGridSize=(8, 8)
)

contraste = clahe.apply(gris)

# Realce de detalles
blur = cv2.GaussianBlur(
    contraste,
    (0, 0),
    2
)

nitida = cv2.addWeighted(
    contraste,
    2.0,
    blur,
    -1.0,
    0
)

cv2.imwrite(
    "resultado_zona_grabado.jpg",
    nitida
)

print("\n===== OCR ZONA GRABADO =====")

for psm in (6, 11, 12, 13):
    texto = pytesseract.image_to_string(
        nitida,
        lang="spa+eng",
        config=f"--oem 3 --psm {psm}"
    )

    print(f"\n--- PSM {psm} ---")
    print(texto.strip())

print(
    "\nImagen generada: "
    "resultado_zona_grabado.jpg"
)