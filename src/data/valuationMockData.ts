import { FieldItem } from "./fieldsData";
import { LandValuation } from "@/types/valuation";

/**
 * Réplica determinística de la ecuación del motor de valuación de Angel:
 *   Projected = V0 × M_log × M_agro × M_mkt
 * Nada de resultados sueltos hardcodeados: cada número se deriva de la zona
 * del campo con las mismas reglas de negocio del spec (+3% cada 10 km de
 * acercamiento al asfalto, tope +15%; CAGR SAGyP × factor 0.8; mercado
 * +2%/año compuesto). Se usa sólo como fallback cuando la API no responde.
 */

interface DemoZoneParams {
  baseValueUsdHa: number;
  cagrAnnualPct: number;
  distanceToCurrentPavedKm: number;
  distanceToFuturePavedKm: number;
  roadDetail: string;
  agroDetail: string;
}

const DEMO_ZONE_PARAMS: Record<string, DemoZoneParams> = {
  "la-esperanza": {
    baseValueUsdHa: 8400,
    cagrAnnualPct: 1.3,
    distanceToCurrentPavedKm: 4,
    distanceToFuturePavedKm: 4,
    roadDetail:
      "Lote consolidado sobre Av. 11 de Septiembre — sin nuevas trazas viales en 50 km",
    agroDetail: "CAGR rindes maíz/soja 15 años — Depto. Río Cuarto (SAGyP)",
  },
  "don-pedro": {
    baseValueUsdHa: 9500,
    cagrAnnualPct: 1.5,
    distanceToCurrentPavedKm: 28,
    distanceToFuturePavedKm: 8,
    roadDetail:
      "Autovía RN 8 (tramo Pergamino–Arrecifes) en ejecución — acerca el pavimento 20 km",
    agroDetail: "CAGR rindes soja 15 años — Depto. Pergamino, zona núcleo (SAGyP)",
  },
  "el-ombu": {
    baseValueUsdHa: 7900,
    cagrAnnualPct: 1.15,
    distanceToCurrentPavedKm: 35,
    distanceToFuturePavedKm: 20,
    roadDetail:
      "Corredor RN 8 sur propuesto en Overpass/OSM — ahorra 15 km al asfalto",
    agroDetail: "CAGR rindes maíz/trigo 15 años — Depto. Gral. López (SAGyP)",
  },
  "san-jeronimo": {
    baseValueUsdHa: 8200,
    cagrAnnualPct: 1.3,
    distanceToCurrentPavedKm: 22,
    distanceToFuturePavedKm: 12,
    roadDetail:
      "Variante RN 158 / acceso Villa María en obra — ahorra 10 km al asfalto",
    agroDetail: "CAGR rindes trigo/soja 15 años — Depto. Gral. San Martín (SAGyP)",
  },
  "la-josefina": {
    baseValueUsdHa: 5900,
    cagrAnnualPct: 1.45,
    distanceToCurrentPavedKm: 40,
    distanceToFuturePavedKm: 15,
    roadDetail:
      "Repavimentación RP 65 corredor exportador — ahorra 25 km al asfalto",
    agroDetail: "CAGR rindes papa/cebada 15 años — Depto. Balcarce (SAGyP)",
  },
};

const DEFAULT_ZONE: DemoZoneParams = {
  baseValueUsdHa: 7000,
  cagrAnnualPct: 1.0,
  distanceToCurrentPavedKm: 30,
  distanceToFuturePavedKm: 30,
  roadDetail: "Sin obras viales detectadas en el radio de 50 km",
  agroDetail: "CAGR zonal SAGyP — serie departamental 15 años",
};

const AUDIT_URLS: Record<string, string> = {
  idecor: "https://www.idecor.gov.ar",
  overpass: "https://overpass-turbo.eu",
  sagyp: "https://www.argentina.gob.ar/agricultura",
};

const round = (n: number, digits = 4) => {
  const f = 10 ** digits;
  return Math.round(n * f) / f;
};

/** Hash determinista estilo SHA-256 para el demo (cyrb53 × 4 seeds → 64 hex). */
function demoHash(payload: string): string {
  const cyrb53 = (str: string, seed: number) => {
    let h1 = 0xdeadbeef ^ seed;
    let h2 = 0x41c6ce57 ^ seed;
    for (let i = 0; i < str.length; i++) {
      const ch = str.charCodeAt(i);
      h1 = Math.imul(h1 ^ ch, 2654435761);
      h2 = Math.imul(h2 ^ ch, 1597334677);
    }
    h1 =
      Math.imul(h1 ^ (h1 >>> 16), 2246822507) ^
      Math.imul(h2 ^ (h2 >>> 13), 3266489909);
    h2 =
      Math.imul(h2 ^ (h2 >>> 16), 2246822507) ^
      Math.imul(h1 ^ (h1 >>> 13), 3266489909);
    return ((h2 >>> 0).toString(16) + (h1 >>> 0).toString(16)).padStart(16, "0");
  };
  return [0, 1, 2, 3].map((s) => cyrb53(payload, s)).join("");
}

export function computeDemoValuation(
  field: FieldItem,
  projectionYears = 5
): LandValuation {
  const zone = DEMO_ZONE_PARAMS[field.id] ?? DEFAULT_ZONE;
  const currentYear = new Date().getFullYear();
  const targetYear = currentYear + projectionYears;

  // M_log: +3% cada 10 km de acercamiento al asfalto, piso 1.0, techo +15%
  const distanceSavedKm = Math.max(
    0,
    zone.distanceToCurrentPavedKm - zone.distanceToFuturePavedKm
  );
  const logisticImpactPct = Math.min(15, distanceSavedKm * 0.3);
  const logisticMultiplier = 1 + logisticImpactPct / 100;

  // M_agro: CAGR departamental × factor de capitalización 0.8 × N años
  const agroImpactPct = zone.cagrAnnualPct * 0.8 * projectionYears;
  const agroMultiplier = 1 + agroImpactPct / 100;

  // M_mkt: +2% anual compuesto
  const marketMultiplier = Math.pow(1.02, projectionYears);
  const marketImpactPct = (marketMultiplier - 1) * 100;

  const totalMultiplier = logisticMultiplier * agroMultiplier * marketMultiplier;
  const projectedValueUsdHa = zone.baseValueUsdHa * totalMultiplier;
  const surfaceHa = field.hectares;
  const totalBaseUsd = zone.baseValueUsdHa * surfaceHa;
  const totalProjectedUsd = projectedValueUsdHa * surfaceHa;

  const valuation: Omit<LandValuation, "contentHash"> = {
    currentYear,
    targetYear,
    projectionYears,
    baseValueUsdHa: round(zone.baseValueUsdHa, 2),
    projectedValueUsdHa: round(projectedValueUsdHa, 2),
    totalAppreciationPercentage: round((totalMultiplier - 1) * 100, 2),
    driversBreakdown: {
      logisticImprovement: {
        impactPercentage: round(logisticImpactPct, 2),
        multiplier: round(logisticMultiplier, 4),
        detail: zone.roadDetail,
        distanceToCurrentPavedKm: zone.distanceToCurrentPavedKm,
        distanceToFuturePavedKm: zone.distanceToFuturePavedKm,
        distanceSavedKm,
      },
      agronomicTrend: {
        impactPercentage: round(agroImpactPct, 2),
        multiplier: round(agroMultiplier, 4),
        detail: zone.agroDetail,
        cagrAnnualPct: zone.cagrAnnualPct,
      },
      marketAppreciation: {
        impactPercentage: round(marketImpactPct, 2),
        multiplier: round(marketMultiplier, 4),
        detail: "Apreciación tendencial del activo rural en USD (+2%/año compuesto)",
        annualRatePct: 2.0,
      },
    },
    financialTotals: {
      surfaceHa,
      totalBaseValueUsd: round(totalBaseUsd, 2),
      totalProjectedValueUsd: round(totalProjectedUsd, 2),
      totalCapitalGainUsd: round(totalProjectedUsd - totalBaseUsd, 2),
    },
    auditUrls: AUDIT_URLS,
  };

  return {
    ...valuation,
    contentHash: demoHash(JSON.stringify({ field: field.id, ...valuation })),
  };
}
