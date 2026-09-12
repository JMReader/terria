"use client";

import React, { useRef } from "react";
import gsap from "gsap";
import { useGSAP } from "@gsap/react";
import { WhatIfSimulation, WhatIfSource } from "@/types/whatIf";

gsap.registerPlugin(useGSAP);

export interface WhatIfHeroCardProps {
  simulation: WhatIfSimulation;
  source: WhatIfSource;
  className?: string;
}

const fmtUsd = (n: number) =>
  n.toLocaleString("es-AR", { maximumFractionDigits: 0 });

function AnimatedNumber({ value, suffix = "", className }: { value: number; suffix?: string; className?: string }) {
  const ref = useRef<HTMLSpanElement>(null);
  const prevRef = useRef(value);

  useGSAP(
    () => {
      const from = prevRef.current;
      const obj = { v: from };
      gsap.to(obj, {
        v: value,
        duration: 0.6,
        ease: "power2.out",
        onUpdate: () => {
          if (ref.current) ref.current.textContent = `${fmtUsd(Math.round(obj.v))}${suffix}`;
        },
        onComplete: () => {
          prevRef.current = value;
        },
      });
    },
    { dependencies: [value] }
  );

  return (
    <span ref={ref} className={className}>
      {fmtUsd(value)}{suffix}
    </span>
  );
}

export default function WhatIfHeroCard({
  simulation,
  source,
  className = "",
}: WhatIfHeroCardProps) {
  const cardRef = useRef<HTMLDivElement>(null);
  const { winnerCrop, bestMarginCrop, realCrop, targetYear, surfaceHa, results } = simulation;

  return (
    <div
      ref={cardRef}
      className={`rounded-3xl border border-piedra-soft bg-papel p-5 sm:p-6 shadow-sm transition-all duration-300 hover:border-bosque/40 ${className}`}
    >
      {/* Header con Badge de Estado */}
      <div className="flex items-center justify-between gap-2 border-b border-piedra-soft pb-3">
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-musgo animate-pulse" />
          <span className="text-[10px] font-mono font-bold tracking-wider text-piedra uppercase">
            Simulador Contrafáctico Multicultivo
          </span>
        </div>

        <span
          className={`rounded-lg px-2 py-0.5 text-[10px] font-mono font-bold uppercase border ${
            source === "live"
              ? "bg-musgo/10 text-musgo border-musgo/30"
              : "bg-tierra/15 text-tierra-deep border-tierra/40"
          }`}
        >
          {source === "live" ? "API Live" : "Modelo Determinístico"}
        </span>
      </div>

      {/* Titular Editorial */}
      <div className="mt-4 space-y-1">
        <h2 className="font-display text-xl sm:text-2xl font-medium text-bosque tracking-tight leading-snug">
          ¿Qué hubiera pasado en la campaña {targetYear}?
        </h2>
        <p className="text-xs font-mono text-bosque/70 leading-relaxed">
          Comparativa retrospectiva contra la siembra real de{" "}
          <strong className="text-bosque font-bold">{realCrop}</strong> evaluando los 10 granos
          del catálogo oficial SAGyP.
        </p>
      </div>

      {/* Tarjetas de Podio: Rendimiento Físico vs Rentabilidad Neta */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-5">
        {/* Ganador en Margen Financiero */}
        <div className="rounded-2xl border border-tierra/40 bg-tierra/10 p-4 relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="rounded-md bg-tierra/20 px-2 py-0.5 text-[9px] font-mono font-bold text-tierra-deep uppercase">
              Máxima Rentabilidad
            </span>
            <span className="text-[10px] font-mono text-tierra-deep font-bold">#1 Margen</span>
          </div>

          <div className="mt-3">
            <div className="text-xs font-mono text-tierra-deep font-bold">
              {bestMarginCrop.cropName} ({bestMarginCrop.season})
            </div>
            <div className="font-display text-2xl sm:text-3xl font-bold text-bosque tracking-tight mt-0.5">
              {bestMarginCrop.financials.diffNetMarginUsdHa >= 0 ? "+" : ""}
              <AnimatedNumber value={bestMarginCrop.financials.diffNetMarginUsdHa} suffix=" USD/ha" />
            </div>
            <p className="text-[11px] font-mono text-bosque/70 mt-1">
              Impacto total lote:{" "}
              <strong className="text-bosque font-bold">
                {bestMarginCrop.financials.totalLotDiffUsd >= 0 ? "+" : "-"}${fmtUsd(Math.abs(bestMarginCrop.financials.totalLotDiffUsd))} USD
              </strong>{" "}
              en {surfaceHa} ha.
            </p>
          </div>
        </div>

        {/* Ganador en Rendimiento Físico */}
        <div className="rounded-2xl border border-musgo/30 bg-musgo/5 p-4 relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="rounded-md bg-musgo/15 px-2 py-0.5 text-[9px] font-mono font-bold text-musgo uppercase">
              Mayor Volumen Físico
            </span>
            <span className="text-[10px] font-mono text-musgo font-bold">#1 Rinde</span>
          </div>

          <div className="mt-3">
            <div className="text-xs font-mono text-musgo font-bold">
              {winnerCrop.cropName} ({winnerCrop.season})
            </div>
            <div className="font-display text-2xl sm:text-3xl font-bold text-bosque tracking-tight mt-0.5">
              {winnerCrop.projectedYieldTnHa} <span className="text-base font-normal font-mono text-bosque/70">tn/ha</span>
            </div>
            <p className="text-[11px] font-mono text-bosque/70 mt-1">
              <span className="text-musgo font-bold">
                {winnerCrop.deltaYieldPct >= 0 ? `+${winnerCrop.deltaYieldPct}%` : `${winnerCrop.deltaYieldPct}%`}
              </span>{" "}
              vs benchmark SAGyP ({winnerCrop.benchmarkDeptYieldTnHa} tn/ha).
            </p>
          </div>
        </div>
      </div>

      {/* Conclusión / Recomendación Dinámica */}
      {results?.recommendation && (
        <div className="mt-4 rounded-xl bg-nube border border-piedra-soft p-3 text-xs font-mono text-bosque/80 leading-relaxed">
          <span className="text-musgo font-bold mr-1">✦ Veredicto Algorítmico:</span>
          {results.recommendation}
        </div>
      )}
    </div>
  );
}
