# 🍹 Analizador de Etiquetado de Tequila

### Sistema de análisis de etiquetas mediante inteligencia artificial y reconocimiento óptico de caracteres

Aplicación web que permite analizar fotografías de etiquetas de botellas de tequila mediante **OCR (Reconocimiento Óptico de Caracteres)** y un motor de reglas para identificar información relacionada con los requisitos de etiquetado establecidos en la **NOM-006-SCFI-2012**.

El sistema facilita la identificación de datos, la revisión de requisitos, la administración de evidencias fotográficas y la generación de reportes.

> **Aviso:** Esta herramienta es un sistema de apoyo para la revisión de etiquetas. Sus resultados no constituyen una certificación oficial de cumplimiento normativo.

---

## 🚀 Características principales

- 📷 **Análisis multimagen:** permite cargar varias fotografías de una misma botella.
- 🧠 **OCR inteligente:** utiliza PaddleOCR como motor principal y Tesseract como respaldo.
- 🔎 **Detección de información:** identifica textos y elementos relevantes del etiquetado.
- 📋 **Validación de requisitos:** evalúa la información mediante reglas automatizadas.
- 🖼️ **Evidencia fotográfica:** relaciona los resultados con las imágenes analizadas.
- ➕ **Agregar evidencia:** permite incorporar nuevas fotografías a un análisis existente.
- ✍️ **Revisión manual:** registra observaciones y decisiones de revisión.
- 💾 **Historial de análisis:** almacena los resultados en SQLite.
- 📄 **Reportes:** permite consultar e imprimir los resultados en PDF.
- 📱 **PWA:** interfaz adaptable a computadoras y dispositivos móviles.
- 🔒 **Finalización:** permite cerrar un análisis para conservarlo en modo de solo lectura.

## 🛠️ Tecnologías utilizadas

| Componente | Tecnología |
|---|---|
| Lenguaje principal | Python 3.11 |
| Backend | FastAPI |
| Servidor | Uvicorn |
| Frontend | HTML5, CSS3 y JavaScript |
| Aplicación web | Progressive Web App (PWA) |
| OCR principal | PaddleOCR 3.x |
| Motor de procesamiento | PaddlePaddle 3.3.1 |
| OCR alternativo | Tesseract OCR |
| Procesamiento de imágenes | OpenCV |
| Base de datos | SQLite |
| Pruebas automatizadas | Pytest |
| Control de versiones | Git y GitHub |

## 🧠 Funcionamiento del sistema

El proceso de análisis sigue este flujo:

```text
INICIO
  |
  v
Seleccionar fotografías
  |
  v
Cargar imágenes al sistema
  |
  v
Procesamiento de imágenes
  |
  v
Reconocimiento OCR
  |
  +---- PaddleOCR (principal)
  |
  +---- Tesseract (respaldo ante errores)
  |
  v
Extracción y normalización de texto
  |
  v
Evaluación de reglas de etiquetado
  |
  v
Clasificación de resultados
  |
  v
Asociación de evidencias fotográficas
  |
  v
Almacenamiento en SQLite
  |
  v
Visualización del reporte
  |
  +---- Agregar evidencia
  |
  +---- Revisión manual
  |
  +---- Imprimir PDF
  |
  +---- Finalizar análisis
```

## 📋 Requisitos de etiquetado

El proyecto contempla 18 requisitos de evaluación.

Actualmente están implementadas cinco reglas:

| Código | Elemento evaluado | Estado |
|---|---|---|
| ET-01 | Denominación Tequila | Implementado |
| ET-02 | Identificación de agave | Implementado |
| ET-03 | Clase de tequila | Implementado |
| ET-05 | Contenido neto | Implementado |
| ET-07 | Graduación alcohólica | Implementado |

Los demás requisitos se encuentran pendientes de implementación.

### Clasificación de resultados

Cada requisito puede presentar alguno de los siguientes estados:

- **Detectado:** se encontró evidencia del elemento.
- **No localizado:** no se identificó el elemento requerido.
- **Baja legibilidad:** la calidad de la imagen dificulta la lectura.
- **Imagen adicional requerida:** se necesita otra fotografía para continuar la revisión.
- **Revisión manual:** el resultado requiere confirmación visual.

La detección automática no equivale por sí sola a una determinación oficial de cumplimiento.

---

## 📁 Estructura del proyecto

```text
tequila-label-analyzer-personal/
|
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── routers/
│   │   │   └── analisis.py
│   │   └── services/
│   │       ├── paddle_ocr.py
│   │       ├── ocr.py
│   │       ├── preprocesamiento.py
│   │       ├── analizador.py
│   │       └── reglas.py
│   ├── tests/
│   ├── uploads/
│   └── requirements.txt
│
├── frontend/
│   ├── index.html
│   ├── manifest.json
│   ├── sw.js
│   ├── css/
│   ├── js/
│   │   ├── app.js
│   │   ├── api.js
│   │   └── vistas/
│   └── img/
│
├── database/
│   ├── db.py
│   └── schema.sql
│
├── docs/
└── README.md
```

## ⚙️ Instalación

### 1. Requisitos previos

Se recomienda contar con:

- Python 3.11.
- Git.
- Tesseract OCR con soporte para español e inglés.
- Conexión a internet para instalar dependencias y descargar inicialmente los modelos OCR.

**Instalación de Tesseract**

macOS:

```bash
brew install tesseract tesseract-lang
```

Ubuntu/Debian:

```bash
sudo apt update
sudo apt install tesseract-ocr tesseract-ocr-spa tesseract-ocr-eng
```

Windows: instalar Tesseract OCR y comprobar que los idiomas `spa` y `eng` estén disponibles. Si es necesario, configurar la variable `TESSERACT_CMD`.

### 2. Clonar el repositorio

```bash
git clone https://github.com/ahtziriHuerta/tequila-label-analyzer-personal.git

cd tequila-label-analyzer-personal
```

Para utilizar la versión que integra PaddleOCR:

```bash
git switch integracion-marcos-ahtziri
```

### 3. Crear un entorno virtual

En macOS/Linux:

```bash
python3.11 -m venv .venv

source .venv/bin/activate
```

En Windows:

```powershell
py -3.11 -m venv .venv

.venv\Scripts\activate
```

### 4. Instalar dependencias

Desde la raíz del proyecto:

```bash
python -m pip install --upgrade pip

python -m pip install -r backend/requirements.txt
```

**Nota:** La instalación de PaddlePaddle depende de la compatibilidad del sistema operativo y la arquitectura. Consultar la documentación oficial de [PaddlePaddle](https://www.paddlepaddle.org.cn/en/install/quick) si la instalación estándar presenta problemas.

### 5. Inicializar la base de datos

Solo si todavía no existe una base de datos inicializada:

```bash
python database/db.py
```

No ejecutar este paso sobre una base existente sin verificar primero su contenido y contar con un respaldo.

## ▶️ Ejecutar el proyecto

Desde la carpeta principal, con el entorno virtual activado:

```bash
PYTHONPATH=backend python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

En Windows PowerShell:

```powershell
$env:PYTHONPATH="backend"

python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Una vez iniciado, acceder a:

| Servicio | Dirección |
|---|---|
| Aplicación web | http://127.0.0.1:8000/app/ |
| Documentación interactiva | http://127.0.0.1:8000/docs |
| Estado del servidor | http://127.0.0.1:8000/salud |

El backend sirve tanto la API como la interfaz web.

## 🧪 Entorno de pruebas aislado

Para evitar modificar los análisis originales, el sistema permite configurar rutas independientes mediante variables de entorno:

- `TEQUILA_DB_PATH`: ubicación de la base de datos SQLite.
- `TEQUILA_UPLOADS_DIR`: directorio de fotografías.

Ejemplo en macOS/Linux:

```bash
TEQUILA_DB_PATH="$(pwd)/database/tequila_pruebas.db" \
TEQUILA_UPLOADS_DIR="$(pwd)/backend/uploads_pruebas" \
PYTHONPATH=backend \
python -m uvicorn app.main:app --host 127.0.0.1 --port 8002
```

**Importante:** las rutas deben existir y la base de pruebas debe estar inicializada con el esquema correspondiente. Este comando no crea automáticamente una copia de la base original.

## 🧪 Pruebas automatizadas

El proyecto utiliza Pytest para comprobar el funcionamiento de los componentes implementados.

Desde la raíz del repositorio:

```bash
PYTHONPATH=backend python -m pytest backend/tests -q
```

En Windows PowerShell:

```powershell
$env:PYTHONPATH="backend"

python -m pytest backend/tests -q
```

Resultado verificado en el entorno de desarrollo:

```text
31 passed
```

Este resultado corresponde al conjunto de pruebas existente y no implica que todos los requisitos normativos estén implementados.

## 📱 Aplicación web progresiva (PWA)

La interfaz está diseñada para utilizarse desde computadoras, tabletas y teléfonos móviles.

Permite:

- Seleccionar fotografías desde el dispositivo.
- Utilizar la cámara cuando el navegador lo permite.
- Consultar análisis anteriores.
- Revisar evidencias y resultados.
- Instalar la interfaz como aplicación web.

La PWA puede abrir su interfaz sin conexión cuando sus recursos están almacenados en caché, pero **el análisis OCR y las operaciones con la base de datos requieren comunicación con el backend**.

Para utilizar la aplicación desde un teléfono mediante un túnel HTTPS, con el servidor activo:

```bash
cloudflared tunnel --url http://localhost:8000
```

Abrir la URL HTTPS proporcionada y añadir `/app/`.

## 🔌 API REST

| Método | Endpoint | Descripción |
|---|---|---|
| GET | `/salud` | Estado del backend y OCR |
| POST | `/analisis/imagenes` | Crear análisis con fotografías |
| GET | `/analisis/historial` | Consultar historial |
| GET | `/analisis/{id}` | Consultar análisis |
| DELETE | `/analisis/{id}` | Eliminar análisis |
| POST | `/analisis/{id}/imagenes` | Agregar evidencias |
| POST | `/analisis/{id}/finalizar` | Finalizar análisis |
| GET | `/analisis/{id}/revisiones` | Consultar revisiones |
| POST | `/analisis/{id}/revisiones` | Registrar revisión manual |
| GET | `/imagenes/{id}` | Consultar fotografía almacenada |

La documentación interactiva completa está disponible en `/docs`.

## 🔐 Consideraciones de seguridad

- No publicar credenciales, claves API ni archivos `.env`.
- No subir fotografías privadas al repositorio.
- Mantener los respaldos de SQLite fuera del control de versiones.
- Utilizar entornos virtuales locales.
- Evitar exponer el servidor de desarrollo directamente a internet sin controles de acceso.
- No utilizar el sistema como sustituto de una evaluación normativa oficial.

## 🔮 Mejoras futuras

- Implementar los 13 requisitos de etiquetado restantes.
- Mejorar el reconocimiento de texto en fotografías con reflejos, inclinación o baja resolución.
- Incorporar información estructurada de las vistas de cada botella.
- Ampliar las pruebas automatizadas.
- Mejorar la generación y exportación de reportes.
- Incorporar autenticación y gestión de usuarios.
- Optimizar la instalación y ejecución en diferentes plataformas.
- Almacenar rutas relativas de fotografías para facilitar la portabilidad.

## 📚 Referencias

- [NOM-006-SCFI-2012 — Diario Oficial de la Federación](https://www.dof.gob.mx/)
- [Documentación de FastAPI](https://fastapi.tiangolo.com/)
- [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR)
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract)
- [SQLite](https://www.sqlite.org/)

---

**Analizador de Etiquetado de Tequila** — Sistema de apoyo para la revisión automatizada de etiquetas mediante OCR y procesamiento de imágenes.