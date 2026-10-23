// Catálogos compartidos. Deben coincidir con backend/app/services/reglas.py y analizador.py.

// Estados del motor de reglas (RNF-07: una lectura fallida NO es incumplimiento).
export const ESTADOS = {
  "Detectado":                  { clase: "detectado", icono: "i-check",      ayuda: "El requisito se localizó en las imágenes." },
  "No localizado":              { clase: "no-local",  icono: "i-search-off", ayuda: "No se encontró el texto; verificar manualmente." },
  "Baja legibilidad":           { clase: "baja",      icono: "i-blur",       ayuda: "La imagen no permite leer el texto con confianza." },
  "Imagen adicional requerida": { clase: "imagen",    icono: "i-image-add",  ayuda: "Falta una vista donde suele aparecer este dato." },
  "Revisión manual":            { clase: "manual",    icono: "i-user-check", ayuda: "Requiere criterio humano (p. ej. símbolos)." },
  "No aplica":                  { clase: "na",        icono: "i-minus",      ayuda: "No aplica según los datos declarados del producto." },
};

// Estado del análisis completo (columna analisis.estado).
export const FINALIZADO = "Finalizado";

// Resultados de las revisiones manuales anteriores al formato CRT (se siguen mostrando).
export const RESULTADOS_REVISION = ["Presente", "Ausente", "No determinado"];

// Columna "Cumple especificación" del formato MO-RV/20 (CHECK de dictamenes en database/schema.sql).
export const CUMPLE = {
  SI: { nombre: "Sí",  clase: "detectado" },
  NO: { nombre: "No",  clase: "no-local" },
  NA: { nombre: "N/A", clase: "na" },
};

// Vistas de la botella. La frontal es la superficie principal de exhibición (NOM-006 11.2.1).
// Se envían al backend con cada foto.
export const VISTAS = [
  { id: "frontal",   nombre: "Frontal",   ayuda: "Etiqueta principal completa (superficie principal)", recomendada: true },
  { id: "posterior", nombre: "Posterior", ayuda: "Contraetiqueta con datos legales",  recomendada: true },
  { id: "lote",      nombre: "Lote",      ayuda: "Código de lote grabado o impreso",  recomendada: true },
  { id: "cuello",    nombre: "Cuello",    ayuda: "Collarín, sello o etiqueta del cuello" },
  { id: "simbolos",  nombre: "Símbolos",  ayuda: "Pictogramas: menores, embarazo, conducir" },
  { id: "lateral",   nombre: "Lateral",   ayuda: "Costados con texto adicional" },
  { id: "otra",      nombre: "Otra",      ayuda: "Cualquier otro detalle" },
];

// Renglones del formato "Requisitos de etiquetado para la NOM-006-SCFI-2012" (MO-RV/20), en su orden.
// seccion: "apartado11" | "otras" (Otras disposiciones obligatorias).
// superficie: destinos en que debe estar en la superficie principal (marcas + y ° del formato).
// vistas: dónde suele aparecer el dato (vista previa de cobertura).
export const REGLAS = [
  { codigo: "ET-01", requisito: 'Palabra "Tequila"',                  seccion: "apartado11", superficie: ["nacional", "exportacion"], vistas: ["frontal"] },
  { codigo: "ET-02", requisito: "Categoría",                          seccion: "apartado11", superficie: ["nacional", "exportacion"], vistas: ["frontal"] },
  { codigo: "ET-03", requisito: "Clase",                              seccion: "apartado11", superficie: ["nacional", "exportacion"], vistas: ["frontal"] },
  { codigo: "ET-04", requisito: "Saborizante o colorante",            seccion: "apartado11", superficie: ["nacional", "exportacion"], vistas: ["frontal"] },
  { codigo: "ET-05", requisito: "Contenido neto",                     seccion: "apartado11", superficie: ["nacional"], vistas: ["frontal", "posterior"] },
  { codigo: "ET-07", requisito: "Contenido alcohólico (% Alc. Vol.)", seccion: "apartado11", superficie: ["nacional"], vistas: ["frontal", "posterior"] },
  { codigo: "ET-08", requisito: "Nombre o razón social",              seccion: "apartado11", superficie: [], vistas: ["posterior"] },
  { codigo: "ET-09", requisito: "Domicilio",                          seccion: "apartado11", superficie: [], vistas: ["posterior"] },
  { codigo: "ET-10", requisito: "Marca registrada",                   seccion: "apartado11", superficie: ["nacional", "exportacion"], vistas: ["frontal"] },
  { codigo: "ET-11", requisito: "Hecho en México",                    seccion: "apartado11", superficie: [], vistas: ["posterior", "frontal"] },
  { codigo: "ET-12", requisito: "Contraseña oficial (NOM)",           seccion: "apartado11", superficie: [], vistas: ["posterior", "cuello"] },
  { codigo: "ET-13", requisito: "Lote",                               seccion: "apartado11", superficie: [], vistas: ["lote", "posterior", "cuello"] },
  { codigo: "ET-14", requisito: "Leyenda precautoria",                seccion: "apartado11", superficie: [], vistas: ["posterior"] },
  { codigo: "ET-19", requisito: "Lista de ingredientes",              seccion: "otras",      superficie: [], vistas: ["posterior"] },
  { codigo: "ET-15", requisito: "Símbolos",                           seccion: "otras",      superficie: [], vistas: ["posterior", "simbolos"] },
];

export const SECCIONES = {
  apartado11: "Apartado 11 de la norma",
  otras: "Otras disposiciones obligatorias",
};

export const ORDEN_REGLAS = new Map(REGLAS.map((r, i) => [r.codigo, i]));

// ---------- Datos del formato (encabezado del MO-RV/20) ----------
// Selección fija: destino, categoría, clase, presentación (o captura) y aditivos.
// Captura manual: empresa, marca y % Alc. Vol. declarado.
// Automáticos: inspector (la cuenta) y fecha.
export const DESTINOS = [
  { id: "nacional",    nombre: "Nacional" },
  { id: "exportacion", nombre: "Exportación" },
];
export const CATEGORIAS = ["100% de agave", "Tequila"];
export const CLASES = ["Blanco", "Joven", "Reposado", "Añejo", "Extra añejo"];
export const PRESENTACIONES_ML = [50, 200, 375, 700, 750, 950, 1000, 1750];
export const ADITIVOS = [
  { id: "no_se", nombre: "No sé" },
  { id: "no",    nombre: "No" },
  { id: "si",    nombre: "Sí" },
];

export const IMAGEN = {
  tiposPermitidos: ["image/jpeg", "image/png", "image/webp"],
  maxBytes: 10 * 1024 * 1024,
  ladoMinimoRecomendado: 1000, // px; por debajo, el OCR suele perder precisión
};

// Nombre del motor de lectura (columna imagenes.motor_ocr y /salud).
export const MOTORES_OCR = { gemini: "Gemini", paddleocr: "PaddleOCR", tesseract: "Tesseract" };
