"use client";

import React from "react";
import { FieldItem } from "@/data/fieldsData";
import { useFieldValuation } from "@/hooks/useFieldValuation";
import MetricStatBox from "@/components/ui/MetricStatBox";
import ValuationHeroCard from "./ValuationHeroCard";
import ProjectionCurveChart from "./ProjectionCurveChart";
import DriverMultiplierCard from "./DriverMultiplierCard";
import ValuationAuditCard from "./ValuationAuditCard";

export interface ValuationPanelProps {
  field: FieldItem;
  sharedValuation?: ReturnType<typeof useFieldValuation>;
  onToggleGpuView?: () => void;
  gpuViewActive?: boolean;
  className?: string;
}

const fmtMillions = (usd: number) => `${(usd / 1_000_000).toFixed(2)}`;
const fmtCompact = (usd: number) =>
  usd >= 1_000_000
    ? `$${fmtMillions(usd)} M`
    : `$${usd.toLocaleString("es-AR", { maximumFractionDigits: 0 })}`;

/**
 * Pestaña "Futuro" del FieldDetailView — consume el proyector de valor de
 * tierra (land-valuation-5yr) del backend de Angel vía useFieldValuation,
 * con fallback demo determinístico cuando la API no responde.
 */
export default function ValuationPanel({
  field,
  sharedValuation,
  onToggleGpuView,
  gpuViewActive = false,
  className = "",
}: ValuationPanelProps) {
  const internal = useFieldValuation(field);
  const ctl = sharedValuation ?? internal;
  const { valuation, source, projectionYears, setProjectionYears } = ctl;
  const d = valuation.driversBreakdown;

  const totalImpact = Math.max(
    0.0001,
    d.logisticImprovement.impactPercentage +
      d.agronomicTrend.impactPercentage +
      d.marketAppreciation.impactPercentage
  );

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Acciones del tab: fuente + toggle vista GPU */}
      <div className="flex items-center justify-between gap-2">
        <span className="text-[10px] font-mono font-bold tracking-wider text-piedra uppercase">
          Futurología · Proyector de valor
        </span>
        {onToggleGpuView && (
          <button
            onClick={onToggleGpuView}
            className={`rounded-xl px-3 py-1.5 text-xs font-mono font-bold transition-all cursor-pointer border ${
              gpuViewActive
                ? "bg-bosque text-nube border-bosque"
                : "bg-papel text-bosque/80 border-piedra-soft hover:border-bosque"
            }`}
          >
            {gpuViewActive ? "Cerrar 3D" : "Proyección 3D"}
          </button>
        )}
      </div>

      <ValuationHeroCard valuation={valuation} source={source} />

      {/* Totales financieros del lote */}
      <div className="grid grid-cols-3 gap-2.5">
        <MetricStatBox
          label={`Lote ${valuation.currentYear}`}
          value={fmtMillions(valuation.financialTotals.totalBaseValueUsd)}
          unit="M USD"
          subtext={`${valuation.financialTotals.surfaceHa} ha`}
          highlight="neutral"
        />
        <MetricStatBox
          label={`Lote ${valuation.targetYear}`}
          value={fmtMillions(valuation.financialTotals.totalProjectedValueUsd)}
          unit="M USD"
          subtext="valor proyectado"
          highlight="blue"
        />
        <MetricStatBox
          label="Ganancia capital"
          value={fmtMillions(valuation.financialTotals.totalCapitalGainUsd)}
          unit="M USD"
          subtext={fmtCompact(valuation.financialTotals.totalCapitalGainUsd)}
          highlight="emerald"
        />
      </div>

      <ProjectionCurveChart
        valuation={valuation}
        projectionYears={projectionYears}
        onYearsChange={setProjectionYears}
      />

      {/* Desglose de los 3 motores de valor */}
      <div>
        <span className="text-[10px] font-mono font-bold tracking-wider text-piedra uppercase block mb-2.5">
          Motores de valor (V0 × M_log × M_agro × M_mkt)
        </span>
        <div className="space-y-2.5">
          <DriverMultiplierCard
            title="Logística vial"
            tag="Overpass · OSM"
            accent="blue"
            driver={d.logisticImprovement}
            sharePercent={
              (d.logisticImprovement.impactPercentage / totalImpact) * 100
            }
            extraRows={[
              {
                label: "Asfalto actual",
                value: `${d.logisticImprovement.distanceToCurrentPavedKm} km`,
              },
              {
                label: "Asfalto futuro",
                value: `${d.logisticImprovement.distanceToFuturePavedKm} km`,
              },
            ]}
          />
          <DriverMultiplierCard
            title="Tendencia agronómica"
            tag="SAGyP · 15 años"
            accent="emerald"
            driver={d.agronomicTrend}
            sharePercent={
              (d.agronomicTrend.impactPercentage / totalImpact) * 100
            }
            extraRows={[
              {
                label: "CAGR rindes",
                value: `+${d.agronomicTrend.cagrAnnualPct.toFixed(1)}%/año`,
              },
              { label: "Factor capitalización", value: "0.8" },
            ]}
          />
          <DriverMultiplierCard
            title="Apreciación de mercado"
            tag="Activo rural USD"
            accent="amber"
            driver={d.marketAppreciation}
            sharePercent={
              (d.marketAppreciation.impactPercentage / totalImpact) * 100
            }
            extraRows={[
              {
                label: "Tasa anual",
                value: `+${d.marketAppreciation.annualRatePct.toFixed(1)}%`,
              },
              { label: "Compuesto", value: `${projectionYears} años` },
            ]}
          />
        </div>
      </div>

      <ValuationAuditCard valuation={valuation} />

      <p className="text-[9px] font-mono leading-relaxed text-piedra px-1">
        Estimación de compatibilidad basada en la información disponible —
        no constituye tasación hipotecaria ni recomendación agronómica.
      </p>
    </div>
  );
}
