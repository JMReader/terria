export interface SimulationFinancials {
  grossIncomeUsdHa: number;
  costsUsdHa: number;
  netMarginUsdHa: number;
  realNetMarginUsdHa: number;
  diffNetMarginUsdHa: number;
  totalLotDiffUsd: number;
}

export interface CropEvaluation {
  cropId: string;
  cropName: string;
  category: string; // Cereal, Oleaginosa, Especialidad, Industrial
  season: string; // Gruesa, Fina
  projectedYieldTnHa: number;
  benchmarkDeptYieldTnHa: number;
  deltaYieldPct: number;
  financials: SimulationFinancials;
  rankYield: number;
  rankMargin: number;
}

export interface ModelMetrics {
  candidateLotsScanned: number;
  strictTwinLotsMatched: number;
  avgSimilarityScore: number;
  dimensionsAnalyzed: string[];
  zoneMeanNdvi: number;
}

export interface SimulationResults {
  projectedYieldTnHa: number;
  benchmarkDeptYieldTnHa: number;
  financials: SimulationFinancials;
  recommendation: string;
}

export interface WhatIfSimulation {
  status: string;
  schemaVersion: string;
  algorithmVersion: string;
  fieldId?: string | null;
  lotName: string;
  surfaceHa: number;
  targetYear: number;
  simulatedCrop?: string | null;
  realCrop: string;
  winnerCrop: CropEvaluation;
  bestMarginCrop: CropEvaluation;
  totalCropsEvaluated: number;
  ranking: CropEvaluation[];
  contentHash: string;
  modelMetrics: ModelMetrics;
  results: SimulationResults;
  auditUrls?: Record<string, string>;
  frozenInputs?: Record<string, unknown>;
}

export type WhatIfSource = "loading" | "live" | "demo" | "error";

export interface FieldWhatIfRequest {
  targetYear: number;
  simulatedCrop?: string | null;
  realCrop: string;
  realMarginUsdHa?: number;
  realYieldTnHa?: number | null;
  includeAudit?: boolean;
}

export interface StandaloneWhatIfRequest extends FieldWhatIfRequest {
  name?: string;
  centroidLat?: number;
  centroidLon?: number;
  areaHectares?: number;
  coordinates?: number[][];
}

export interface CropCatalogItem {
  id: string;
  name: string;
  category: string;
  season: string;
  icon?: string;
}

export const CROP_OPTIONS: CropCatalogItem[] = [
  { id: "soja_1ra", name: "Soja de 1ra", category: "Oleaginosa", season: "Gruesa" },
  { id: "maiz", name: "Maíz", category: "Cereal", season: "Gruesa" },
  { id: "trigo", name: "Trigo Pan", category: "Cereal", season: "Fina" },
  { id: "soja_2da", name: "Soja de 2da", category: "Oleaginosa", season: "Gruesa" },
  { id: "girasol", name: "Girasol", category: "Oleaginosa", season: "Gruesa" },
  { id: "cebada", name: "Cebada Cervecera", category: "Cereal", season: "Fina" },
  { id: "sorgo", name: "Sorgo Granífero", category: "Cereal", season: "Gruesa" },
  { id: "mani", name: "Maní", category: "Especialidad", season: "Gruesa" },
  { id: "algodon", name: "Algodón", category: "Industrial", season: "Gruesa" },
  { id: "colza", name: "Colza / Canola", category: "Oleaginosa", season: "Fina" },
];

/**
 * Detecta el cultivo oficial de SAGyP a partir de los datos cargados en el campo.
 */
export function detectFieldDefaultCrop(cropStr?: string): string {
  if (!cropStr) return "soja_1ra";
  const s = cropStr.toLowerCase();
  if (s.includes("maíz") || s.includes("maiz")) return "maiz";
  if (s.includes("maní") || s.includes("mani")) return "mani";
  if (s.includes("trigo")) return "trigo";
  if (s.includes("cebada")) return "cebada";
  if (s.includes("sorgo")) return "sorgo";
  if (s.includes("girasol")) return "girasol";
  if (s.includes("algodón") || s.includes("algodon")) return "algodon";
  if (s.includes("colza") || s.includes("canola")) return "colza";
  if (s.includes("2da") || s.includes("segunda")) return "soja_2da";
  if (s.includes("soja")) return "soja_1ra";
  return "soja_1ra";
}

export type YearDataStatus = "verified_live" | "historical_extrapolation" | "future_projection";

export interface YearDataAvailability {
  status: YearDataStatus;
  label: string;
  badgeClass: string;
  details: string;
  hasSatellite: boolean;
}

/**
 * Valida la disponibilidad de series satelitales (Sentinel-2) y benchmarks oficiales para un año dado.
 */
export function checkYearDataAvailability(year: number): YearDataAvailability {
  if (year < 2017) {
    return {
      status: "historical_extrapolation",
      label: "Extrapolación previa a Sentinel-2",
      badgeClass: "bg-tierra/15 text-tierra-deep border-tierra/40",
      details: "Antes de 2017 no hay cobertura operativa Sentinel-2 L2A. Se computa con climatología histórica AgERA5.",
      hasSatellite: false,
    };
  }
  if (year > 2025) {
    return {
      status: "future_projection",
      label: "Proyección futura simulada",
      badgeClass: "bg-cielo/15 text-cielo-deep border-cielo/40",
      details: "Campaña futura: no existen imágenes satelitales aún; se utiliza ensamble climatológico proyectado.",
      hasSatellite: false,
    };
  }
  if (year === 2023) {
    return {
      status: "verified_live",
      label: "Campaña 2022/23 (Sequía Histórica) · Datos Verificados",
      badgeClass: "bg-musgo/15 text-musgo border-musgo/40",
      details: "Serie satelital completa Sentinel-2, Sentinel-1 y reanálisis ERA5 con anomalía térmica extrema.",
      hasSatellite: true,
    };
  }
  return {
    status: "verified_live",
    label: `Campaña ${year - 1}/${String(year).slice(-2)} · Datos Satelitales Completos`,
    badgeClass: "bg-musgo/10 text-musgo border-musgo/30",
    details: "Sentinel-2 L2A (10m) + AgERA5 + Estadísticas oficiales SAGyP por departamento.",
    hasSatellite: true,
  };
}
