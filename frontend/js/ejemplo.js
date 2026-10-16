// Análisis de demostración (#/analisis/EJEMPLO) con datos ficticios, en el mismo formato
// que devuelve desdeServidor() en api.js. La interfaz lo marca claramente como ejemplo.
export function analisisEjemplo() {
  return {
    id: "EJEMPLO",
    ejemplo: true,
    estado: "Revisión pendiente",
    finalizado: false,
    fecha: new Date().toISOString(),
    imagenes: [
      { id: 1, numero: 1, url: null, confianza: 87.4, texto: "TEQUILA 100% DE AGAVE REPOSADO 750 ml" },
      { id: 2, numero: 2, url: null, confianza: 52.1, texto: "38% Alc. Vol. HECHO EN MEXICO" },
    ],
    resultados: [
      { codigo: "ET-01", requisito: "Denominación",          valor: "TEQUILA",       estado: "Detectado",        numeroImagen: 1 },
      { codigo: "ET-02", requisito: "Categoría",             valor: "100% DE AGAVE", estado: "Detectado",        numeroImagen: 1 },
      { codigo: "ET-03", requisito: "Clase",                 valor: "REPOSADO",      estado: "Detectado",        numeroImagen: 1 },
      { codigo: "ET-05", requisito: "Contenido neto",        valor: "750 ML",        estado: "Detectado",        numeroImagen: 1 },
      { codigo: "ET-07", requisito: "Graduación alcohólica", valor: "38% ALC. VOL.", estado: "Baja legibilidad", numeroImagen: 2 },
    ],
    revisiones: [
      { id: 1, codigo_regla: "ET-07", requisito: "Graduación alcohólica", resultado: "Presente",
        observaciones: "Se lee 38 % Alc. Vol. en la contraetiqueta; el reflejo dificulta el OCR.",
        fecha_revision: null },
    ],
  };
}
