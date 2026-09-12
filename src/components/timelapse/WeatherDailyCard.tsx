"use client";

import React, { useRef } from "react";
import gsap from "gsap";
import { useGSAP } from "@gsap/react";
import { WeatherDaily } from "@/types/terria";

gsap.registerPlugin(useGSAP);

export interface WeatherDailyCardProps {
  weather: WeatherDaily | null;
  selectedDate: string;
  className?: string;
}

export default function WeatherDailyCard({
  weather,
  selectedDate,
  className = "",
}: WeatherDailyCardProps) {
  const cardRef = useRef<HTMLDivElement>(null);

  useGSAP(
    () => {
      gsap.fromTo(
        cardRef.current,
        { autoAlpha: 0.88, scale: 0.995 },
        { autoAlpha: 1, scale: 1, duration: 0.25, ease: "power2.out" }
      );
    },
    { dependencies: [selectedDate], scope: cardRef }
  );

  const rainDay = weather?.precipitationDay.value;
  const rain7d = weather?.precipitation7d.value;
  const tMin = weather?.temperatureMin.value;
  const tMax = weather?.temperatureMax.value;

  return (
    <div
      ref={cardRef}
      className={`group relative flex flex-col justify-between rounded-2xl border border-piedra-soft bg-papel p-4.5 shadow-xs transition-colors duration-200 hover:border-cielo-deep cursor-default select-none ${className}`}
    >
      {/* Header */}
      <div className="flex items-center justify-between border-b border-piedra-soft pb-2.5">
        <span className="text-[10px] font-mono font-bold tracking-wider text-piedra uppercase">
          Clima Histórico
        </span>
        <span className="rounded-full bg-cielo/15 border border-cielo/40 px-2 py-0.5 text-[9px] font-mono font-bold text-cielo-deep tracking-wider uppercase">
          ERA5 Reanalysis
        </span>
      </div>

      {/* Grid of 2 key weather metrics */}
      <div className="grid grid-cols-2 gap-3 py-3">
        {/* Rainfall */}
        <div className="rounded-xl bg-nube border border-piedra-soft p-2.5 transition-colors group-hover:bg-cielo/10">
          <span className="text-[9px] font-mono font-bold text-piedra uppercase tracking-wider block">
            Lluvia del Día
          </span>
          <div className="mt-1 flex items-baseline gap-1">
            <span className="text-xl font-black tracking-tight text-bosque">
              {rainDay !== null && rainDay !== undefined ? rainDay.toFixed(1) : "—"}
            </span>
            <span className="text-[11px] font-mono text-piedra font-bold">
              mm
            </span>
          </div>
          <span className="text-[10px] font-mono text-cielo-deep block mt-1 font-semibold">
            {rain7d !== null && rain7d !== undefined ? `${rain7d.toFixed(1)} mm / 7d` : "7d: —"}
          </span>
        </div>

        {/* Temperature */}
        <div className="rounded-xl bg-nube border border-piedra-soft p-2.5 transition-colors group-hover:bg-cielo/10">
          <span className="text-[9px] font-mono font-bold text-piedra uppercase tracking-wider block">
            Régimen Térmico
          </span>
          <div className="mt-1 flex items-baseline gap-1">
            <span className="text-xl font-black tracking-tight text-bosque">
              {tMax !== null && tMax !== undefined ? `${Math.round(tMax)}°` : "—"}
            </span>
            <span className="text-[11px] font-mono text-piedra font-medium">
              máx
            </span>
          </div>
          <span className="text-[10px] font-mono text-bosque/60 block mt-1 font-semibold">
            {tMin !== null && tMin !== undefined ? `Mín: ${Math.round(tMin)}°C` : "Mín: —"}
          </span>
        </div>
      </div>

      {/* Footer info */}
      <div className="border-t border-piedra-soft pt-2 flex items-center justify-between text-[10px] font-mono text-piedra">
        <span>Día: {selectedDate || "—"}</span>
        <span>Reanálisis 0.25°</span>
      </div>
    </div>
  );
}
