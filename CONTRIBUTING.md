# Cómo trabajamos

## Ramas
- `main`: siempre estable, lista para demo. **No se hace commit directo**; solo entra por Pull Request.
- `desarrollo-v2`: integración. Aquí se juntan las ramas personales y se prueba todo junto.
- Ramas personales, una por integrante:
  - `dev-ahtziri`: backend, OCR y motor de reglas.
  - `dev-manuel`: base de datos, reportes e integración.
  - `dev-marcos`: frontend / UX.

```
dev-ahtziri ─┐
dev-manuel  ─┼─► desarrollo-v2 ─► main
dev-marcos  ─┘
```

## Ciclo de una tarea
1. Actualiza tu rama con lo último de integración:
   ```bash
   git checkout dev-<tu-nombre>
   git pull
   git merge origin/desarrollo-v2
   ```
2. Commits pequeños con mensajes claros, con la capa al inicio:
   `frontend: agrega pantalla de configuración`, `reglas: detecta ET-13 lote`.
3. `git push` y abre un Pull Request de tu rama hacia `desarrollo-v2`.
4. Otra persona lo revisa y aprueba (corre `pytest` y prueba la app). Se hace merge.
5. Antes de cada demo: PR de `desarrollo-v2` a `main`.

## Antes de abrir un PR
- `cd backend && pytest` pasa.
- La app abre en http://127.0.0.1:8000/app/ y se puede hacer un análisis completo.
- No se cambió `database/tequila.db` sin avisar (tiene datos de prueba del equipo).

## Reglas
- Nunca subir `.env` ni credenciales.
- Si cambias la API, actualiza la tabla de endpoints del README y `frontend/js/api.js`.
- Si agregas una regla ET, súmala también a `REGLAS` en `frontend/js/catalogos.js`.
- Si agregas un archivo al frontend, súmalo a `NUCLEO` en `frontend/sw.js` y sube la versión de `CACHE`.
- Duda bloqueante: ábrela como Issue con etiqueta `duda` y la capa (`ux`, `backend`, `datos`, `infra`).
- Definición de "listo para demo": corre local, sin errores, y se puede mostrar en 2 minutos.
