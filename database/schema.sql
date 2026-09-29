-- Basado en la sección 11 de la documentación + id_organizacion (separación entre consejos: CRT, otros)
CREATE DATABASE IF NOT EXISTS tequila_analyzer CHARACTER SET utf8mb4;
USE tequila_analyzer;

CREATE TABLE organizacion (
  id_organizacion INT AUTO_INCREMENT PRIMARY KEY,
  nombre VARCHAR(120) NOT NULL          -- ej. CRT
);

CREATE TABLE usuario (
  id_usuario INT AUTO_INCREMENT PRIMARY KEY,
  id_organizacion INT NOT NULL,
  nombre VARCHAR(120) NOT NULL,
  correo VARCHAR(160) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,   -- nunca guardar contraseñas en texto plano
  rol ENUM('admin','revisor','lectura') NOT NULL DEFAULT 'revisor',
  FOREIGN KEY (id_organizacion) REFERENCES organizacion(id_organizacion)
);

CREATE TABLE analisis (
  id_analisis INT AUTO_INCREMENT PRIMARY KEY,
  id_organizacion INT NOT NULL,
  id_usuario INT NOT NULL,
  fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
  observaciones TEXT,
  estado_general VARCHAR(40),
  FOREIGN KEY (id_organizacion) REFERENCES organizacion(id_organizacion),
  FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario)
);

CREATE TABLE imagen (
  id_imagen INT AUTO_INCREMENT PRIMARY KEY,
  id_analisis INT NOT NULL,
  tipo_vista ENUM('frontal','posterior','lateral','cuello','tapa','lote','simbolos','otra') NOT NULL,
  archivo VARCHAR(255) NOT NULL,
  texto_ocr MEDIUMTEXT,                  -- texto original sin normalizar (trazabilidad)
  calidad DECIMAL(5,2),
  fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (id_analisis) REFERENCES analisis(id_analisis)
);

CREATE TABLE regla (
  id_regla INT AUTO_INCREMENT PRIMARY KEY,
  codigo VARCHAR(10) NOT NULL UNIQUE,    -- ET-01 ... ET-18
  requisito VARCHAR(80) NOT NULL,
  descripcion VARCHAR(255),
  tipo_revision VARCHAR(40)              -- Automática / Manual / Visión...
);

CREATE TABLE deteccion (
  id_deteccion INT AUTO_INCREMENT PRIMARY KEY,
  id_imagen INT NOT NULL,
  id_regla INT NOT NULL,
  valor_detectado VARCHAR(255),
  confianza DECIMAL(5,2),
  estado ENUM('Detectado','No localizado','Imagen adicional requerida','Baja legibilidad','Revisión manual') NOT NULL,
  observacion VARCHAR(255),
  FOREIGN KEY (id_imagen) REFERENCES imagen(id_imagen),
  FOREIGN KEY (id_regla) REFERENCES regla(id_regla)
);

INSERT INTO regla (codigo, requisito, tipo_revision) VALUES
('ET-01','Denominación','Automática'),('ET-02','Categoría','Automática'),
('ET-03','Clase','Automática'),('ET-05','Contenido neto','Automática'),
('ET-07','Alcohol % Alc. Vol.','Automática'),('ET-11','Origen','Automática'),
('ET-13','Lote','OCR + evidencia'),('ET-14','Leyenda precautoria','Automática'),
('ET-15','Símbolos','Visión/manual'),('ET-16','D.O.P.','Automática');
