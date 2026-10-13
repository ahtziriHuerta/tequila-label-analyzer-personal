# Registro de decisiones
| Fecha | Decisión | Motivo |
|---|---|---|
| 2026-10-05 | Web responsiva instalable (**PWA**) en lugar de app nativa | RNF-02 pide navegadores web; reutiliza todo el frontend; se instala en el celular sin tiendas. Requiere https (túnel o servidor). |
| 2026-10-08 | Base de datos **SQLite** en lugar de MariaDB | Sin instalar servidor de BD; un archivo fácil de compartir para el prototipo. |
| 2026-10-12 | FastAPI sirve el frontend en `/app/` | Un solo puerto y un solo túnel para el celular; la API queda en el mismo origen (sin CORS). |
| 2026-10-12 | Revisión manual separada de las detecciones del OCR | Lo que lee la máquina y lo que decide la persona quedan registrados por separado. |
| 2026-10-12 | Un análisis finalizado queda en solo lectura | El reporte final no cambia después de entregarse. |
| (pendiente) | OCR inicial: Tesseract | Gratis; migrar a Google Vision si la precisión no alcanza (comparativa con 10–20 botellas reales). |
