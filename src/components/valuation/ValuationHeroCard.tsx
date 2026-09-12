"use client";

import React, { useRef } from "react";
import gsap from "gsap";
import { useGSAP } from "@gsap/react";
import { LandValuation, ValuationSource } from "@/types/valuation";

gsap.registerPlugin(useGSAP);

export interface ValuationHeroCardProps {
  valuation: LandValuation;
  source: ValuationSource;
  className?: string;
}

const fmtUsd = (n: number) =>
  n.toLocaleString("es-AR", { maximumFractionDigits: 0 });

/** Número que anima su transición con GSAP al cambiar de valuación/años. */
function AnimatedUsd({ value, className }: { value: number; className?: string }) {
  const ref = useRef<HTMLSpanElement>(null);
  const prevRef = useRef(value);

  useGSAP(
    () => {
      const from = prevRef.current;
      const obj = { v: from };
      gsap.to(obj, {
        v: value,
        duration: 0.7,
        ease: "power2.out",
        onUpdate: () => {
          if (ref.current) ref.current.textContent = fmtUsd(obj.v);
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
      {fmtUsd(value)}
    </span>
  );
}

export default function ValuationHeroCard({
  valuation,
  source,
  className = "",
}: ValuationHeroCardProps) {
  const cardRef = useRef<HTMLDivElement>(null);
  const v = valuation;
  const d = v.driversBreakdown;

  const totalImpact = Math.max(
    0.0001,
    d.logisticImprovement.impactPercentage +
      d.agronomicTrend.impactPercentage +
      d.marketAppreciation.impactPercentage
  );
  const shares = [
    { pct: (d.logisticImprovement.impactPercentage / totalImpact) * 100, color: "bg-cielo-deep" },
    { pct: (d.agronomicTrend.impactPercentage / totalImpact) * 100, color: "bg-musgo" },
    { pct: (d.marketAppreciation.impactPercentage / totalImpact) * 100, color: "bg-tierra-deep" },
  ];

  return (
    <div
      ref={cardRef}
      className={`group relative flex flex-col rounded-2xl border border-piedra-soft bg-papel p-4.5 shadow-xs transition-colors duration-200 hover:border-bosque select-none ${className}`}
    >
      <div className="flex items-center justify-between border-b border-piedra-soft pb-2.5">
        <span className="text-[10px] font-mono font-bold tracking-wider text-piedra uppercase">
          Proyección de Valor · {v.projectionYears} años
        </span>
        <span
          className={`rounded-full px-2 py-0.5 text-[9px] font-mono font-bold tracking-wider uppercase border ${
            source === "live"
              ? "bg-musgo/10 border-musgo/30 text-musgo"
              : "bg-nube border-piedra-soft text-piedra"
          }`}
        >
          {source === "live"
            ? "● En vivo"
            : source === "loading"
              ? "Conectando…"
              : "Demo local"}
        </span>
      </div>

      {/* Comparativa central: hoy → target */}
      <div className="flex items-end justify-between gap-3 py-3.5">
        <div>
          <span className="block text-[9px] font-mono font-bold uppercase tracking-wider text-piedra">
            USD/ha · {v.currentYear}
          </span>
          <span className="text-2xl font-black tracking-tight text-piedra">
            <AnimatedUsd value={v.baseValueUsdHa} />
          </span>
        </div>

        <span className="pb-1 text-lg font-black text-piedra-soft">→</span>

        <div className="text-right">
          <span className="block text-[9px] font-mono font-bold uppercase tracking-wider text-musgo">
            USD/ha · {v.targetYear}
          </span>
          <span className="text-3xl font-black tracking-tight text-bosque">
            <AnimatedUsd value={v.projectedValueUsdHa} />
          </span>
        </div>
      </div>

      {/* ROI chip */}
      <div className="flex items-center gap-2">
        <span className="rounded-xl bg-musgo/10 border border-musgo/30 px-2.5 py-1 text-xs font-mono font-bold text-musgo">
          ROI +{v.totalAppreciationPercentage.toFixed(1)}%
        </span>
        <span className="text-[10px] font-mono text-piedra">
          retorno pasivo del suelo
        </span>
      </div>

      {/* Barra de composición: peso de cada driver en el impacto total */}
      <div className="mt-3">
        <div className="flex h-1.5 w-full overflow-hidden rounded-full bg-piedra-soft">
          {shares.map((s, i) => (
            <div
              key={i}
              className={`h-full ${s.color} transition-all duration-500`}
              style={{ width: `${s.pct}%` }}
            />
          ))}
        </div>
        <div className="mt-1.5 flex items-center justify-between text-[9px] font-mono text-piedra">
          <span>Vial · Agro · Mercado</span>
          <span className="font-bold text-bosque/60">
            ×{(v.projectedValueUsdHa / v.baseValueUsdHa).toFixed(3)} compuesto
          </span>
        </div>
      </div>
    </div>
  );
}
