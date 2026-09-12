# Timelapse — especificación técnica v0.2

Estado: propuesta implementable. Fecha: 2026-09-12. Autor: korita.
Base inspeccionada: backend `terria`, commit `1ddcabd`. Alcance: documentación, sin implementación de endpoints ni infraestructura.

## 1. Integración con el proyecto existente

El proyecto usa Python 3.12, FastAPI 0.128 y Pydantic. `app/main.py` expone `/v1/fields` y `/v1/public/fields/{public_slug}`. `app/schemas.py` define PolygonGeometry, FieldResponse y StrictModel. `app/store.py` usa InMemoryFieldStore; aún no implementa persistencia, owner_id ni autenticación. La decisión de equipo define Supabase/PostGIS/Auth y API en Vercel.

Este documento reemplaza las rutas orientativas `/api/v1/parcels` del borrador por `/v1/fields` y mantiene snake_case. Los campos existentes son parcelas; la ficha pública es el pasaporte. No crear un segundo CRUD de parcelas.

Dependencias previas: persistencia y validación JWT para uso compartido; geometría versionada; worker persistente para ingesta. El repositorio en memoria sólo sirve para fixtures y pruebas locales. La validación actual sólo comprueba el anillo exterior y el área es aproximada; validar todos los anillos, geometría no vacía y no autointersectada. Al actualizar boundary, reconstruir PolygonGeometry antes de calcular superficie (model_dump produce un dict en el código actual).

## 2. Alcance y datos de la primera entrega

Una parcela, período histórico de hasta 366 días, capas RGB/NDVI y serie diaria de lluvia/temperatura. No hay identificación automática de semillas, rendimiento, diagnóstico hídrico ni altura real de plantas.

| Salida | Fuente concreta | Obtención y semántica |
|---|---|---|
| boundary, area_hectares | Campo y versión PostGIS | WGS84; área geodésica en hectáreas |
| rgb | CDSE Sentinel Hub, Sentinel-2 L2A | Process API, bandas B04/B03/B02, imagen RGBA |
| ndvi | Mismas capturas | `(B08-B04)/(B08+B04)`; raster y media/p10/p90 |
| valid_area_fraction | Máscara local del lote | Área observable / área total, entre 0 y 1 |
| precipitation_mm | Open-Meteo Historical Weather, ERA5 | `precipitation_sum`, mm/día |
| precipitation_7d_mm | Cálculo backend | Suma inclusiva D-6 a D; null si ventana incompleta |
| temperature_min_c/max_c | Misma API climática | `temperature_2m_min/max`, °C |

Sentinel-2: RGB/NIR a 10 m; SCL a 20 m. El filtro de nubes del catálogo es por tile: no reemplaza la máscara del lote. [Bandas y producto](https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/S2L2A.html).

La selección de escenas usa [STAC Catalog](https://documentation.dataspace.copernicus.eu/APIs/STAC.html) y las capas se producen con [Process API](https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Process.html). En la implementación actual, media/p10/p90 de NDVI se derivan del raster NDVI RGBA procesado para el lote (por eso son cuantizados a 8 bits); una siguiente iteración puede sustituirlas por la Statistical API con máscara analítica. Autenticación [OAuth del proveedor](https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Overview/Authentication.html) exclusivamente en worker. Validar cuotas con la cuenta real; datos abiertos no implican procesamiento ilimitado.

Clima: `GET https://archive-api.open-meteo.com/v1/archive`, parámetros latitude, longitude, start_date, end_date, daily, models=era5 y timezone del campo. La ingesta comienza 6 días antes del período. Guardar también coordenadas de la celda devuelta. Son estimaciones regionales de reanálisis; no colorear subzonas de la parcela con ese dato. [Documentación](https://open-meteo.com/en/docs/historical-weather-api).

Prueba ya realizada: consulta Córdoba (-31.4,-64.2), 01–03/01/2025 devolvió lluvia y temperatura. Pendiente comprobar tres escenas satelitales autenticadas sobre el campo demo. No sustituir datos faltantes con mock sin etiquetarlo.

## 3. Arquitectura propuesta

FastAPI valida acceso, crea jobs y sirve resultados. Worker Python externo al request consume jobs persistidos, consulta proveedores, genera assets y publica datasets. Para desarrollo: comando CLI de worker; para uso continuo: proceso en contenedor con reinicio automático. El proveedor de alojamiento del worker queda por elegir; no bloquea contrato ni ejecución local.

Persistencia: Supabase PostgreSQL/PostGIS para registros y geometría; bucket privado Supabase Storage para imágenes. [PostGIS](https://supabase.com/docs/guides/database/extensions/postgis) y [Storage privado](https://supabase.com/docs/guides/storage/buckets/fundamentals). API y worker comparten interfaces de repositorio, nunca un diccionario en memoria en producción. Usar migraciones reproducibles.

Se propone una tabla de jobs con toma transaccional de trabajo y lease, evitando añadir otro broker en este corte. La transacción de toma termina antes de llamar proveedores. Worker renueva lease; reclaim de lease vencido; cada finalización compara lease_token para impedir que un worker antiguo publique. Tres intentos para errores transitorios, backoff con jitter y respeto de Retry-After; credenciales inválidas producen error accionable. No ejecutar ingesta mediante BackgroundTasks de FastAPI: trabajo pesado debe sobrevivir al request. [Guía FastAPI](https://fastapi.tiangolo.com/tutorial/background-tasks/).

## 4. Modelo de datos

| Entidad propuesta | Campos principales y restricciones |
|---|---|
| field_geometry_versions | id UUID, field_id, boundary Polygon/4326, geometry_hash, area_hectares, created_at; inmutable |
| timelapse_jobs | id, field_id, geometry_version_id, request_hash, status, progress, attempts, lease_token, lease_until, error_code, created_at; deduplicar jobs activos por request_hash |
| timelapse_datasets | id UUID, field_id, geometry_version_id, start_date, end_date, timezone, processing_version, status, generated_at; identificador inmutable de versión |
| timelapse_frames | id, dataset_id, observed_at UTC, local_date, source_item_ids, usable, valid_area_fraction, ndvi_mean/p10/p90 nullable; orden estable por observed_at/id |
| timelapse_assets | id, frame_id, layer, object_key, bbox, crs, resolution_m, width, height, sha256; unique(frame_id,layer) |
| timelapse_weather_daily | dataset_id, date, precipitation_mm, precipitation_7d_mm, temperature_min_c/max_c, source_id, missing_reason; unique(dataset_id,date) |
| timelapse_sources | id, dataset_id, provider, collection, request_parameters sin secretos, item_ids, model, retrieval_time, source_resolution, attribution, processing_version |
| field_public_timelapse | field_id, dataset_id, published_at; referencia explícita al dataset compartido |

Índices en FKs de consulta, dataset/fecha y jobs(status,lease_until). Proteger por propietario del campo en API; RLS en tablas expuestas, sin acceso anónimo directo a fuentes ni jobs. La conexión privilegiada no debe suponerse protegida por auth.uid(): aplicar autorización de propietario explícita y probar aislamiento. JWT: firma, issuer, audience y expiración. Valores meteorológicos/índices faltantes son null; 0 es dato válido.

Editar boundary crea otra versión, invalida el puntero al timelapse publicado y requiere nuevo dataset. La historia previa se conserva. Unpublish impide nuevos accesos públicos; URLs firmadas ya emitidas pueden seguir válidas hasta su expiración (propuesta: 5 minutos).

## 5. Contrato HTTP

| Método y ruta nueva | Resultado |
|---|---|
| POST /v1/fields/{field_id}/timelapses | 202 job creado/existente; 200 si ya existe dataset listo idéntico |
| GET /v1/timelapse-jobs/{job_id} | Estado autorizado, progress 0..1, dataset_id si disponible |
| GET /v1/fields/{field_id}/timelapses/{dataset_id} | Manifest privado, sólo si dataset pertenece al campo |
| GET /v1/fields/{field_id}/timelapses/{dataset_id}/frames/{frame_id} | Métricas y URLs renovadas de assets |
| POST /v1/fields/{field_id}/timelapses/{dataset_id}/publish | Vincula dataset ready/partial a ficha ya pública y geometría actual |
| GET /v1/public/fields/{public_slug}/timelapse | Manifest del dataset publicado; 404 si no existe/no público |
| GET /v1/public/fields/{public_slug}/timelapse/frames/{frame_id} | Assets sólo del dataset publicado tras validar visibilidad |

POST body: `{ "start_date": "2025-01-01", "end_date": "2025-12-31", "layers": ["rgb", "ndvi"] }`. El backend fija geometry_version y timezone; no acepta owner_id del navegador. Idempotencia por field_id+geometry_hash+fechas+capas ordenadas+processing_version. Misma solicitud en progreso retorna mismo job. Reintento tras failed crea nuevo intento con límite; ready siempre se reutiliza.

Errores: 401 sin identidad válida; 404 ausente/no autorizado; 409 conflicto de publicación o geometría; 422 período/forma inválida; 429 límite de trabajos. Adoptar envelope actual `detail: {code,message,request_id}` para este módulo; el ErrorResponse existente usa otro envelope y debe conciliarse antes de exportar OpenAPI. No registrar error interno del proveedor con credenciales.

Manifest (schema a definir con StrictModel, extra=forbid):

```text
dataset_id: UUID
schema_version: "1"
processing_version: string
field_id: UUID (sólo privado)
geometry_version_id: UUID
boundary: PolygonGeometry
area_hectares: number
start_date/end_date: date
timezone: IANA string
status: ready | partial
generated_at: datetime UTC
playback: {max_image_age_days: 10, step_days: 1}
frames: [{id, observed_at, local_date, usable, valid_area_fraction,
          ndvi: {mean: number|null, p10: number|null, p90: number|null},
          missing_reason: string|null, source_ids: UUID[], available_layers: string[]}]
weather_daily: [{date, precipitation_mm: number|null,
                precipitation_7d_mm: number|null, temperature_min_c: number|null,
                temperature_max_c: number|null, source_id, missing_reason: string|null}]
events: [{id, date, type: observation | declared_operation,
          label, origin: satellite | declared, source_ids}]
availability: [{source_id, status: complete | partial | unavailable,
                available_from: date|null, available_to: date|null,
                missing_intervals: [{from,to,reason}]}]
sources: [{id, provider, dataset, model: string|null, resolution,
           retrieved_at, documentation_url, attribution}]
```

Detalle frame agrega `assets: [{id,layer,url,expires_at,bbox:[west,south,east,north],crs,resolution_m,width,height,sha256}]`. RGB/NDVI: PNG RGBA con alpha=0 fuera de polígono/huecos y bbox en EPSG:4326; reprojectar a imagen norte-arriba antes de exportar. Conservar resolución de origen en metadata. Paleta NDVI y estiramiento RGB fijos/versionados durante el dataset. No entregar TIFF crudo al navegador. Tope inicial de preview 1024 px por lado; imágenes mayores se reducen y declaran resolución de salida. Hoy las métricas se derivan de ese raster de 256 px; al incorporar Statistical API pasarán a resolución analítica sin cambiar el contrato.

## 6. Pipeline y sincronización visual

Buscar escenas que intersecten polígono y período; paginar catálogo y agrupar tiles de una misma adquisición. Guardar IDs y método de mosaico. Misma selección temporal y máscara para textura y estadísticas. Máscara inicial SCL 4/5/6, excluyendo no-data y denominador cero. Usabilidad propuesta >=70% de área válida; umbral configurable, no probabilidad de exactitud. Conservar nubes como huecos transparentes.

El worker procesa etapas catalog → frames → weather → finalize, con checkpoints y keys de assets deterministas. Publicación atómica: sólo marcar ready tras comprobar metadata y objetos. partial si una fuente o fecha falla pero hay resultados útiles; failed si no hay ningún resultado utilizable. No emitir assets de pasos incompletos. Fixtures locales deben llevar bandera is_demo y nunca publicarse como observación real.

El slider usa días locales. Para D selecciona captura utilizable más reciente con local_date<=D; si antigüedad>10 días, sin textura temporal. NDVI indica fecha de captura; clima corresponde a D. El 3D conserva contorno, relieve y cámara. Cambian textura RGB/NDVI y tarjetas. No interpolar mediciones; fundido visual opcional. Precargar dos frames; cancelar respuesta vieja al cambiar selección; pausar playback si falta textura. Public manifest contiene sólo metadata necesaria y procedencia pública, nunca parámetros internos de autenticación.

## 7. Límites, configuración y verificación

Topes de producto iniciales: 366 días, un job activo por campo y máximo 120 adquisiciones; superar tope informa error/rango a reducir, sin truncar silenciosamente. Dimensiones de lote aceptadas se cierran tras spike para evitar solicitudes imposibles. Persistir límites aplicados en request_parameters.

Variables propuestas: CDSE_CLIENT_ID, CDSE_CLIENT_SECRET sólo worker; CDSE_API_BASE_URL; WEATHER_API_BASE_URL; TIMELAPSE_BUCKET; TIMELAPSE_PROCESSING_VERSION; configuración DB/Auth ya prevista. Worker usa credenciales de mínimo privilegio. Pin de dependencias y lockfile al implementar. API HTTP necesita cliente HTTP en dependencias runtime, actualmente httpx sólo aparece en dev.

Logs: request_id, job_id, dataset_id, etapa, duración, intentos, recuento de escenas y errores por proveedor. Estado muestra último heartbeat para detectar jobs sin worker. No prometer refresco satelital por minuto: la actualización de datos se lanza por job y depende de disponibilidad de escenas.

Pruebas obligatorias: contrato OpenAPI existente sin regresiones; JWT/propiedad; geometría con agujeros y autointersecciones; máscara y NDVI numérico; lluvia con huecos; timezone; job duplicado; worker interrumpido; no publicar lease vencido; assets privados; despublicación; edición de geometría; slider fuera de orden. Ver plan de ejecución.
