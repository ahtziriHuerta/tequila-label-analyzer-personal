# Cómo trabajamos

## Ramas
- `main`: siempre estable, lista para demo (jueves/viernes). No se hace commit directo.
- `develop`: integración semanal.
- `feature/<area>-<tema>`: una por tarea. Ej.: `feature/frontend-pantalla-datos`, `feature/backend-ocr`, `feature/db-esquema`.

## Ciclo de una tarea
1. Toma una tarjeta del tablero (GitHub Projects) y muévela a "En progreso".
2. `git checkout develop && git pull` y luego `git checkout -b feature/...`
3. Commits pequeños con mensajes claros: `frontend: agrega pantalla Datos de la botella`
4. `git push -u origin feature/...` y abre un Pull Request hacia `develop`.
5. Otra persona lo revisa y aprueba. Se hace merge.
6. Antes de cada demo: PR de `develop` a `main`.

## Reglas
- Nunca subir `.env` ni credenciales.
- Duda bloqueante: ábrela como Issue con etiqueta `duda` y la capa (`ux`, `backend`, `datos`, `infra`).
- Definición de "listo para demo": corre local, sin errores, y se puede mostrar en 2 minutos.
