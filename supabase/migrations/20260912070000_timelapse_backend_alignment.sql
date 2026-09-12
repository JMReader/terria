-- Backend alignment: columnas y tablas que necesita la API Python para
-- persistir fields + timelapse en Supabase (decisión "supabase-base-datos-unica").
-- Todo es aditivo: no modifica columnas ni constraints existentes.

-- Timestamp de primera publicación del field; la API lo expone en la ficha pública.
alter table core.fields
  add column if not exists published_at timestamptz;

-- Cola compartida: payload por job (parámetros, request_hash, resultado),
-- progreso y token de lease para que el worker valide su claim.
alter table ops.jobs
  add column if not exists payload jsonb not null default '{}'::jsonb,
  add column if not exists progress numeric(4,3) not null default 0
    check (progress between 0 and 1),
  add column if not exists lease_token text;

create index if not exists jobs_timelapse_request_hash_ix
  on ops.jobs ((payload ->> 'request_hash'))
  where kind = 'timelapse';

-- Historial de geometrías por field (equivale a field_geometry_versions de
-- SQLite; el hash desduplica versiones para los request_hash del timelapse).
create table if not exists timelapse.geometry_versions (
  id uuid primary key default gen_random_uuid(),
  field_id uuid not null references core.fields(id) on delete cascade,
  boundary extensions.geography(MULTIPOLYGON, 4326) not null,
  geometry_hash text not null,
  area_hectares numeric(12,2) not null,
  created_at timestamptz not null default now(),
  unique (field_id, geometry_hash)
);
comment on table timelapse.geometry_versions
  is 'Historial de geometrías de core.fields usado por los request_hash del timelapse';

create index if not exists geometry_versions_field_ix
  on timelapse.geometry_versions (field_id, created_at desc);

alter table timelapse.geometry_versions enable row level security;
create policy "owners read geometry versions" on timelapse.geometry_versions
  for select to authenticated using (
    exists (
      select 1 from core.fields f
      where f.id = field_id and f.owner_id = (select auth.uid())
    )
  );
