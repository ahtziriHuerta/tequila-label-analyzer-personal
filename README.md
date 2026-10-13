# Analizador de etiquetado de Tequila (OCR multimagen)

Herramienta de **apoyo** que analiza varias fotografías de una misma botella de tequila,
extrae texto con OCR y clasifica cada requisito (Detectado / No localizado / Baja legibilidad /
Imagen adicional requerida / Revisión manual). **No sustituye una certificación oficial.**

Base normativa: NOM-006-SCFI-2012.

## Qué hace hoy
| Función | Dónde |
|---|---|
| Asistente de fotos por vista (frontal, posterior, lote…), con cámara directa en el celular | `#/nuevo` |
| OCR adaptativo (varias versiones de la foto y modos de Tesseract) | `backend/app/services/ocr.py` |
| Motor de reglas: **5 de 18** requisitos (ET-01, 02, 03, 05, 07) | `backend/app/services/reglas.py` |
| Reporte por requisito con filtros, evidencia por fotografía e impresión a PDF | `#/analisis/<id>` |
| **Agregar evidencia**: subir otra foto y reevaluar (solo se lee la foto nueva) | Reporte |
| **Revisión manual** por requisito, con historial (no modifica lo detectado por OCR) | Reporte |
| **Finalizar análisis**: queda en solo lectura | Reporte |
| Historial guardado en SQLite, con eliminar | Inicio |
| Configuración: estado del servidor y del OCR | `#/configuracion` |
| **PWA**: instalable en el celular y abre sin red | `frontend/manifest.json`, `frontend/sw.js` |

## Stack
| Capa | Tecnología |
|---|---|
| Frontend | HTML, CSS y JavaScript (módulos ES, sin frameworks); PWA |
| Backend | Python + FastAPI (también sirve el frontend en `/app/`) |
| Imagen | OpenCV |
| OCR | Tesseract (`pytesseract`), idiomas español + inglés |
| Base de datos | SQLite (`database/tequila.db`) |
| Reportes | Impresión del navegador a PDF (ReportLab está en requirements para un PDF del servidor) |

## Estructura
```
backend/
  app/main.py               API: /salud, /imagenes/{id} y el frontend en /app/
  app/routers/analisis.py   Endpoints de análisis, evidencia, revisiones y finalizar
  app/services/             ocr.py, preprocesamiento.py, reglas.py, analizador.py
  tests/                    pytest (la API se prueba con una BD temporal)
frontend/
  index.html  manifest.json  sw.js
  js/app.js                 Navegación (#/...) y PWA
  js/api.js                 Cliente de la API
  js/vistas/                inicio, nuevo, resultado, configuracion
  css/  img/  fonts/
database/   schema.sql, db.py (crea las tablas) y tequila.db
docs/       Decisiones y documentación
```

## Arranque rápido (local)

### 1. Tesseract (una sola vez)
- **Windows:** `winget install UB-Mannheim.TesseractOCR`. El backend lo encuentra en
  `C:\Program Files\Tesseract-OCR` (o indica otra ruta con la variable `TESSERACT_CMD`).
  Falta el español: descarga [`spa.traineddata`](https://github.com/tesseract-ocr/tessdata/raw/main/spa.traineddata)
  y cópialo a `C:\Program Files\Tesseract-OCR\tessdata` (pide permisos de administrador).
- **macOS:** `brew install tesseract tesseract-lang`
- **Linux:** `sudo apt install tesseract-ocr tesseract-ocr-spa`

### 2. Backend + frontend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python ../database/db.py          # solo si no existe database/tequila.db
uvicorn app.main:app --reload
```
- App: **http://127.0.0.1:8000/app/**
- Documentación de la API: http://127.0.0.1:8000/docs
- En **Configuración** debe decir «Tesseract 5.x». Si dice «sin idioma español», falta `spa.traineddata`.

También puedes abrir `frontend/index.html` con Live Server (puerto 5500): la app detecta ese
puerto y usa la API en `:8000`.

### 3. Pruebas
```bash
cd backend
pytest
```

### Probar en el celular (PWA)
El celular exige **https** para instalar la app y usar la cámara. Con el backend encendido:
```bash
cloudflared tunnel --url http://localhost:8000
```
Abre en el celular la URL `https://….trycloudflare.com/app/` que imprime el comando (cambia en cada arranque)
y usa «Instalar app» (Android) o Compartir → «Agregar a inicio» (iPhone).

## API
| Método | Ruta | Uso |
|---|---|---|
| GET | `/salud` | Estado del backend y del OCR |
| POST | `/analisis/imagenes` | Crea un análisis con 1 o más fotos (`archivos`) |
| GET | `/analisis/historial` | Lista de análisis con conteos |
| GET | `/analisis/{id}` | Detalle: imágenes y detecciones |
| DELETE | `/analisis/{id}` | Elimina el análisis, sus fotos y revisiones |
| POST | `/analisis/{id}/imagenes` | Agrega evidencia y reevalúa |
| POST | `/analisis/{id}/finalizar` | Cierra el análisis (solo lectura) |
| GET / POST | `/analisis/{id}/revisiones` | Historial / nueva revisión manual |
| GET | `/imagenes/{id}` | Fotografía original |

## Ramas
| Rama | Responsable | Para qué |
|---|---|---|
| `main` | Equipo | Versión estable para demo. Solo entra por Pull Request. |
| `desarrollo-v2` | Equipo | Integración de la versión 2: aquí se juntan las ramas personales antes de pasar a `main`. |
| `dev-ahtziri` | Ahtziri | Backend, OCR y motor de reglas (p. ej. mejor detección de categoría y clase). |
| `dev-manuel` | Manuel | Base de datos, reportes e integración. |
| `dev-marcos` | Marcos | Frontend / UX: PWA, cámara, diseño, reporte, configuración. |

Flujo de trabajo y reglas: ver [CONTRIBUTING.md](CONTRIBUTING.md).

## Equipo y áreas
| Persona | Área principal |
|---|---|
| Marcos | Frontend / UX |
| Ahtziri | Backend, OCR, motor de reglas |
| Manuel | Base de datos, reportes, integración |

## Pendientes conocidos
- Reglas ET-04, 06 y 08–18 (13 de 18).
- La BD no guarda la vista de cada foto (frontal, posterior…) ni los datos declarados de la botella; el reporte las numera.
- `database/tequila.db` está en git y guarda rutas absolutas de las fotos: en otra computadora
  esas fotos no cargan. Conviene sacarla de git y guardar rutas relativas a `backend/uploads/`.
- Usuario provisional (`sistema@tequila.local`) hasta tener inicio de sesión.

## Seguridad (reglas del equipo)
- Nunca subir `.env`, contraseñas ni API keys.
- Fotos de prueba: solo de botellas que podamos compartir (`backend/uploads/` no se sube).
