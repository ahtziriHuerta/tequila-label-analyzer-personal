# Registro de decisiones
| Fecha | Decisión | Motivo |
|---|---|---|
| 2026-10-05 | Web responsiva instalable (**PWA**) en lugar de app nativa | RNF-02 pide navegadores web; reutiliza todo el frontend; se instala en el celular sin tiendas. Requiere https (túnel o servidor). |
| 2026-10-08 | Base de datos **SQLite** en lugar de MariaDB | Sin instalar servidor de BD; un archivo fácil de compartir para el prototipo. |
| 2026-10-12 | FastAPI sirve el frontend en `/app/` | Un solo puerto y un solo túnel para el celular; la API queda en el mismo origen (sin CORS). |
| 2026-10-12 | Revisión manual separada de las detecciones del OCR | Lo que lee la máquina y lo que decide la persona quedan registrados por separado. |
| 2026-10-12 | Un análisis finalizado queda en solo lectura | El reporte final no cambia después de entregarse. |
| 2026-10-20 | **Login con sesión en el servidor** y cookie `HttpOnly` (no JWT en `localStorage`) | La app y la API comparten origen; la sesión se puede cerrar desde el servidor (desactivar cuenta, cambiar contraseña) y un script inyectado no puede leerla. Contraseñas con Argon2id. |
| 2026-10-20 | Cuentas creadas por un administrador; sin registro público ni recuperación por correo | Herramienta interna; recuperar por correo exige un servidor de correo. El administrador restablece con contraseña temporal y la app obliga a cambiarla. |
| 2026-10-20 | Cada analista ve solo sus análisis; solo el administrador elimina y ve todos | Decisión del equipo. Un análisis ajeno responde 404 para no revelar que existe. |
| 2026-10-20 | Los análisis anteriores al login pasan a un **bloque de pruebas** del equipo | Seguir viendo cómo evoluciona la lectura del OCR con las mismas botellas, sin mezclarlo con el trabajo real. |
| (pendiente) | OCR inicial: Tesseract | Gratis; migrar a Google Vision si la precisión no alcanza (comparativa con 10–20 botellas reales). |
