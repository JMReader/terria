import { FieldItem } from "@/data/fieldsData";
import {
  WhatIfSimulation,
  CropEvaluation,
  SimulationFinancials,
  ModelMetrics,
} from "@/types/whatIf";

interface RawCropSpec {
  id: string;
  name: string;
  category: string;
  season: string;
  baseBenchmark: number;
  basePriceUsd: number;
  baseCostsUsd: number;
}

const SAGYP_CATALOG: RawCropSpec[] = [
  {
    id: "maiz",
    name: "Maíz",
    category: "Cereal",
    season: "Gruesa",
    baseBenchmark: 7.2,
    basePriceUsd: 200,
    baseCostsUsd: 620,
  },
  {
    id: "mani",
    name: "Maní",
    category: "Especialidad",
    season: "Gruesa",
    baseBenchmark: 3.1,
    basePriceUsd: 550,
    baseCostsUsd: 780,
  },
  {
    id: "algodon",
    name: "Algodón",
    category: "Industrial",
    season: "Gruesa",
    baseBenchmark: 1.9,
    basePriceUsd: 650,
    baseCostsUsd: 710,
  },
  {
    id: "soja_1ra",
    name: "Soja de 1ra",
    category: "Oleaginosa",
    season: "Gruesa",
    baseBenchmark: 2.8,
    basePriceUsd: 320,
    baseCostsUsd: 440,
  },
  {
    id: "sorgo",
    name: "Sorgo Granífero",
    category: "Cereal",
    season: "Gruesa",
    baseBenchmark: 5.4,
    basePriceUsd: 160,
    baseCostsUsd: 420,
  },
  {
    id: "cebada",
    name: "Cebada Cervecera",
    category: "Cereal",
    season: "Fina",
    baseBenchmark: 3.8,
    basePriceUsd: 220,
    baseCostsUsd: 430,
  },
  {
    id: "trigo",
    name: "Trigo Pan",
    category: "Cereal",
    season: "Fina",
    baseBenchmark: 3.2,
    basePriceUsd: 230,
    baseCostsUsd: 410,
  },
  {
    id: "girasol",
    name: "Girasol",
    category: "Oleaginosa",
    season: "Gruesa",
    baseBenchmark: 2.1,
    basePriceUsd: 360,
    baseCostsUsd: 380,
  },
  {
    id: "soja_2da",
    name: "Soja de 2da",
    category: "Oleaginosa",
    season: "Gruesa",
    baseBenchmark: 1.9,
    basePriceUsd: 320,
    baseCostsUsd: 340,
  },
  {
    id: "colza",
    name: "Colza / Canola",
    category: "Oleaginosa",
    season: "Fina",
    baseBenchmark: 1.6,
    basePriceUsd: 380,
    baseCostsUsd: 390,
  },
];

export function computeDemoWhatIf(
  field: FieldItem,
  targetYear: number = 2023,
  realCrop: string = "soja_1ra",
  realMarginUsdHa: number = 350.0
): WhatIfSimulation {
  const surface = field.hectares || 100;
  const isDrought = targetYear === 2023;
  const weatherFactor = isDrought ? 0.78 : 1.05;
  const zoneNdvi = isDrought ? 0.4133 : 0.742;

  // Multiplicador del lote respecto a la zona según aptitud
  const lotAptitudeFactor =
    field.suitabilityScore != null ? field.suitabilityScore / 100 : 0.95;

  const evaluations: CropEvaluation[] = SAGYP_CATALOG.map((crop) => {
    // Rendimiento proyectado
    const benchmarkYield = parseFloat(
      (crop.baseBenchmark * (isDrought ? 0.8 : 1.0)).toFixed(2)
    );
    const projectedYield = parseFloat(
      (benchmarkYield * lotAptitudeFactor * (1 + (zoneNdvi > 0.6 ? 0.08 : -0.04))).toFixed(2)
    );
    const deltaYieldPct = parseFloat(
      (((projectedYield - benchmarkYield) / benchmarkYield) * 100).toFixed(1)
    );

    // Métricas financieras
    const grossIncome = Math.round(projectedYield * crop.basePriceUsd * weatherFactor);
    const costs = crop.baseCostsUsd;
    const netMargin = grossIncome - costs;
    const diffNetMargin = parseFloat((netMargin - realMarginUsdHa).toFixed(2));
    const totalLotDiff = Math.round(diffNetMargin * surface);

    const financials: SimulationFinancials = {
      grossIncomeUsdHa: grossIncome,
      costsUsdHa: costs,
      netMarginUsdHa: netMargin,
      realNetMarginUsdHa: realMarginUsdHa,
      diffNetMarginUsdHa: diffNetMargin,
      totalLotDiffUsd: totalLotDiff,
    };

    return {
      cropId: crop.id,
      cropName: crop.name,
      category: crop.category,
      season: crop.season,
      projectedYieldTnHa: projectedYield,
      benchmarkDeptYieldTnHa: benchmarkYield,
      deltaYieldPct,
      financials,
      rankYield: 0,
      rankMargin: 0,
    };
  });

  // Ordenar por rinde (volumen tn/ha)
  evaluations
    .slice()
    .sort((a, b) => b.projectedYieldTnHa - a.projectedYieldTnHa)
    .forEach((e, i) => {
      const target = evaluations.find((item) => item.cropId === e.cropId);
      if (target) target.rankYield = i + 1;
    });

  // Ordenar por margen neto (rentabilidad USD/ha)
  evaluations
    .slice()
    .sort((a, b) => b.financials.netMarginUsdHa - a.financials.netMarginUsdHa)
    .forEach((e, i) => {
      const target = evaluations.find((item) => item.cropId === e.cropId);
      if (target) target.rankMargin = i + 1;
    });

  // Leaderboard ordenado por margen neto descendente por defecto
  const ranking = evaluations.slice().sort((a, b) => b.financials.netMarginUsdHa - a.financials.netMarginUsdHa);

  const winnerCrop = evaluations.slice().sort((a, b) => b.projectedYieldTnHa - a.projectedYieldTnHa)[0];
  const bestMarginCrop = ranking[0];

  const modelMetrics: ModelMetrics = {
    candidateLotsScanned: isDrought ? 342 : 418,
    strictTwinLotsMatched: 12,
    avgSimilarityScore: 0.942,
    dimensionsAnalyzed: [
      "f_soil_clay_pct",
      "f_topo_slope_deg",
      "f_init_water_radar_db",
      "f_water_bal_mm",
      "f_history_ndvi_max",
    ],
    zoneMeanNdvi: zoneNdvi,
  };

  const contentHash = `sha256:7f3a9e${(targetYear * 13).toString(16)}${Math.abs(
    Math.round(surface * 42)
  ).toString(16)}b0c741e9a22409f87c2b3e41`;

  return {
    status: "success",
    schemaVersion: "0.1",
    algorithmVersion: "2.2.0",
    fieldId: field.id,
    lotName: field.name,
    surfaceHa: surface,
    targetYear,
    simulatedCrop: null,
    realCrop,
    winnerCrop,
    bestMarginCrop,
    totalCropsEvaluated: 10,
    ranking,
    contentHash,
    modelMetrics,
    results: {
      projectedYieldTnHa: bestMarginCrop.projectedYieldTnHa,
      benchmarkDeptYieldTnHa: bestMarginCrop.benchmarkDeptYieldTnHa,
      financials: bestMarginCrop.financials,
      recommendation: `En la campaña ${targetYear}, la opción más rentable calculada para ${field.name} (${surface} ha) fue ${bestMarginCrop.cropName}, con una diferencia de ${bestMarginCrop.financials.diffNetMarginUsdHa >= 0 ? "+USD " : "-USD "}${Math.abs(bestMarginCrop.financials.diffNetMarginUsdHa)}/ha respecto a la referencia de ${realCrop} (impacto neto total en el lote: ${bestMarginCrop.financials.totalLotDiffUsd >= 0 ? "+USD " : "-USD "}${Math.abs(bestMarginCrop.financials.totalLotDiffUsd).toLocaleString("es-AR")}).`,
    },
    auditUrls: {
      "Copernicus Browser": "https://browser.dataspace.copernicus.eu/",
      "Open-Meteo ERA5": "https://open-meteo.com/en/docs/historical-weather-api",
      "SoilGrids 250m": "https://rest.isric.org/soilgrids/v2.0/docs",
      "SAGyP Estimaciones": "https://datos.magyp.gob.ar/dataset/estimaciones-agricolas",
    },
  };
}
