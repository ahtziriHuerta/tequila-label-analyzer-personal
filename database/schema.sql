
-- ==========================================
-- BASE DE DATOS
-- ANALIZADOR DE ETIQUETADO DE TEQUILA
-- ==========================================

PRAGMA foreign_keys = ON;


-- ==========================================
-- 1. USUARIOS
-- ==========================================

-- Las cuentas las crea un administrador (backend/app/usuarios_cli.py).
-- contrasena_hash NULL = la cuenta no puede iniciar sesión
-- (p. ej. "Usuario de prueba", dueño de los análisis anteriores al login).
-- Las bases existentes se actualizan al arrancar (app/basedatos.py).

CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    correo TEXT NOT NULL UNIQUE,
    fecha_registro TEXT NOT NULL
        DEFAULT CURRENT_TIMESTAMP,
    contrasena_hash TEXT,
    rol TEXT NOT NULL DEFAULT 'analista'
        CHECK (rol IN ('analista', 'administrador')),
    activo INTEGER NOT NULL DEFAULT 1,
    debe_cambiar_contrasena INTEGER NOT NULL DEFAULT 0,
    intentos_fallidos INTEGER NOT NULL DEFAULT 0,
    bloqueado_hasta TEXT,
    ultimo_acceso TEXT
);


-- ==========================================
-- 1.1 SESIONES
-- ==========================================
-- Solo se guarda el hash del token; el token viaja
-- en una cookie HttpOnly.

CREATE TABLE IF NOT EXISTS sesiones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token_hash TEXT NOT NULL UNIQUE,
    usuario_id INTEGER NOT NULL,
    creada TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expira TEXT NOT NULL,
    ultimo_uso TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    agente TEXT,

    FOREIGN KEY (usuario_id)
        REFERENCES usuarios(id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_sesiones_usuario
ON sesiones(usuario_id);


-- ==========================================
-- 2. ANALISIS
-- ==========================================

CREATE TABLE IF NOT EXISTS analisis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL,
    estado TEXT NOT NULL DEFAULT 'Pendiente',
    fecha_creacion TEXT NOT NULL
        DEFAULT CURRENT_TIMESTAMP,
    -- 1 = análisis de prueba: visible para todo el equipo
    -- y fuera de las métricas personales.
    es_prueba INTEGER NOT NULL DEFAULT 0,

    -- Datos del formato CRT "Requisitos de etiquetado" (MO-RV/20).
    -- Los captura quien analiza; NULL = no se declaró.
    destino TEXT
        CHECK (destino IN ('nacional', 'exportacion')),
    empresa TEXT,
    marca TEXT,
    categoria TEXT,
    clase TEXT,
    contenido_ml REAL,
    alcohol REAL,
    -- 'si', 'no' o 'no_se': decide si aplican saborizantes e ingredientes.
    aditivos TEXT,

    FOREIGN KEY (usuario_id)
        REFERENCES usuarios(id)
        ON DELETE RESTRICT
);


-- ==========================================
-- 3. IMAGENES
-- ==========================================

CREATE TABLE IF NOT EXISTS imagenes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analisis_id INTEGER NOT NULL,
    nombre_archivo TEXT NOT NULL,
    ruta_archivo TEXT NOT NULL,
    texto_ocr TEXT,
    confianza_ocr REAL,
    -- 'paddleocr' o 'tesseract'; permite comparar motores en las pruebas.
    motor_ocr TEXT,
    -- Vista de la botella: frontal, posterior, lote, lateral, cuello,
    -- simbolos u otra. La frontal es la superficie principal de exhibición.
    vista TEXT,
    fecha_carga TEXT NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (analisis_id)
        REFERENCES analisis(id)
        ON DELETE CASCADE
);


-- ==========================================
-- 4. REGLAS
-- ==========================================

CREATE TABLE IF NOT EXISTS reglas (
    codigo TEXT PRIMARY KEY,
    requisito TEXT NOT NULL,
    descripcion TEXT
);


-- ==========================================
-- 5. DETECCIONES
-- ==========================================

CREATE TABLE IF NOT EXISTS detecciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analisis_id INTEGER NOT NULL,
    imagen_id INTEGER,
    codigo_regla TEXT NOT NULL,
    valor TEXT,
    estado TEXT NOT NULL,
    -- Explicación de la regla (formato, comparación con lo declarado...).
    observacion TEXT,
    fecha_deteccion TEXT NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (analisis_id)
        REFERENCES analisis(id)
        ON DELETE CASCADE,

    FOREIGN KEY (imagen_id)
        REFERENCES imagenes(id)
        ON DELETE SET NULL,

    FOREIGN KEY (codigo_regla)
        REFERENCES reglas(codigo)
        ON DELETE RESTRICT
);

-- ==========================================
-- EVIDENCIAS POR FOTOGRAFÍA
-- ==========================================

-- ==========================================
-- EVIDENCIAS POR FOTOGRAFIA
-- ==========================================

CREATE TABLE IF NOT EXISTS evidencias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    deteccion_id INTEGER NOT NULL,
    imagen_id INTEGER NOT NULL,
    valor_detectado TEXT,
    estado TEXT NOT NULL,

    FOREIGN KEY (deteccion_id)
        REFERENCES detecciones(id)
        ON DELETE CASCADE,

    FOREIGN KEY (imagen_id)
        REFERENCES imagenes(id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_evidencias_deteccion
ON evidencias(deteccion_id);

CREATE INDEX IF NOT EXISTS idx_evidencias_imagen
ON evidencias(imagen_id);

-- ==========================================
-- INDICES
-- ==========================================

CREATE INDEX IF NOT EXISTS idx_analisis_usuario
ON analisis(usuario_id);

CREATE INDEX IF NOT EXISTS idx_imagenes_analisis
ON imagenes(analisis_id);

CREATE INDEX IF NOT EXISTS idx_detecciones_analisis
ON detecciones(analisis_id);

CREATE INDEX IF NOT EXISTS idx_detecciones_regla
ON detecciones(codigo_regla);



-- ==========================================
-- 6. REVISIONES MANUALES
-- ==========================================

CREATE TABLE IF NOT EXISTS revisiones_manuales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    analisis_id INTEGER NOT NULL,
    codigo_regla TEXT NOT NULL,
    usuario_id INTEGER NOT NULL,

    resultado TEXT NOT NULL
        CHECK (
            resultado IN (
                'Presente',
                'Ausente',
                'No determinado'
            )
        ),

    observaciones TEXT,

    fecha_revision TEXT NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (analisis_id)
        REFERENCES analisis(id)
        ON DELETE CASCADE,

    FOREIGN KEY (codigo_regla)
        REFERENCES reglas(codigo)
        ON DELETE RESTRICT,

    FOREIGN KEY (usuario_id)
        REFERENCES usuarios(id)
        ON DELETE RESTRICT
);


-- ==========================================
-- INDICES DE REVISIONES
-- ==========================================

CREATE INDEX IF NOT EXISTS idx_revisiones_analisis
ON revisiones_manuales(analisis_id);

CREATE INDEX IF NOT EXISTS idx_revisiones_regla
ON revisiones_manuales(codigo_regla);

CREATE INDEX IF NOT EXISTS idx_revisiones_usuario
ON revisiones_manuales(usuario_id);

CREATE INDEX IF NOT EXISTS idx_revisiones_fecha
ON revisiones_manuales(fecha_revision);


-- ==========================================
-- 7. DICTAMEN DEL FORMATO CRT (MO-RV/20)
-- ==========================================
-- Lo que marca el inspector por requisito: cumple SI / NO / N/A,
-- la información incorrecta, cómo debe decir y observaciones.
-- Se guarda el historial; vale el más reciente de cada requisito.

CREATE TABLE IF NOT EXISTS dictamenes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analisis_id INTEGER NOT NULL,
    codigo_regla TEXT NOT NULL,
    usuario_id INTEGER NOT NULL,
    cumple TEXT NOT NULL
        CHECK (cumple IN ('SI', 'NO', 'NA')),
    informacion_incorrecta TEXT,
    informacion_correcta TEXT,
    observaciones TEXT,
    fecha TEXT NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (analisis_id)
        REFERENCES analisis(id)
        ON DELETE CASCADE,

    FOREIGN KEY (codigo_regla)
        REFERENCES reglas(codigo)
        ON DELETE RESTRICT,

    FOREIGN KEY (usuario_id)
        REFERENCES usuarios(id)
        ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_dictamenes_analisis
ON dictamenes(analisis_id);
