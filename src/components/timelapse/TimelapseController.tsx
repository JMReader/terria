"use client";

import React, { useRef } from "react";
import gsap from "gsap";
import { useGSAP } from "@gsap/react";
import { TimelineState, TimelapseLayer } from "@/types/terria";

gsap.registerPlugin(useGSAP);

export interface TimelapseControllerProps {
  dates: string[];
  dateIndex: number;
  onDateIndexChange: (idx: number) => void;
  timelineState: TimelineState;
  isPlaying: boolean;
  onTogglePlay: () => void;
  speed: 1 | 2 | 4;
  onSpeedChange: (speed: 1 | 2 | 4) => void;
  activeLayer: TimelapseLayer;
  onLayerChange: (layer: TimelapseLayer) => void;
  onStepNext: () => void;
  onStepPrev: () => void;
  onJumpObservation: (direction: "prev" | "next") => void;
  className?: string;
}

export default function TimelapseController({
  dates,
  dateIndex,
  onDateIndexChange,
  timelineState,
  isPlaying,
  onTogglePlay,
  speed,
  onSpeedChange,
  activeLayer,
  onLayerChange,
  onStepNext,
  onStepPrev,
  onJumpObservation,
  className = "",
}: TimelapseControllerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const statusBadgeRef = useRef<HTMLSpanElement>(null);

  useGSAP(
    () => {
      gsap.fromTo(
        containerRef.current,
        { autoAlpha: 0, y: 20 },
        { autoAlpha: 1, y: 0, duration: 0.45, ease: "power3.out" }
      );
    },
    { scope: containerRef }
  );

  useGSAP(
    () => {
      if (statusBadgeRef.current) {
        gsap.fromTo(
          statusBadgeRef.current,
          { autoAlpha: 0.6, scale: 0.98 },
          { autoAlpha: 1, scale: 1, duration: 0.2, ease: "power2.out" }
        );
      }
    },
    { dependencies: [timelineState.satellite?.id, timelineState.isFresh], scope: containerRef }
  );

  const { selectedDate, satellite, isFresh, ageDays } = timelineState;

  return (
    <div
      ref={containerRef}
      className={`group relative flex flex-col gap-2.5 rounded-3xl border border-gray-200 bg-white p-3.5 sm:p-4 shadow-md transition-colors duration-200 hover:border-gray-900 select-none ${className}`}
    >
      {/* Top Status & Layer Switcher Bar */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-gray-100 pb-2.5">
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono font-black text-gray-900 tracking-tight">
            {selectedDate || "2025-01-01"}
          </span>

          <span
            ref={statusBadgeRef}
            className={`rounded-full px-2.5 py-0.5 text-[10px] font-mono font-bold tracking-wider uppercase border ${
              isFresh && satellite
                ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                : "bg-gray-100 text-gray-600 border-gray-200"
            }`}
          >
            {isFresh && satellite
              ? `Sentinel: hace ${ageDays ?? 0}d`
              : "Sin imagen reciente (>10d)"}
          </span>
        </div>

        {/* Layer Segmented Control (NDVI vs RGB vs Weather) */}
        <div className="flex items-center rounded-xl bg-gray-100 p-0.5 border border-gray-200">
          <button
            onClick={() => onLayerChange("ndvi")}
            className={`rounded-lg px-2.5 py-1 text-[10px] font-mono font-bold tracking-wider uppercase transition-all cursor-pointer ${
              activeLayer === "ndvi"
                ? "bg-white text-emerald-800 shadow-xs border border-gray-200"
                : "text-gray-500 hover:text-gray-900"
            }`}
          >
            NDVI Vigor
          </button>
          <button
            onClick={() => onLayerChange("rgb")}
            className={`rounded-lg px-2.5 py-1 text-[10px] font-mono font-bold tracking-wider uppercase transition-all cursor-pointer ${
              activeLayer === "rgb"
                ? "bg-white text-blue-800 shadow-xs border border-gray-200"
                : "text-gray-500 hover:text-gray-900"
            }`}
          >
            RGB Natural
          </button>
          <button
            onClick={() => onLayerChange("weather")}
            className={`rounded-lg px-2.5 py-1 text-[10px] font-mono font-bold tracking-wider uppercase transition-all cursor-pointer ${
              activeLayer === "weather"
                ? "bg-white text-amber-700 shadow-xs border border-gray-200"
                : "text-gray-500 hover:text-gray-900"
            }`}
          >
            ERA5 Clima
          </button>
        </div>
      </div>

      {/* Scrubber Range Slider */}
      <div className="flex flex-col gap-1">
        <input
          type="range"
          min={0}
          max={Math.max(0, dates.length - 1)}
          value={dateIndex}
          onChange={(e) => onDateIndexChange(Number(e.target.value))}
          className="w-full accent-gray-900 h-1.5 bg-gray-100 rounded-lg appearance-none cursor-pointer"
        />
        <div className="flex justify-between text-[9px] font-mono text-gray-400">
          <span>{dates[0] || "Inicio"}</span>
          <span>Paso diario</span>
          <span>{dates[dates.length - 1] || "Fin"}</span>
        </div>
      </div>

      {/* Bottom Action Controls */}
      <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
        <div className="flex items-center gap-1.5">
          {/* Play/Pause Button */}
          <button
            onClick={onTogglePlay}
            className={`rounded-xl px-3 py-1.5 text-xs font-mono font-bold tracking-wider uppercase transition-all duration-150 cursor-pointer shadow-xs active:scale-[0.98] ${
              isPlaying
                ? "bg-amber-600 text-white hover:bg-amber-700"
                : "bg-gray-900 text-white hover:bg-black"
            }`}
          >
            {isPlaying ? "Pausa" : "Reproducir"}
          </button>

          {/* Daily Steppers */}
          <button
            onClick={onStepPrev}
            title="Día anterior"
            className="rounded-xl border border-gray-200 bg-white hover:border-gray-900 px-2.5 py-1.5 text-[11px] font-mono font-bold text-gray-700 transition-colors cursor-pointer"
          >
            ‹ Día
          </button>
          <button
            onClick={onStepNext}
            title="Día siguiente"
            className="rounded-xl border border-gray-200 bg-white hover:border-gray-900 px-2.5 py-1.5 text-[11px] font-mono font-bold text-gray-700 transition-colors cursor-pointer"
          >
            Día ›
          </button>

          {/* Jump to Observations */}
          <button
            onClick={() => onJumpObservation("prev")}
            title="Observación satelital previa"
            className="hidden sm:inline-block rounded-xl border border-gray-200 bg-gray-50 hover:border-gray-900 px-2.5 py-1.5 text-[10px] font-mono font-semibold text-gray-600 transition-colors cursor-pointer"
          >
            ‹ Satélite
          </button>
          <button
            onClick={() => onJumpObservation("next")}
            title="Observación satelital siguiente"
            className="hidden sm:inline-block rounded-xl border border-gray-200 bg-gray-50 hover:border-gray-900 px-2.5 py-1.5 text-[10px] font-mono font-semibold text-gray-600 transition-colors cursor-pointer"
          >
            Satélite ›
          </button>
        </div>

        {/* Playback Speed Segment */}
        <div className="flex items-center rounded-xl bg-gray-100 p-0.5 border border-gray-200 text-[10px] font-mono">
          {([1, 2, 4] as const).map((s) => (
            <button
              key={s}
              onClick={() => onSpeedChange(s)}
              className={`rounded-lg px-2 py-1 font-bold transition-all cursor-pointer ${
                speed === s
                  ? "bg-white text-gray-900 shadow-xs border border-gray-200"
                  : "text-gray-500 hover:text-gray-900"
              }`}
            >
              {s}X
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
