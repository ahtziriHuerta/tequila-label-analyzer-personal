// Catálogos compartidos. Deben coincidir con backend/app/services/reglas.py y analizador.py.

// Estados del motor de reglas (RNF-07: una lectura fallida NO es incumplimiento).
export const ESTADOS = {
  "Detectado":                  { clase: "detectado", icono: "i-check",      ayuda: "El requisito se localizó en las imágenes." },
  "No localizado":              { clase: "no-local",  icono: "i-search-off", ayuda: "No se encontró el texto; verificar manualmente." },
  "Baja legibilidad":           { clase: "baja",      icono: "i-blur",       ayuda: "La imagen no permite leer el texto con confianza." },
  "Imagen adicional requerida": { clase: "imagen",    icono: "i-image-add",  ayuda: "Falta una vista donde suele aparecer este dato." },
  "Revisión manual":            { clase: "manual",    icono: "i-user-check", ayuda: "Requiere criterio humano (p. ej. símbolos)." },
};

// Estado del análisis completo (columna analisis.estado).
export const FINALIZADO = "Finalizado";

// Resultados permitidos en una revisión manual (CHECK de revisiones_manuales en database/schema.sql).
export const RESULTADOS_REVISION = ["Presente", "Ausente", "No determinado"];

// Vistas sugeridas al fotografiar la botella. Solo guían al usuario: el backend
// todavía no guarda la vista de cada foto (las numera en el orden en que se suben).
export const VISTAS = [
  { id: "frontal",   nombre: "Frontal",   ayuda: "Etiqueta principal completa",      recomendada: true },
  { id: "posterior", nombre: "Posterior", ayuda: "Contraetiqueta con datos legales", recomendada: true },
  { id: "lote",      nombre: "Lote",      ayuda: "Código de lote o fecha impresa",   recomendada: true },
  { id: "lateral",   nombre: "Lateral",   ayuda: "Costados con texto adicional" },
  { id: "cuello",    nombre: "Cuello",    ayuda: "Collarín o etiqueta del cuello" },
  { id: "simbolos",  nombre: "Símbolos",  ayuda: "Logotipos CRT, NOM, reciclaje…" },
  { id: "otra",      nombre: "Otra",      ayuda: "Cualquier otro detalle" },
];

// Reglas que evalúa hoy el backend (5 de las 18 de la matriz ET).
// `vistas` = dónde suele aparecer el dato; sirve para la vista previa de cobertura.
export const REGLAS = [
  { codigo: "ET-01", requisito: "Denominación",          vistas: ["frontal"] },
  { codigo: "ET-02", requisito: "Categoría",             vistas: ["frontal"] },
  { codigo: "ET-03", requisito: "Clase",                 vistas: ["frontal"] },
  { codigo: "ET-05", requisito: "Contenido neto",        vistas: ["frontal", "posterior"] },
  { codigo: "ET-07", requisito: "Graduación alcohólica", vistas: ["frontal", "posterior"] },
];
export const TOTAL_REGLAS_ET = 18;

export const IMAGEN = {
  tiposPermitidos: ["image/jpeg", "image/png", "image/webp"],
  maxBytes: 10 * 1024 * 1024,
  ladoMinimoRecomendado: 1000, // px; por debajo, el OCR suele perder precisión
};
