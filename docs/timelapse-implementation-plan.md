# Timelapse — plan de implementación

Fecha: 2026-09-12. Estado: listo para iniciar; tareas pendientes. Referencia: [spec técnico v0.2](timelapse-technical-spec.md). El trabajo realizado en esta entrega es documentación; este plan no afirma que exista la feature.

## Orden recomendado

P0 validar datos → P1 contrato y bases → P2 persistencia/jobs → P3 ingesta → P4 HTTP/publicación → P5 integración frontend → P6 demo verificable.

P0 debe resolverse temprano: evita desarrollar un recorrido dependiente de acceso satelital no probado. El front puede preparar el reproductor con fixtures explícitos desde P1 mientras se completa ingesta.

## P0 — Obtener evidencia real

- Elegir un field real del proyecto y período histórico con >=3 escenas útiles.
- Verificar credenciales/cuotas CDSE; consultar Catalog y obtener RGB/NDVI y estadísticas para la misma adquisición.
- Consultar ERA5 para el período ampliado seis días; conservar respuesta y celda devuelta.
- Guardar fixtures sin secretos, IDs de escenas, provenance y hashes. Revisar máscara y alineación con contorno.
- Medir duración y tamaño; cerrar límites de área, número de escenas y recursos del worker. Si no hay capturas, probar otro período conservando registro del resultado.

Entrega: tres frames reales y clima, con reporte reproducible. Aceptación: valores y assets corresponden al mismo polígono y fechas; ninguna imagen de ejemplo se presenta como real. Prerrequisitos externos: campo seleccionado y cuenta CDSE habilitada.

## P1 — Acordar contrato y preparar módulo

- Añadir `app/timelapse/schemas.py`, `router.py`, `service.py`, `repository.py` e interfaces de proveedores; mantener `app/main.py` como registro de routers.
- Schemas Pydantic snake_case derivados del spec; errores compatibles con detail actual; tests del envelope.
- Añadir campos/versiones sin romper consumidores de FieldResponse. Resolver el bug de PATCH boundary con dict y validación de todos los anillos.
- Fixtures de manifest y frame en tests/fixtures/timelapse; URLs dummy y bandera demo explícita.
- Exportar OpenAPI con `scripts/export_openapi.py`; no editar manualmente openapi.json.

Entrega: contrato navegable y fixtures tipados. Aceptación: OpenAPI contiene rutas/modelos nuevos y conserva el CRUD existente. Si la infraestructura sigue pendiente, routers de jobs reales no simulan éxito; usar implementación fake sólo por inyección en pruebas.

## P2 — Persistencia, identidad y jobs durables

- Coordinar dependencia de Supabase/Auth del backend base: owner_id, JWT y repositorio persistente. InMemoryFieldStore queda para tests.
- Crear migraciones de geometrías, jobs, datasets, frames, assets, clima, fuentes y publicación; constraints e índices del spec.
- Crear bucket privado; verificar permisos y TTL de firmas. API valida propietario aunque use conexión privilegiada.
- Implementar deduplicación, leases con token, heartbeat, checkpoints y reintentos.
- Añadir `app/timelapse/worker.py` con entrada propuesta `python -m app.timelapse.worker`; aún no disponible. Worker local para desarrollo; documentar despliegue en contenedor antes del uso continuo.

Entrega: job persiste tras reiniciar API y es retomable tras caída de worker. Aceptación: dos workers no completan/publican la misma lease; un usuario no accede a jobs/campos ajenos.

## P3 — Proveedores y procesamiento

- Implementar `providers/cdse.py`, `providers/weather.py`, `processing.py` y `assets.py` dentro de app/timelapse.
- Cliente HTTP runtime, OAuth con renovación; timeouts, rate limiting y backoff. Credenciales sólo en entorno.
- Selección paginada de escenas, agrupación por adquisición, máscara del lote y resampling declarado.
- Generar RGBA/estadísticas usando misma selección; registrar checksums, fórmula y versión.
- Serie ERA5 diaria y acumulado 7 días con null para ventanas incompletas.
- Guardar checkpoints; finalizar dataset ready/partial de forma atómica.

Entrega: dataset real recuperable desde DB/Storage. Aceptación: nube no entra al promedio; un cero de lluvia permanece cero; fallo de clima permite dataset parcial satelital; las métricas sobreviven a regenerar URLs.

## P4 — Endpoints privados y ficha pública

- Conectar POST de generación, polling de job, manifest y detalle frame al repositorio real.
- Publicación explícita de dataset sobre ficha pública; comprobar geometría actual y estado listo/parcial.
- Resolver slug con visibilidad y dataset fijado. Redactar campos internos; aplicar mismas reglas al endpoint público de frames.
- Despublicar bloquea nuevas firmas; editar boundary invalida referencia publicada sin destruir dataset histórico.
- Agregar CORS de dominios aprobados y caché acorde a permisos/TTL. No cachear públicamente respuestas privadas.

Entrega: recorrido API crear campo → generar → consultar → publicar → leer por slug → despublicar. Aceptación: 401/404/409/422/429 según contrato y ausencia de regresiones CRUD.

## P5 — Handoff e integración frontend

- Entregar OpenAPI, manifest/frames y reglas de dos fechas al equipo de frontend.
- Implementar slider diario y saltos por captura, capas RGB/NDVI, etiquetas de fecha/antigüedad y tres tarjetas (NDVI, lluvia, temperatura).
- Precargar dos frames; renovar URL vencida por endpoint autorizado; descartar respuestas fuera de orden.
- Mostrar nubes/huecos, fuente regional del clima y estado parcial. Relieve fijo, sin inferir altura de cultivo.
- Mantener el dataset fijo durante reproducción; nueva versión requiere recarga explícita.

Entrega: reproductor conectado a backend. Aceptación: arrastre rápido mantiene consistencia fecha/imagen/tarjetas; en >10 días sin captura aparece estado sin imagen; el slider no dispara procesamiento.

## P6 — Verificación y entrega del MVP

- Ejecutar `uv run pytest`, `uv run ruff check app tests scripts` y exportación OpenAPI. Registrar problemas preexistentes separados de regresiones.
- Integración con servicios de pruebas: persistencia, worker restart y accesos entre dos usuarios.
- Prueba real con las tres fechas de P0 y rango climático; revisar procedencia desde el front.
- Registrar tiempos reales de ingesta y reproducción; objetivo inicial de interacción con datos precargados <100 ms, a verificar en dispositivo demo.
- Documentar variables sin valores secretos, arranque API/worker, cuotas, errores comunes y recuperación de jobs.

Definición de terminado: campo real → job durable → dataset trazable → timelapse 3D por fechas → ficha compartible con permisos correctos. No exige IA ni simulación de semillas.

## Recorte para hackathon

Si el tiempo aprieta, procesar por CLI un campo y período conocidos y servir el resultado persistido con el mismo contrato. Declarar que la generación autoservicio está pendiente. Esto permite una demo real del timelapse sin prometer un job público todavía inexistente.

Responsabilidades sugeridas (sin asignar personas): backend base P2/Auth; integración satelital P0/P3; API P1/P4; frontend P5; validación conjunta P6. Ordenar entregas por las dependencias anteriores. No estimar horas de procesamiento hasta medir el spike.
