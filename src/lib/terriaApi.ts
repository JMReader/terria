import {
  MetricValue,
  TimelapseManifest,
  TimelapseFrame,
  WeatherDaily,
  TimelapseSource,
} from "@/types/terria";
import { LandValuation } from "@/types/valuation";
import {
  WhatIfSimulation,
  CropEvaluation,
  FieldWhatIfRequest,
  StandaloneWhatIfRequest,
} from "@/types/whatIf";

/**
 * Cliente liviano para la API FastAPI de TERRIA + adaptador del contrato
 * backend (snake_case, métricas planas) a los tipos del frontend
 * (camelCase, métricas envueltas en MetricValue).
 */

export const API_BASE = (
  process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000"
).replace(/\/$/, "");

/** Campo real del backend usado para el timelapse en vivo (Establecimiento La Posta — demo pública). */
export const TIMELAPSE_FIELD_ID =
  process.env.NEXT_PUBLIC_TIMELAPSE_FIELD_ID ??
  "67afba41-1bcc-4a1b-9ac3-90fd91132281";

const TIMELAPSE_START = process.env.NEXT_PUBLIC_TIMELAPSE_START ?? "2024-01-01";
const TIMELAPSE_END = process.env.NEXT_PUBLIC_TIMELAPSE_END ?? "2024-03-31";

/* ---------- Tipos del backend (espejo de app/timelapse/schemas.py) ---------- */

interface ApiAsset {
  id: string;
  layer: "rgb" | "ndvi";
  url: string;
  width: number;
  height: number;
  bbox?: number[] | null;
  crs?: string | null;
  sha256?: string | null;
}

interface ApiFrame {
  id: string;
  observed_at: string;
  local_date: string;
  source_item_ids: string[];
  usable: boolean;
  valid_area_fraction: number;
  valid_pixel_count: number;
  ndvi: { mean: number | null; p10: number | null; p90: number | null };
  missing_reason: string | null;
  available_layers: string[];
  assets: ApiAsset[];
}

interface ApiWeatherDaily {
  date: string;
  precipitation_mm: number | null;
  precipitation_7d_mm: number | null;
  temperature_min_c: number | null;
  temperature_max_c: number | null;
  source_id: string;
  missing_reason: string | null;
}

interface ApiSource {
  id: string;
  provider: string;
  dataset: string;
  model?: string | null;
  resolution?: string | null;
  retrieved_at: string;
  documentation_url: string;
  attribution: string;
}

export interface ApiManifest {
  dataset_id: string;
  schema_version: string;
  processing_version: string;
  field_id: string;
  geometry_version_id: string;
  boundary: unknown;
  area_hectares: number;
  start_date: string;
  end_date: string;
  timezone: string;
  status: "ready" | "partial" | "failed";
  generated_at: string;
  is_demo: boolean;
  playback: { max_image_age_days: number; step_days: number };
  frames: ApiFrame[];
  weather_daily: ApiWeatherDaily[];
  sources: ApiSource[];
  missing_reasons: string[];
}

interface ApiDatasetSummary {
  id: string;
  field_id: string;
  start_date: string;
  end_date: string;
  status: string;
  is_demo: boolean;
  generated_at: string;
  frames_count: number;
}

interface ApiJob {
  id: string;
  status: "queued" | "processing" | "ready" | "partial" | "failed";
  progress: number;
  dataset_id: string | null;
  error_code: string | null;
}

/* ---------- Adaptadores ---------- */

const mv = (
  value: number | null,
  unit: string,
  sourceId: string,
  kind: MetricValue["kind"],
  missingReason?: string | null
): MetricValue<number> => ({
  value,
  unit,
  sourceId,
  kind,
  missingReason: missingReason ?? undefined,
});

const absoluteUrl = (url: string) =>
  url.startsWith("http") ? url : `${API_BASE}${url}`;

function adaptFrame(f: ApiFrame): TimelapseFrame {
  return {
    id: f.id,
    observedAt: f.observed_at,
    localDate: f.local_date,
    sourceItemIds: f.source_item_ids,
    usable: f.usable,
    unusableReason: f.missing_reason ?? undefined,
    quality: {
      validPixelFraction: f.valid_area_fraction,
      validPixelCount: f.valid_pixel_count,
      cloudFraction: Math.max(0, 1 - f.valid_area_fraction),
    },
    ndvi: {
      mean: mv(f.ndvi?.mean ?? null, "index", "sentinel-2-l2a", "derived", f.missing_reason),
      p10: mv(f.ndvi?.p10 ?? null, "index", "sentinel-2-l2a", "derived", f.missing_reason),
      p90: mv(f.ndvi?.p90 ?? null, "index", "sentinel-2-l2a", "derived", f.missing_reason),
    },
    assets: (f.assets ?? []).map((a) => ({
      layer: a.layer,
      url: absoluteUrl(a.url),
      expiresAt: "2027-12-31T23:59:59Z",
      resolutionM: 10,
      checksum: a.sha256 ?? undefined,
    })),
  };
}

function adaptWeather(w: ApiWeatherDaily): WeatherDaily {
  return {
    date: w.date,
    precipitationDay: mv(w.precipitation_mm, "mm", w.source_id, "reanalysis", w.missing_reason),
    precipitation7d: mv(w.precipitation_7d_mm, "mm", w.source_id, "derived", w.missing_reason),
    temperatureMin: mv(w.temperature_min_c, "°C", w.source_id, "reanalysis", w.missing_reason),
    temperatureMax: mv(w.temperature_max_c, "°C", w.source_id, "reanalysis", w.missing_reason),
  };
}

function adaptSource(s: ApiSource): TimelapseSource {
  return {
    id: s.id,
    provider: s.provider,
    dataset: s.dataset,
    documentationUrl: s.documentation_url,
    resolution: s.resolution ?? undefined,
    attribution: s.attribution,
  };
}

export function adaptManifest(m: ApiManifest): TimelapseManifest {
  return {
    schemaVersion: "1",
    datasetVersion: m.processing_version,
    fieldId: m.field_id,
    geometryVersion: m.geometry_version_id,
    from: m.start_date,
    to: m.end_date,
    generatedAt: m.generated_at,
    status: m.status === "failed" ? "partial" : m.status,
    frames: m.frames.map(adaptFrame),
    weatherDaily: m.weather_daily.map(adaptWeather),
    sources: m.sources.map(adaptSource),
  };
}

/* ---------- Flujo en vivo ---------- */

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init);
  if (!res.ok) throw new Error(`${init?.method ?? "GET"} ${url} -> ${res.status}`);
  return (await res.json()) as T;
}

async function getManifest(fieldId: string, datasetId: string): Promise<TimelapseManifest> {
  const raw = await fetchJson<ApiManifest>(
    `${API_BASE}/v1/fields/${fieldId}/timelapses/${datasetId}`
  );
  return adaptManifest(raw);
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

/**
 * Resuelve el mejor manifest disponible para el campo:
 * 1. Lista datasets existentes y elige el mejor (ready/partial, real primero, más frames).
 * 2. Si no hay, POST de generación y polling del job (reusa dataset listo si existe).
 */
export async function loadLiveManifest(
  fieldId: string = TIMELAPSE_FIELD_ID
): Promise<TimelapseManifest> {
  // 1) Datasets ya generados
  const summaries = await fetchJson<ApiDatasetSummary[]>(
    `${API_BASE}/v1/fields/${fieldId}/timelapses`
  );

  const usable = summaries
    .filter((d) => (d.status === "ready" || d.status === "partial") && d.frames_count > 0)
    .sort((a, b) => {
      // Datos reales primero, luego más cobertura temporal y más frames
      if (a.is_demo !== b.is_demo) return a.is_demo ? 1 : -1;
      if (a.status !== b.status) return a.status === "ready" ? -1 : 1;
      if (a.frames_count !== b.frames_count) return b.frames_count - a.frames_count;
      return b.end_date.localeCompare(a.end_date);
    });

  if (usable.length > 0) {
    return getManifest(fieldId, usable[0].id);
  }

  // 2) Generar dataset nuevo (el backend reusa si el hash coincide)
  const post = await fetch(`${API_BASE}/v1/fields/${fieldId}/timelapses`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      start_date: TIMELAPSE_START,
      end_date: TIMELAPSE_END,
      layers: ["rgb", "ndvi"],
      is_demo: true,
    }),
  });

  if (post.status === 200) {
    const body = (await post.json()) as { dataset_id: string };
    return getManifest(fieldId, body.dataset_id);
  }
  if (post.status !== 202) throw new Error(`POST timelapses -> ${post.status}`);

  const job = (await post.json()) as ApiJob;
  const deadline = Date.now() + 45_000;
  while (Date.now() < deadline) {
    await sleep(1500);
    const cur = await fetchJson<ApiJob>(`${API_BASE}/v1/timelapse-jobs/${job.id}`);
    if ((cur.status === "ready" || cur.status === "partial") && cur.dataset_id) {
      return getManifest(fieldId, cur.dataset_id);
    }
    if (cur.status === "failed") {
      throw new Error(`Timelapse job failed: ${cur.error_code ?? "unknown"}`);
    }
  }
  throw new Error("Timelapse job timeout");
}

/* ---------- Valuación de tierra a N años (spec land-valuation-5yr) ---------- */

interface ApiValuationDriver {
  impact_percentage: number;
  multiplier: number;
  detail: string;
}

interface ApiLogisticDriver extends ApiValuationDriver {
  distance_to_current_paved_km: number;
  distance_to_future_paved_km: number;
  distance_saved_km: number;
}

interface ApiAgronomicDriver extends ApiValuationDriver {
  cagr_annual_pct: number;
}

interface ApiMarketDriver extends ApiValuationDriver {
  annual_rate_pct: number;
}

interface ApiValuation {
  current_year: number;
  target_year: number;
  projection_years: number;
  base_value_usd_ha: number;
  projected_value_usd_ha: number;
  total_appreciation_percentage: number;
  drivers_breakdown: {
    logistic_improvement: ApiLogisticDriver;
    agronomic_trend: ApiAgronomicDriver;
    market_appreciation: ApiMarketDriver;
  };
  financial_totals: {
    surface_ha: number;
    total_base_value_usd: number;
    total_projected_value_usd: number;
    total_capital_gain_usd: number;
  };
  content_hash: string;
  audit_urls: Record<string, string>;
}

/** La respuesta puede venir envuelta en `{ valuation: … }` o plana. */
type ApiValuationResponse = ApiValuation | { valuation: ApiValuation };

export function adaptValuation(raw: ApiValuation): LandValuation {
  const d = raw.drivers_breakdown;
  return {
    currentYear: raw.current_year,
    targetYear: raw.target_year,
    projectionYears: raw.projection_years,
    baseValueUsdHa: raw.base_value_usd_ha,
    projectedValueUsdHa: raw.projected_value_usd_ha,
    totalAppreciationPercentage: raw.total_appreciation_percentage,
    driversBreakdown: {
      logisticImprovement: {
        impactPercentage: d.logistic_improvement.impact_percentage,
        multiplier: d.logistic_improvement.multiplier,
        detail: d.logistic_improvement.detail,
        distanceToCurrentPavedKm: d.logistic_improvement.distance_to_current_paved_km,
        distanceToFuturePavedKm: d.logistic_improvement.distance_to_future_paved_km,
        distanceSavedKm: d.logistic_improvement.distance_saved_km,
      },
      agronomicTrend: {
        impactPercentage: d.agronomic_trend.impact_percentage,
        multiplier: d.agronomic_trend.multiplier,
        detail: d.agronomic_trend.detail,
        cagrAnnualPct: d.agronomic_trend.cagr_annual_pct,
      },
      marketAppreciation: {
        impactPercentage: d.market_appreciation.impact_percentage,
        multiplier: d.market_appreciation.multiplier,
        detail: d.market_appreciation.detail,
        annualRatePct: d.market_appreciation.annual_rate_pct,
      },
    },
    financialTotals: {
      surfaceHa: raw.financial_totals.surface_ha,
      totalBaseValueUsd: raw.financial_totals.total_base_value_usd,
      totalProjectedValueUsd: raw.financial_totals.total_projected_value_usd,
      totalCapitalGainUsd: raw.financial_totals.total_capital_gain_usd,
    },
    contentHash: raw.content_hash,
    auditUrls: raw.audit_urls ?? {},
  };
}

export interface FieldValuationRequest {
  centroidLat: number;
  centroidLon: number;
  areaHectares: number;
  projectionYears?: number;
  name?: string;
}

/**
 * Proyección de valor de tierra vía endpoint standalone del backend
 * (`POST /v1/valuations/5yr`). El front envía centroide + superficie del
 * FieldItem; si el catálogo migra a fields reales del backend, switchear a
 * `POST /v1/fields/{field_id}/valuations/5yr`.
 */
export async function fetchFieldValuation(
  req: FieldValuationRequest
): Promise<LandValuation> {
  const body = await fetchJson<ApiValuationResponse>(`${API_BASE}/v1/valuations/5yr`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name: req.name ?? "Lote Futurología",
      centroid_lat: req.centroidLat,
      centroid_lon: req.centroidLon,
      area_hectares: req.areaHectares,
      projection_years: req.projectionYears ?? 5,
      include_audit: true,
    }),
  });
  const raw = "valuation" in body ? body.valuation : body;
  return adaptValuation(raw);
}

/* ---------- Simulador What-If Multicultivo (spec feature-2-what-if v2.2) ---------- */

interface ApiCropEvaluation {
  crop_id: string;
  crop_name: string;
  category: string;
  season: string;
  projected_yield_tn_ha: number;
  benchmark_dept_yield_tn_ha: number;
  delta_yield_pct: number;
  financials: {
    gross_income_usd_ha: number;
    costs_usd_ha: number;
    net_margin_usd_ha: number;
    real_net_margin_usd_ha: number;
    diff_net_margin_usd_ha: number;
    total_lot_diff_usd: number;
  };
  rank_yield: number;
  rank_margin: number;
}

interface ApiWhatIfSimulation {
  status: string;
  schema_version: string;
  algorithm_version: string;
  field_id?: string | null;
  lot_name: string;
  surface_ha: number;
  target_year: number;
  simulated_crop?: string | null;
  real_crop: string;
  winner_crop: ApiCropEvaluation;
  best_margin_crop: ApiCropEvaluation;
  total_crops_evaluated: number;
  ranking: ApiCropEvaluation[];
  content_hash: string;
  model_metrics: {
    candidate_lots_scanned: number;
    strict_twin_lots_matched: number;
    avg_similarity_score: number;
    dimensions_analyzed: string[];
    zone_mean_ndvi: number;
  };
  results: {
    projected_yield_tn_ha: number;
    benchmark_dept_yield_tn_ha: number;
    financials: ApiCropEvaluation["financials"];
    recommendation: string;
  };
  audit_urls?: Record<string, string>;
  frozen_inputs?: Record<string, unknown>;
}

function adaptCropEvaluation(raw: ApiCropEvaluation): CropEvaluation {
  return {
    cropId: raw.crop_id,
    cropName: raw.crop_name,
    category: raw.category,
    season: raw.season,
    projectedYieldTnHa: raw.projected_yield_tn_ha,
    benchmarkDeptYieldTnHa: raw.benchmark_dept_yield_tn_ha,
    deltaYieldPct: raw.delta_yield_pct,
    financials: {
      grossIncomeUsdHa: raw.financials.gross_income_usd_ha,
      costsUsdHa: raw.financials.costs_usd_ha,
      netMarginUsdHa: raw.financials.net_margin_usd_ha,
      realNetMarginUsdHa: raw.financials.real_net_margin_usd_ha,
      diffNetMarginUsdHa: raw.financials.diff_net_margin_usd_ha,
      totalLotDiffUsd: raw.financials.total_lot_diff_usd,
    },
    rankYield: raw.rank_yield,
    rankMargin: raw.rank_margin,
  };
}

export function adaptWhatIf(raw: ApiWhatIfSimulation): WhatIfSimulation {
  return {
    status: raw.status,
    schemaVersion: raw.schema_version,
    algorithmVersion: raw.algorithm_version,
    fieldId: raw.field_id,
    lotName: raw.lot_name,
    surfaceHa: raw.surface_ha,
    targetYear: raw.target_year,
    simulatedCrop: raw.simulated_crop,
    realCrop: raw.real_crop,
    winnerCrop: adaptCropEvaluation(raw.winner_crop),
    bestMarginCrop: adaptCropEvaluation(raw.best_margin_crop),
    totalCropsEvaluated: raw.total_crops_evaluated,
    ranking: (raw.ranking || []).map(adaptCropEvaluation),
    contentHash: raw.content_hash,
    modelMetrics: {
      candidateLotsScanned: raw.model_metrics.candidate_lots_scanned,
      strictTwinLotsMatched: raw.model_metrics.strict_twin_lots_matched,
      avgSimilarityScore: raw.model_metrics.avg_similarity_score,
      dimensionsAnalyzed: raw.model_metrics.dimensions_analyzed,
      zoneMeanNdvi: raw.model_metrics.zone_mean_ndvi,
    },
    results: {
      projectedYieldTnHa: raw.results.projected_yield_tn_ha,
      benchmarkDeptYieldTnHa: raw.results.benchmark_dept_yield_tn_ha,
      financials: {
        grossIncomeUsdHa: raw.results.financials.gross_income_usd_ha,
        costsUsdHa: raw.results.financials.costs_usd_ha,
        netMarginUsdHa: raw.results.financials.net_margin_usd_ha,
        realNetMarginUsdHa: raw.results.financials.real_net_margin_usd_ha,
        diffNetMarginUsdHa: raw.results.financials.diff_net_margin_usd_ha,
        totalLotDiffUsd: raw.results.financials.total_lot_diff_usd,
      },
      recommendation: raw.results.recommendation,
    },
    auditUrls: raw.audit_urls ?? {},
    frozenInputs: raw.frozen_inputs ?? {},
  };
}

export async function fetchFieldWhatIf(
  fieldId: string,
  req: FieldWhatIfRequest
): Promise<WhatIfSimulation> {
  const raw = await fetchJson<ApiWhatIfSimulation>(
    `${API_BASE}/v1/fields/${fieldId}/simulations/what-if`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        target_year: req.targetYear,
        simulated_crop: req.simulatedCrop ?? null,
        real_crop: req.realCrop,
        real_margin_usd_ha: req.realMarginUsdHa ?? 350.0,
        real_yield_tn_ha: req.realYieldTnHa ?? null,
        include_audit: req.includeAudit ?? true,
      }),
    }
  );
  return adaptWhatIf(raw);
}

export async function fetchStandaloneWhatIf(
  req: StandaloneWhatIfRequest
): Promise<WhatIfSimulation> {
  const raw = await fetchJson<ApiWhatIfSimulation>(
    `${API_BASE}/v1/simulations/what-if`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: req.name ?? "Lote Simulado",
        centroid_lat: req.centroidLat,
        centroid_lon: req.centroidLon,
        area_hectares: req.areaHectares,
        coordinates: req.coordinates,
        target_year: req.targetYear,
        simulated_crop: req.simulatedCrop ?? null,
        real_crop: req.realCrop,
        real_margin_usd_ha: req.realMarginUsdHa ?? 350.0,
        real_yield_tn_ha: req.realYieldTnHa ?? null,
        include_audit: req.includeAudit ?? true,
      }),
    }
  );
  return adaptWhatIf(raw);
}

