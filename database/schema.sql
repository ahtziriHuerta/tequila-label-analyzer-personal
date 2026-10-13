
-- ==========================================
-- BASE DE DATOS
-- ANALIZADOR DE ETIQUETADO DE TEQUILA
-- ==========================================

PRAGMA foreign_keys = ON;


-- ==========================================
-- 1. USUARIOS
-- ==========================================

CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    correo TEXT NOT NULL UNIQUE,
    fecha_registro TEXT NOT NULL
        DEFAULT CURRENT_TIMESTAMP
);


-- ==========================================
-- 2. ANALISIS
-- ==========================================

CREATE TABLE IF NOT EXISTS analisis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL,
    estado TEXT NOT NULL DEFAULT 'Pendiente',
    fecha_creacion TEXT NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

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
