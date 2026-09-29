# Analizador de etiquetado de Tequila (OCR multimagen)

Herramienta de **apoyo** que analiza varias fotografías de una misma botella de tequila,
extrae texto con OCR y clasifica hallazgos (Detectado / No localizado / Baja legibilidad /
Imagen adicional requerida / Revisión manual). **No sustituye una certificación oficial.**

Base normativa: NOM-006-SCFI-2012.

## Stack
| Capa | Tecnología |
|---|---|
| Frontend | HTML, CSS, JavaScript (web responsiva) |
| Backend | Python + FastAPI |
| Imagen | OpenCV |
| OCR | Tesseract (`pytesseract`) al inicio |
| Base de datos | MariaDB / MySQL |
| Reportes | PDF (ReportLab / WeasyPrint) |

## Estructura
```
backend/     API, servicios (preprocesamiento, OCR, motor de reglas)
frontend/    Interfaz web
database/    Esquema SQL y datos semilla
docs/        Documentación y diseño (mockups, diagramas)
```

## Arranque rápido (local)
**Backend**
```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
Abre http://127.0.0.1:8000/docs para ver la API.

**Frontend**: abre `frontend/index.html` (o usa la extensión Live Server de VS Code).

**Base de datos**: crea la BD y ejecuta `database/schema.sql`.

## Equipo y áreas (ajustable)
| Persona | Área principal |
|---|---|
| Marcos | Frontend / UX |
| Atziri | Backend, OCR, motor de reglas (sugerido) |
| Manuel | Base de datos, reportes, integración (sugerido) |

Flujo de trabajo: ver [CONTRIBUTING.md](CONTRIBUTING.md).

## Seguridad (reglas del equipo)
- Nunca subir `.env`, contraseñas ni API keys.
- Todo dato debe pertenecer a una organización (`id_organizacion`) para separar CRT de futuros consejos.
- Fotos de prueba: solo de botellas que podamos compartir.
