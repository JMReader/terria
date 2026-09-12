# TERRIA API

Backend inicial para que un propietario administre campos y publique una ficha compartible.

## Desarrollo

```bash
uv sync --all-groups
uv run fastapi dev app/main.py
```

La documentación interactiva queda en `http://127.0.0.1:8000/docs`; el contrato estático se genera con:

```bash
uv run python scripts/export_openapi.py
```

Mientras no exista configuración de Supabase, el proyecto usa un repositorio de memoria exclusivamente para desarrollo y pruebas. No debe desplegarse con ese modo. La integración con Supabase, migraciones PostGIS y validación de JWT son la siguiente tarea de backend.

## API inicial

- `GET /health`
- `POST /v1/fields`
- `GET /v1/fields`
- `GET /v1/fields/{field_id}`
- `PATCH /v1/fields/{field_id}`
- `POST /v1/fields/{field_id}/publish`
- `POST /v1/fields/{field_id}/unpublish`
- `DELETE /v1/fields/{field_id}`
- `GET /v1/public/fields/{public_slug}`
