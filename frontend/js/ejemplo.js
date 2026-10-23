// Análisis de demostración (#/analisis/EJEMPLO) con datos ficticios, en el mismo formato
// que devuelve desdeServidor() en api.js. La interfaz lo marca claramente como ejemplo.
export function analisisEjemplo() {
  const r = (codigo, requisito, estado, valor = null, numeroImagen = null, observacion = null) =>
    ({ codigo, requisito, estado, valor, numeroImagen, observacion });
  return {
    id: "EJEMPLO",
    ejemplo: true,
    estado: "Revisión pendiente",
    finalizado: false,
    autor: "Inspector de ejemplo",
    fecha: new Date().toISOString(),
    datos: {
      destino: "nacional", empresa: "Destilería de Muestra, S.A. de C.V.", marca: "Agave Muestra",
      categoria: "100% de agave", clase: "Reposado", contenido_ml: 750, alcohol: 38, aditivos: "no",
    },
    imagenes: [
      { id: 1, numero: 1, url: null, vista: "frontal", motor: "gemini", confianza: null,
        texto: "AGAVE MUESTRA TEQUILA 100% DE AGAVE REPOSADO 750 ml 38% Alc. Vol." },
      { id: 2, numero: 2, url: null, vista: "posterior", motor: "gemini", confianza: null,
        texto: "NOM 1234 CRT ELABORADO POR: DESTILERIA DE MUESTRA, S.A. DE C.V. ... HECHO EN MEXICO" },
    ],
    evidencias: [],
    resultados: [
      r("ET-01", 'Palabra "Tequila"', "Detectado", "TEQUILA", 1),
      r("ET-02", "Categoría", "Detectado", "100% de agave", 1),
      r("ET-03", "Clase", "Detectado", "Reposado", 1),
      r("ET-04", "Saborizante o colorante", "No aplica", null, null, "Se declaró sin saborizantes ni colorantes."),
      r("ET-05", "Contenido neto", "Detectado", "750 mL", 1),
      r("ET-07", "Contenido alcohólico (% Alc. Vol.)", "Detectado", "38% Alc. Vol.", 1),
      r("ET-08", "Nombre o razón social", "Detectado", "DESTILERIA DE MUESTRA, S.A. DE C.V.", 2),
      r("ET-09", "Domicilio", "Revisión manual", "Jalisco", 2,
        "Domicilio incompleto en la lectura: debe incluir calle, número, C.P. y entidad (NOM-142 9.3.2.1)."),
      r("ET-10", "Marca registrada", "Detectado", "Agave Muestra", 1),
      r("ET-11", "Hecho en México", "Detectado", "HECHO EN MEXICO", 2),
      r("ET-12", "Contraseña oficial (NOM)", "Detectado", "NOM 1234", 2,
        "Verificar el diseño en la foto: letras NOM de al menos 2,5 mm, en negro, gris o blanco, sin sombras (NOM-106-SCFI-2017)."),
      r("ET-13", "Lote", "Imagen adicional requerida", null, null),
      r("ET-14", "Leyenda precautoria", "Baja legibilidad", null, null, "Se leyó parte de la leyenda; confirmar el texto completo."),
      r("ET-19", "Lista de ingredientes", "No aplica", null, null, "Se declaró sin ingredientes ni aditivos añadidos."),
      r("ET-15", "Símbolos", "Revisión manual", null, null,
        "Confirmar en la foto los 3 símbolos: juntos de al menos 7 mm (3,5 mm si el envase es de 500 mL o menos), NOM-142 Apéndice A."),
    ],
    dictamenes: [
      { id: 2, codigo_regla: "ET-14", requisito: "Leyenda precautoria", cumple: "NO",
        informacion_incorrecta: "EL ABUSO DE ESTE PRODUCTO ES NOCIVO",
        informacion_correcta: "EL ABUSO EN EL CONSUMO DE ESTE PRODUCTO ES NOCIVO PARA LA SALUD",
        observaciones: "La leyenda no puede modificarse (NOM-142 9.4.1.1).", usuario: "Inspector de ejemplo", fecha: null },
      { id: 1, codigo_regla: "ET-04", requisito: "Saborizante o colorante", cumple: "NA",
        informacion_incorrecta: "", informacion_correcta: "", observaciones: "", usuario: "Inspector de ejemplo", fecha: null },
    ],
    revisiones: [],
  };
}
