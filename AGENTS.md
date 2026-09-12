## Cerebro del proyecto

```yaml
brain: shared-brain
project: terria
```

# TERRIA — Directivas de Arquitectura y Memoria de Proyecto

> **MEMORIA CRÍTICA PARA TODOS LOS AGENTES Y CHATS:**
> Este documento rige de forma obligatoria para cualquier agente (Antigravity, Claude, Codex, etc.) que trabaje en el proyecto TERRIA (`terria` / `hackcba`).

---

## 1. Regla de los 3 Campos Reales de Supabase (Allowlist Cerrada)

En la base de datos de producción (**Supabase Postgres/PostGIS**) y en la réplica local de desarrollo (`data/terria.db`), **SOLO EXISTEN Y SE TRABAJA CON ESTOS 3 CAMPOS REALES APROBADOS**:

| # | Nombre Oficial del Campo | Jurisdicción | ID en Supabase (UUID) | Slug Público | Descripción Agronómica |
|---|---|---|---|---|---|
| 1 | **Lote Sur — EEA INTA Marcos Juárez** | Marcos Juárez, Córdoba | `9d103ed2-cfac-4ff9-bd9f-9fa3d9225d38` | `2e9a0e25032e` | Predio experimental del INTA (RP 12 km 3). Suelo Argiudol típico Clase I. Núcleo pampeano de máxima productividad. |
| 2 | **Lote NO — EEA INTA Manfredi** | Manfredi, Córdoba | `377e9838-826a-46ad-bb25-9a5230f59752` | `94d9fb54c3d3` | Estación experimental del INTA sobre RN 9 km 636. Suelo Haplustol típico, ensayos de labranza y rotación desde 1997. |
| 3 | **Campo Experimental Pozo del Carril (FAV-UNRC)** | La Aguada, Córdoba | `6b54bd15-70b3-40aa-970c-7922e3c82741` | `af1b4970ff52` | Establecimiento de la Fac. de Agronomía y Veterinaria de Río Cuarto. Piedemonte de Comechingones, silvopastoril. |

### Reglas estrictas:
- **Prohibido crear campos dummy o adicionales en Supabase o en la base local.** Ningún script, seed, endpoint ni test de humo debe insertar campos de prueba en la base de datos.
- Los tests automatizados (`pytest`) se ejecutan siempre contra SQLite temporal en memoria o archivos descartables (`tests/conftest.py`).
- El único script autorizado para poblar la base es `scripts/seed_real_fields.py`, el cual es idempotente por nombre y carga exclusivamente estos 3 campos.

---

## 2. Acceso a Datos y Factory de Almacenamiento

- **NUNCA instanciar `SQLiteFieldStore()` directamente** en routers, servicios, CLIs ni scripts.
- **SIEMPRE usar `get_field_store()`** (en `app/store.py`), que detecta automáticamente si `DATABASE_URL` está configurado para conectar con Supabase (pooler transaccional en puerto `6543`), o si debe usar SQLite local como fallback.
- Del mismo modo, para timelapses usar `get_timelapse_repository()`.

---

## 3. Simulador What-If y Proyector de Valuación (CLI y Endpoints)

Ambos motores (`run_what_if.py` y `run_valuation.py`) soportan 3 modos de operación:
1. **Opción [1] - Presets Regionales**: Lotes precalculados para exploración rápida de otras cuencas (Marcos Juárez, Federación Mandisoví, Pergamino, Venado Tuerto, Charata, Tres Arroyos).
2. **Opción [2] - Datos Manuales / GeoJSON**: Entrada de cualquier polígono personalizado que el usuario pegue o cargue vía archivo `.geojson`.
3. **Opción [3] - Base de Datos de TERRIA**: Consulta directa al store (`get_field_store()`) que presenta **exclusivamente los 3 campos oficiales de Supabase**.

---

## 4. Referencias en el Cerebro Compartido (Obsidian)

- Runbook de producción: `shared-brain/team/projects/terria-backend-produccion.md`
- Decisión de arquitectura: `shared-brain/team/decisions/2026-09-12-campos-demo-productivos.md`
- Registro de sesiones y avances: `shared-brain/each_one/angel-kemerer/sessions/`
