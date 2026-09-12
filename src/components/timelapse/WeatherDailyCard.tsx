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
      className={`group relative flex flex-col justify-between rounded-2xl border border-gray-200 bg-white p-4.5 shadow-xs transition-colors duration-200 hover:border-blue-600 cursor-default select-none ${className}`}
    >
      {/* Header */}
      <div className="flex items-center justify-between border-b border-gray-100 pb-2.5">
        <span className="text-[10px] font-mono font-bold tracking-wider text-gray-400 uppercase">
          Clima Histórico
        </span>
        <span className="rounded-full bg-blue-50 border border-blue-200 px-2 py-0.5 text-[9px] font-mono font-bold text-blue-700 tracking-wider uppercase">
          ERA5 Reanalysis
        </span>
      </div>

      {/* Grid of 2 key weather metrics */}
      <div className="grid grid-cols-2 gap-3 py-3">
        {/* Rainfall */}
        <div className="rounded-xl bg-gray-50/70 border border-gray-100 p-2.5 transition-colors group-hover:bg-blue-50/30">
          <span className="text-[9px] font-mono font-bold text-gray-400 uppercase tracking-wider block">
            Lluvia del Día
          </span>
          <div className="mt-1 flex items-baseline gap-1">
            <span className="text-xl font-black tracking-tight text-gray-900">
              {rainDay !== null && rainDay !== undefined ? rainDay.toFixed(1) : "—"}
            </span>
            <span className="text-[11px] font-mono text-gray-500 font-bold">
              mm
            </span>
          </div>
          <span className="text-[10px] font-mono text-blue-700 block mt-1 font-semibold">
            {rain7d !== null && rain7d !== undefined ? `${rain7d.toFixed(1)} mm / 7d` : "7d: —"}
          </span>
        </div>

        {/* Temperature */}
        <div className="rounded-xl bg-gray-50/70 border border-gray-100 p-2.5 transition-colors group-hover:bg-blue-50/30">
          <span className="text-[9px] font-mono font-bold text-gray-400 uppercase tracking-wider block">
            Régimen Térmico
          </span>
          <div className="mt-1 flex items-baseline gap-1">
            <span className="text-xl font-black tracking-tight text-gray-900">
              {tMax !== null && tMax !== undefined ? `${Math.round(tMax)}°` : "—"}
            </span>
            <span className="text-[11px] font-mono text-gray-400 font-medium">
              máx
            </span>
          </div>
          <span className="text-[10px] font-mono text-gray-500 block mt-1 font-semibold">
            {tMin !== null && tMin !== undefined ? `Mín: ${Math.round(tMin)}°C` : "Mín: —"}
          </span>
        </div>
      </div>

      {/* Footer info */}
      <div className="border-t border-gray-100 pt-2 flex items-center justify-between text-[10px] font-mono text-gray-400">
        <span>Día: {selectedDate || "—"}</span>
        <span>Reanálisis 0.25°</span>
      </div>
    </div>
  );
}
