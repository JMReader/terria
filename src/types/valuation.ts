/* Tipos del frontend (camelCase) para el contrato `land-valuation-5yr`
 * del backend de Angel: POST /v1/valuations/5yr y
 * POST /v1/fields/{field_id}/valuations/5yr.
 */

export interface ValuationDriver {
  /** Aporte porcentual al valor (ej: 6.0 = +6%). */
  impactPercentage: number;
  /** Multiplicador compuesto (ej: 1.06). */
  multiplier: number;
  /** Descripción legible del driver / fuente. */
  detail: string;
}

export interface LogisticDriver extends ValuationDriver {
  distanceToCurrentPavedKm: number;
  distanceToFuturePavedKm: number;
  distanceSavedKm: number;
}

export interface AgronomicDriver extends ValuationDriver {
  /** CAGR anual de rindes SAGyP del departamento (ej: 1.2 = +1.2%/año). */
  cagrAnnualPct: number;
}

export interface MarketDriver extends ValuationDriver {
  /** Apreciación anual compuesta del activo (ej: 2.0 = +2%/año). */
  annualRatePct: number;
}

export interface DriversBreakdown {
  logisticImprovement: LogisticDriver;
  agronomicTrend: AgronomicDriver;
  marketAppreciation: MarketDriver;
}

export interface FinancialTotals {
  surfaceHa: number;
  totalBaseValueUsd: number;
  totalProjectedValueUsd: number;
  totalCapitalGainUsd: number;
}

export interface LandValuation {
  currentYear: number;
  targetYear: number;
  projectionYears: number;
  baseValueUsdHa: number;
  projectedValueUsdHa: number;
  totalAppreciationPercentage: number;
  driversBreakdown: DriversBreakdown;
  financialTotals: FinancialTotals;
  /** SHA-256 hex (64 chars) de los inputs congelados — apto para memo Solana. */
  contentHash: string;
  auditUrls: Record<string, string>;
}

export type ValuationSource = "loading" | "live" | "demo" | "error";
