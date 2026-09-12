"use client";

import React, { useRef } from "react";
import gsap from "gsap";
import { useGSAP } from "@gsap/react";
import { TimelineState } from "@/types/terria";

gsap.registerPlugin(useGSAP);

export interface NdviMetricCardProps {
  timelineState: TimelineState;
  className?: string;
}

export default function NdviMetricCard({
  timelineState,
  className = "",
}: NdviMetricCardProps) {
  const cardRef = useRef<HTMLDivElement>(null);
  const { satellite, isFresh, ageDays } = timelineState;

  useGSAP(
    () => {
      gsap.fromTo(
        cardRef.current,
        { autoAlpha: 0.85, scale: 0.995 },
        { autoAlpha: 1, scale: 1, duration: 0.25, ease: "power2.out" }
      );
    },
    { dependencies: [satellite?.id, isFresh], scope: cardRef }
  );

  const meanVal = satellite?.ndvi.mean.value;
  const p10Val = satellite?.ndvi.p10.value;
  const p90Val = satellite?.ndvi.p90.value;
  const validFraction = satellite?.quality.validPixelFraction;

  return (
    <div
      ref={cardRef}
      className={`group relative flex flex-col justify-between rounded-2xl border border-piedra-soft bg-papel p-4.5 shadow-xs transition-colors duration-200 hover:border-musgo cursor-default select-none ${className}`}
    >
      {/* Header */}
      <div className="flex items-center justify-between border-b border-piedra-soft pb-2.5">
        <span className="text-[10px] font-mono font-bold tracking-wider text-piedra uppercase">
          Vigor Vegetativo (NDVI)
        </span>
        <span
          className={`rounded-full px-2 py-0.5 text-[9px] font-mono font-bold tracking-wider uppercase ${
            isFresh && satellite
              ? "bg-musgo/10 text-musgo border border-musgo/30"
              : "bg-nube text-piedra border border-piedra-soft"
          }`}
        >
          {isFresh && satellite ? "Sentinel-2 L2A" : "Sin Cobertura"}
        </span>
      </div>

      {/* Main KPI Body */}
      <div className="py-3">
        {isFresh && satellite && meanVal !== null && meanVal !== undefined ? (
          <div>
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-black tracking-tight text-musgo">
                {meanVal.toFixed(2)}
              </span>
              <span className="text-xs font-mono font-semibold text-piedra">
                / 1.00
              </span>
            </div>

            {/* Gauge bar */}
            <div className="mt-2.5 h-1.5 w-full overflow-hidden rounded-full bg-piedra-soft">
              <div
                className="h-full rounded-full bg-musgo transition-all duration-300"
                style={{ width: `${Math.min(Math.max(meanVal * 100, 0), 100)}%` }}
              />
            </div>

            <div className="mt-2 flex items-center justify-between text-[10px] font-mono text-piedra">
              <span>Rango P10-P90:</span>
              <span className="font-bold text-bosque/80">
                {p10Val?.toFixed(2) ?? "—"} – {p90Val?.toFixed(2) ?? "—"}
              </span>
            </div>
          </div>
        ) : (
          <div className="py-2 space-y-1 text-center">
            <span className="text-xs font-mono font-bold text-bosque/60 block uppercase tracking-wider">
              Sin imagen reciente
            </span>
            <span className="text-[10px] font-mono text-piedra block">
              {ageDays !== null && ageDays > 10
                ? `>10 días sin pasada útil (${ageDays}d)`
                : "Nubosidad o fuera de rango"}
            </span>
          </div>
        )}
      </div>

      {/* Footer Info */}
      <div className="border-t border-piedra-soft pt-2 flex items-center justify-between text-[10px] font-mono text-piedra">
        <span>
          {satellite && isFresh
            ? `Captura: hace ${ageDays ?? 0}d`
            : "Regla máx. 10 días"}
        </span>
        <span>
          {validFraction !== undefined
            ? `${Math.round(validFraction * 100)}% observable`
            : "0% válido"}
        </span>
      </div>
    </div>
  );
}
