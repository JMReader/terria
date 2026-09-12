# TERRIA API

Backend para la administración de campos, publicación de fichas compartibles y motor de timelapse con observaciones satelitales y climáticas.

## Desarrollo

```bash
uv sync --all-groups
uv run fastapi dev app/main.py
```

### Persistencia

- **`DATABASE_URL` configurada** → Supabase Postgres (pooler transaccional `:6543`, `NullPool` + `prepare_threshold=None`). La API escribe en `core.fields`, `timelapse.*` y `ops.jobs`; área/centroide los calcula PostGIS.
- **Sin `DATABASE_URL`** → SQLite local en `TERRIA_DB_PATH` (`data/terria.db`), para desarrollo y tests.

El `owner_id` requerido por `core.fields` se toma de `TERRIA_DEFAULT_OWNER_ID`; si falta, el backend provisiona `TERRIA_SYSTEM_EMAIL` en Supabase Auth vía Admin API (`SUPABASE_SERVICE_ROLE_KEY`).

### Migraciones

El DDL canónico vive en `supabase/migrations/`; Alembic lo ejecuta versionado:

```bash
uv run alembic upgrade head   # aplica pendientes (MIGRATION_DATABASE_URL > DATABASE_DIRECT_URL > DATABASE_URL)
uv run alembic stamp 0001     # si la base ya tiene el schema inicial aplicado
```

La documentación interactiva queda en `http://127.0.0.1:8000/docs`; el contrato estático se genera con:

```bash
uv run python scripts/export_openapi.py
```

## Frontend de diagnóstico de Timelapse

El backend incluye una interfaz de diagnóstico interactiva en HTML/JS nativo para explorar el timelapse, reproducir la serie diaria y visualizar el JSON reactivo:

```text
http://127.0.0.1:8000/debug/timelapse
```

## Procesamiento y CLI de Timelapse

El procesamiento pesado corre fuera del request. Para inicializar datos de prueba o procesar la cola de trabajos:

1. **Sembrar campo y datasets de prueba (Demo sintética + Clima real):**
   ```bash
   uv run python -m app.timelapse.cli seed-demo
   ```

2. **Ejecutar el worker para procesar trabajos encolados:**
   ```bash
   uv run python -m app.timelapse.cli run-worker
   # O para procesar un lote y salir:
   uv run python -m app.timelapse.cli run-worker --once
   ```

3. **Generar un dataset manualmente por línea de comandos:**
   ```bash
   uv run python -m app.timelapse.cli generate --field-id <UUID> --start-date 2024-01-01 --end-date 2024-03-31 --demo
   ```

## Fuentes de datos

- **Clima histórico:** Open-Meteo Historical Weather API (ERA5 Reanalysis). Lluvia diaria, lluvia acumulada inclusiva de 7 días (D-6 a D) y temperaturas mínima/máxima.
- **Satélite Sentinel-2 L2A:** Adaptador preparado para Copernicus Data Space Ecosystem (CDSE). Si no se configuran `CDSE_CLIENT_ID` y `CDSE_CLIENT_SECRET`, el dataset real se genera en modo `partial` con clima real y documentación explícita de la ausencia satelital en `missing_reasons`.
- **Demo sintética:** Dataset visual completo (`is_demo: true`) con curvas de cultivo realistas, huecos temporales para validar el límite de antigüedad (10 días) y assets PNG (RGB y NDVI) generados.

## Endpoints

### Campos (CRUD y pasaporte público)
- `GET /health`
- `POST /v1/fields`
- `GET /v1/fields`
- `GET /v1/fields/{field_id}`
- `PATCH /v1/fields/{field_id}`
- `POST /v1/fields/{field_id}/publish`
- `POST /v1/fields/{field_id}/unpublish`
- `DELETE /v1/fields/{field_id}`
- `GET /v1/public/fields/{public_slug}`

### Timelapse (Privado y Público)
- `POST /v1/fields/{field_id}/timelapses`: Solicitar generación (202 Job encolado / 200 Reuso de dataset listo).
- `GET /v1/timelapse-jobs/{job_id}`: Consultar estado y progreso del job.
- `GET /v1/fields/{field_id}/timelapses`: Listar datasets generados para un campo.
- `GET /v1/fields/{field_id}/timelapses/{dataset_id}`: Manifest privado completo.
- `GET /v1/fields/{field_id}/timelapses/{dataset_id}/frames/{frame_id}`: Detalle de frame.
- `GET /v1/fields/{field_id}/timelapses/{dataset_id}/frames/{frame_id}/assets/{layer}`: Descarga o vista de asset PNG (RGB/NDVI).
- `GET /v1/fields/{field_id}/timelapses/{dataset_id}/timeline-state?date=YYYY-MM-DD`: Estado puntual para una fecha según reglas temporales.
- `POST /v1/fields/{field_id}/timelapses/{dataset_id}/publish`: Vincular timelapse al pasaporte público.
- `GET /v1/public/fields/{public_slug}/timelapse`: Manifest público (omite `field_id` privado).
- `GET /v1/public/fields/{public_slug}/timelapse/frames/{frame_id}/assets/{layer}`: Assets públicos.
- `GET /debug/timelapse`: UI de diagnóstico en HTML/JS nativo.
