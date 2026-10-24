# 🍹 Analizador de Etiquetado de Tequila

### Sistema de análisis de etiquetas mediante inteligencia artificial y reconocimiento óptico de caracteres

Aplicación web que permite analizar fotografías de etiquetas de botellas de tequila mediante **OCR (Reconocimiento Óptico de Caracteres)** y un motor de reglas para identificar información relacionada con los requisitos de etiquetado establecidos en la **NOM-006-SCFI-2012**.

El sistema facilita la identificación de datos, la revisión de requisitos, la administración de evidencias fotográficas y la generación de reportes.

> **Aviso:** Esta herramienta es un sistema de apoyo para la revisión de etiquetas. Sus resultados no constituyen una certificación oficial de cumplimiento normativo.

---

## 🚀 Características principales

- 📷 **Análisis multimagen:** permite cargar varias fotografías de una misma botella.
- 🧠 **Lectura de fotos:** Gemini (si hay `GEMINI_API_KEY` en `backend/.env`) como lector principal, con PaddleOCR y Tesseract de respaldo. El modelo solo transcribe; las reglas deciden.
- 🔎 **Detección de información:** identifica textos y elementos relevantes del etiquetado.
- 📋 **Validación de requisitos:** evalúa la información mediante reglas automatizadas.
- 🖼️ **Evidencia fotográfica:** relaciona los resultados con las imágenes analizadas.
- ➕ **Agregar evidencia:** permite incorporar nuevas fotografías a un análisis existente.
- ✍️ **Revisión manual:** registra observaciones y decisiones de revisión.
- 💾 **Historial de análisis:** almacena los resultados en SQLite.
- 📄 **Reportes:** permite consultar e imprimir los resultados en PDF.
- 📱 **PWA:** interfaz adaptable a computadoras y dispositivos móviles.
- 🔒 **Finalización:** permite cerrar un análisis para conservarlo en modo de solo lectura.
- 👤 **Cuentas de usuario:** inicio de sesión; cada analista ve sus propios análisis y solo un administrador puede eliminarlos.
- 🧪 **Bloque de pruebas:** análisis de prueba visibles para todo el equipo, para comparar cómo evoluciona la lectura.

## 🛠️ Tecnologías utilizadas

| Componente | Tecnología |
|---|---|
| Lenguaje principal | Python 3.11 |
| Backend | FastAPI |
| Servidor | Uvicorn |
| Frontend | HTML5, CSS3 y JavaScript |
| Aplicación web | Progressive Web App (PWA) |
| Lectura principal | Gemini (API de Google), configurable en `backend/.env` |
| OCR local | PaddleOCR 3.x |
| Motor de procesamiento | PaddlePaddle 3.3.1 |
| OCR alternativo | Tesseract OCR |
| Procesamiento de imágenes | OpenCV |
| Base de datos | SQLite |
| Contraseñas | Argon2id (argon2-cffi) |
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
  +---- Gemini (principal, si hay GEMINI_API_KEY)
  |
  +---- PaddleOCR (respaldo)
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

La herramienta sigue el formato del Consejo Regulador del Tequila **«Requisitos de etiquetado para la NOM-006-SCFI-2012» (MO-RV/20)**
(copia en `docs/CRT_Requisitos_Etiquetado_NOM-006-SCFI-2012.pdf`) y las normas a las que remite: NOM-006, NOM-030 (cantidad),
NOM-142 (etiquetado sanitario) y NOM-106 (contraseña NOM). Las reglas están en `backend/app/services/reglas.py`.

**Antes de las fotos** se captura el encabezado del formato:

| Dato | Cómo se captura | Para qué sirve |
|---|---|---|
| Destino (nacional / exportación) | Selección | Qué datos deben ir en la superficie principal (marcas + y ° del formato) |
| Categoría, clase | Selección (o «leer de la etiqueta») | Se comparan con lo leído |
| Presentación (mL) | Selección de las comunes o captura | Se compara con el contenido neto leído |
| ¿Lleva saborizantes o aditivos? | Selección (No / Sí / No sé) | Con «No», saborizante e ingredientes quedan como N/A |
| Marca, empresa, % Alc. Vol. | Manual | La marca se busca en la etiqueta; el alcohol se compara |
| Inspector, fecha | Automáticos (la cuenta y el día) | — |

Lo declarado **no sustituye** a la etiqueta: si no coincide con lo leído, el requisito pasa a «Revisión manual». Todo se puede
corregir después desde el reporte (se reevalúa sin volver a leer las fotos). Cada foto se envía con su **vista**; la frontal es la
superficie principal de exhibición (NOM-006 11.2.1).

| Código | Renglón del formato | Qué revisa la regla |
|---|---|---|
| ET-01 | Palabra «Tequila» | Palabra completa; no cuenta «Tequila, Jal.» del domicilio |
| ET-02 | Categoría | Las 4 leyendas de 100 % (NOM-006 5.1.1); «Tequila» si se declaró mixto |
| ET-03 | Clase | Blanco/Plata, Joven/Oro, Reposado, Añejo, Extra añejo y sus nombres de exportación |
| ET-04 | Saborizante o colorante | N/A sin aditivos; si los lleva, busca la leyenda |
| ET-05 | Contenido neto | Símbolo mL o L de la Tabla 3 de NOM-030; mL abajo de 1 L |
| ET-07 | Contenido alcohólico | % Alc. Vol. entre 35 y 55 (NOM-006 Tabla 1); fuera de rango = probable error de lectura |
| ET-08 | Nombre o razón social | «Elaborado/Envasado por» y S.A. de C.V., S. de R.L., S.A.P.I. de C.V.… |
| ET-09 | Domicilio | Código postal y entidad federativa (NOM-142 9.3.2.1) |
| ET-10 | Marca registrada | La marca declarada (también lectura aproximada) |
| ET-11 | Hecho en México | «Hecho en México» y análogas; «Product of Mexico» |
| ET-12 | Contraseña oficial (NOM) | «NOM» y número de registro; el diseño (NOM-106) lo verifica el inspector |
| ET-13 | Lote | LOTE, LOT, LT o L + clave (NOM-142 9.3.4.3) |
| ET-14 | Leyenda precautoria | Texto exacto de NOM-142 9.3.7.2.1 |
| ET-19 | Lista de ingredientes | N/A sin aditivos (NOM-142 9.3.7.1) |
| ET-15 | Símbolos | Siempre revisión visual (NOM-142 Apéndice A) |

**Dictamen del inspector:** por cada renglón, *Cumple* Sí / No / N/A, información incorrecta, información correcta
(obligatoria si no cumple, nota *** del formato) y observaciones. El reporte muestra el formato MO-RV/20 lleno y se imprime.

### Clasificación de resultados

Cada requisito puede presentar alguno de los siguientes estados:

- **Detectado:** se encontró evidencia del elemento.
- **No localizado:** no se identificó el elemento requerido.
- **Baja legibilidad:** la calidad de la imagen dificulta la lectura.
- **Imagen adicional requerida:** se necesita otra fotografía para continuar la revisión.
- **Revisión manual:** el resultado requiere confirmación visual.
- **No aplica:** el requisito no aplica según los datos declarados.

La detección automática no equivale por sí sola a una determinación oficial de cumplimiento.

---

## 📁 Estructura del proyecto

```text
tequila-label-analyzer-personal/
|
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── basedatos.py        # conexión y actualización del esquema
│   │   ├── usuarios_cli.py     # crear cuentas desde la terminal
│   │   ├── routers/
│   │   │   ├── analisis.py
│   │   │   └── auth.py         # iniciar/cerrar sesión, contraseña
│   │   └── services/
│   │       ├── seguridad.py    # contraseñas, sesiones, permisos
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
│   │   ├── sesion.js           # menú de usuario, sesión vencida
│   │   └── vistas/             # acceso.js = iniciar sesión y contraseña
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

Para leer las fotos con Gemini, copia `backend/.env.example` como `backend/.env` y pon tu `GEMINI_API_KEY`
(el archivo `.env` no se sube a git). Las fotos se envían a Google: con una clave de nivel gratuito Google puede usar
esos datos, así que no la uses con etiquetas confidenciales.

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

Al arrancar, el servidor crea las tablas que falten y actualiza las bases creadas antes del inicio de sesión (columnas nuevas y tabla `sesiones`). En esa actualización, los análisis que ya existían pasan al **bloque de pruebas**. Haz un respaldo de la base antes de arrancar por primera vez con esta versión.

### 6. Crear la primera cuenta de administrador

No hay registro público: las cuentas las crea un administrador. Desde `backend/`, con la misma `TEQUILA_DB_PATH` que usará el servidor:

```bash
python -m app.usuarios_cli crear --nombre "Nombre Apellido" --correo persona@ejemplo.mx --rol administrador
```

El comando muestra **una sola vez** una contraseña temporal. Entrégala por un medio privado; la app pide cambiarla en el primer acceso. Otros comandos:

| Comando | Para qué |
|---|---|
| `crear --nombre … --correo … [--rol analista\|administrador]` | Cuenta nueva con contraseña temporal |
| `restablecer --correo …` | Contraseña temporal nueva (olvido); cierra sus sesiones |
| `desactivar --correo …` / `activar --correo …` | Quitar o devolver el acceso; desactivar cierra sus sesiones |
| `listar` | Ver las cuentas, su rol y su último acceso |

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

El backend sirve tanto la API como la interfaz web. La aplicación pide iniciar sesión; `/salud` y los archivos de la interfaz son públicos, todo lo demás requiere sesión.

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
49 passed
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
| GET | `/salud` | Estado del backend y OCR (público) |
| POST | `/auth/entrar` | Iniciar sesión (correo y contraseña); abre la sesión en una cookie |
| POST | `/auth/salir` | Cerrar sesión |
| GET | `/auth/yo` | Usuario de la sesión actual |
| POST | `/auth/cambiar-contrasena` | Cambiar la contraseña; cierra las otras sesiones |
| POST | `/analisis/imagenes` | Crear análisis con fotografías (`datos` del formato y `vistas` en JSON; `es_prueba` opcional) |
| GET | `/analisis/historial` | Historial: `?ambito=mios` (predeterminado), `pruebas` o `todos` (administrador, con `usuario_id` opcional) |
| GET | `/analisis/{id}` | Consultar análisis |
| DELETE | `/analisis/{id}` | Eliminar análisis (solo administrador) |
| POST | `/analisis/{id}/imagenes` | Agregar evidencias (`vistas` opcional) |
| PUT | `/analisis/{id}/datos` | Capturar o corregir los datos del formato y reevaluar (sin repetir el OCR) |
| GET / POST | `/analisis/{id}/dictamen` | Dictamen del formato: Sí / No / N/A por requisito |
| POST | `/analisis/{id}/finalizar` | Finalizar análisis |
| GET | `/analisis/{id}/revisiones` | Consultar revisiones |
| POST | `/analisis/{id}/revisiones` | Registrar revisión manual |
| GET | `/imagenes/{id}` | Consultar fotografía almacenada |

La documentación interactiva completa está disponible en `/docs`.

### Cuentas y permisos

| Acción | Analista | Administrador |
|---|---|---|
| Crear análisis, agregar fotos, revisar y finalizar | Los suyos y las pruebas | Todos |
| Ver análisis de otras personas | No | Sí |
| Ver y revisar el bloque de pruebas | Sí | Sí |
| Eliminar análisis | No | Sí |
| Crear cuentas y restablecer contraseñas | No | Sí (`usuarios_cli`) |

Un análisis que el usuario no puede ver responde `404`, igual que si no existiera. Las revisiones manuales quedan a nombre de quien las hace. Mientras dure el desarrollo, *Nuevo análisis* permite marcar el análisis como prueba; se desactiva con `TEQUILA_PRUEBAS_ACTIVAS=0`.

## 🔐 Consideraciones de seguridad

- No publicar credenciales, claves API ni archivos `.env`.
- No subir fotografías privadas al repositorio.
- Mantener los respaldos de SQLite fuera del control de versiones.
- Utilizar entornos virtuales locales.
- Evitar exponer el servidor de desarrollo directamente a internet sin controles de acceso.
- Sesión en el servidor con cookie `HttpOnly` y `SameSite=Lax` (y `Secure` en https); duración de 14 días que se renueva con el uso. La sesión no se guarda en `localStorage`.
- Contraseñas cifradas con Argon2id. Tras 5 intentos fallidos la cuenta espera 15 minutos; también hay un límite por dirección IP.
- Las peticiones que modifican datos se rechazan si vienen de otro sitio, y las respuestas privadas llevan `Cache-Control: no-store`.
- No utilizar el sistema como sustituto de una evaluación normativa oficial.

## 🔮 Mejoras futuras

- Implementar los 13 requisitos de etiquetado restantes.
- Mejorar el reconocimiento de texto en fotografías con reflejos, inclinación o baja resolución.
- Incorporar información estructurada de las vistas de cada botella.
- Ampliar las pruebas automatizadas.
- Mejorar la generación y exportación de reportes.
- Pantalla de administración de usuarios (hoy se usa `usuarios_cli`).
- "Volver a analizar" las pruebas con el código actual para comparar el antes y el después.
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