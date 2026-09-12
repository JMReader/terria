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
      className={`group relative flex flex-col justify-between rounded-2xl border border-gray-200 bg-white p-4.5 shadow-xs transition-colors duration-200 hover:border-emerald-600 cursor-default select-none ${className}`}
    >
      {/* Header */}
      <div className="flex items-center justify-between border-b border-gray-100 pb-2.5">
        <span className="text-[10px] font-mono font-bold tracking-wider text-gray-400 uppercase">
          Vigor Vegetativo (NDVI)
        </span>
        <span
          className={`rounded-full px-2 py-0.5 text-[9px] font-mono font-bold tracking-wider uppercase ${
            isFresh && satellite
              ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
              : "bg-gray-100 text-gray-500 border border-gray-200"
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
              <span className="text-3xl font-black tracking-tight text-emerald-800">
                {meanVal.toFixed(2)}
              </span>
              <span className="text-xs font-mono font-semibold text-gray-400">
                / 1.00
              </span>
            </div>

            {/* Gauge bar */}
            <div className="mt-2.5 h-1.5 w-full overflow-hidden rounded-full bg-gray-100">
              <div
                className="h-full rounded-full bg-emerald-600 transition-all duration-300"
                style={{ width: `${Math.min(Math.max(meanVal * 100, 0), 100)}%` }}
              />
            </div>

            <div className="mt-2 flex items-center justify-between text-[10px] font-mono text-gray-500">
              <span>Rango P10-P90:</span>
              <span className="font-bold text-gray-700">
                {p10Val?.toFixed(2) ?? "—"} – {p90Val?.toFixed(2) ?? "—"}
              </span>
            </div>
          </div>
        ) : (
          <div className="py-2 space-y-1 text-center">
            <span className="text-xs font-mono font-bold text-gray-500 block uppercase tracking-wider">
              Sin imagen reciente
            </span>
            <span className="text-[10px] font-mono text-gray-400 block">
              {ageDays !== null && ageDays > 10
                ? `>10 días sin pasada útil (${ageDays}d)`
                : "Nubosidad o fuera de rango"}
            </span>
          </div>
        )}
      </div>

      {/* Footer Info */}
      <div className="border-t border-gray-100 pt-2 flex items-center justify-between text-[10px] font-mono text-gray-400">
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
