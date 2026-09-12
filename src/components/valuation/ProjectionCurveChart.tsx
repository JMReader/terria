"use client";

import React, { useMemo, useRef } from "react";
import gsap from "gsap";
import { useGSAP } from "@gsap/react";
import { LandValuation } from "@/types/valuation";

gsap.registerPlugin(useGSAP);

export interface ProjectionCurveChartProps {
  valuation: LandValuation;
  projectionYears: number;
  onYearsChange: (years: number) => void;
  className?: string;
}

/**
 * Curva compuesta año a año V0 → V_target: replica la interpolación
 * exponencial del motor (`mTotal^(i/N)`) sólo para visualización — los valores
 * de los extremos son los del contrato.
 */
export default function ProjectionCurveChart({
  valuation,
  projectionYears,
  onYearsChange,
  className = "",
}: ProjectionCurveChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const areaRef = useRef<SVGPathElement>(null);

  const width = 340;
  const height = 110;
  const paddingX = 16;
  const paddingTop = 18;
  const paddingBottom = 20;

  const points = useMemo(() => {
    const v = valuation;
    const n = v.projectionYears;
    const mTotal = v.projectedValueUsdHa / v.baseValueUsdHa;
    const minVal = v.baseValueUsdHa;
    const maxVal = v.projectedValueUsdHa;
    const span = Math.max(1, maxVal - minVal);

    return Array.from({ length: n + 1 }, (_, i) => {
      const m = Math.pow(mTotal, i / n);
      const value = v.baseValueUsdHa * m;
      const x = paddingX + (i / n) * (width - paddingX * 2);
      const normalized = (value - minVal) / span;
      const y =
        height - paddingBottom - normalized * (height - paddingTop - paddingBottom);
      return { x, y, year: v.currentYear + i, value };
    });
  }, [valuation]);

  const { linePath, areaPath } = useMemo(() => {
    if (points.length === 0) return { linePath: "", areaPath: "" };
    const line = points.reduce((acc, pt, i) => {
      if (i === 0) return `M ${pt.x} ${pt.y}`;
      const prev = points[i - 1];
      const cx = prev.x + (pt.x - prev.x) / 2;
      return `${acc} C ${cx} ${prev.y}, ${cx} ${pt.y}, ${pt.x} ${pt.y}`;
    }, "");
    const area = `${line} L ${points[points.length - 1].x} ${height - paddingBottom} L ${points[0].x} ${height - paddingBottom} Z`;
    return { linePath: line, areaPath: area };
  }, [points]);

  const lastPoint = points[points.length - 1];

  useGSAP(
    () => {
      if (areaRef.current) {
        gsap.fromTo(
          areaRef.current,
          { autoAlpha: 0.4 },
          { autoAlpha: 1, duration: 0.5, ease: "power2.out" }
        );
      }
    },
    { dependencies: [areaPath], scope: containerRef }
  );

  return (
    <div
      ref={containerRef}
      className={`group relative flex flex-col rounded-2xl border border-piedra-soft bg-papel p-4 shadow-xs transition-colors duration-200 hover:border-bosque select-none ${className}`}
    >
      <div className="flex items-center justify-between border-b border-piedra-soft pb-2">
        <span className="text-[10px] font-mono font-bold tracking-wider text-piedra uppercase">
          Curva de Apreciación Compuesta
        </span>
        <span className="text-[10px] font-mono font-bold text-bosque/80">
          {valuation.currentYear} → {valuation.targetYear}
        </span>
      </div>

      <div className="relative my-2 w-full flex justify-center">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="w-full h-26 overflow-visible"
        >
          <defs>
            <linearGradient id="valArea" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#4a6b46" stopOpacity="0.28" />
              <stop offset="100%" stopColor="#4a6b46" stopOpacity="0.02" />
            </linearGradient>
          </defs>

          {/* Baseline: valor actual */}
          <line
            x1={paddingX}
            y1={height - paddingBottom}
            x2={width - paddingX}
            y2={height - paddingBottom}
            stroke="#dcdcd2"
            strokeWidth="1.5"
          />
          <line
            x1={paddingX}
            y1={points[0]?.y ?? height - paddingBottom}
            x2={width - paddingX}
            y2={points[0]?.y ?? height - paddingBottom}
            stroke="#a7a7a0"
            strokeWidth="1"
            strokeDasharray="4 4"
          />

          <path ref={areaRef} d={areaPath} fill="url(#valArea)" stroke="none" />
          <path
            d={linePath}
            fill="none"
            stroke="#4a6b46"
            strokeWidth="2.5"
            strokeLinecap="round"
          />

          {points.map((pt) => (
            <g key={pt.year}>
              <circle
                cx={pt.x}
                cy={pt.y}
                r="3"
                fill="#fafaf6"
                stroke="#4a6b46"
                strokeWidth="2"
              />
              <text
                x={pt.x}
                y={height - 6}
                textAnchor="middle"
                className="fill-piedra"
                fontSize="7"
                fontFamily="monospace"
              >
                {String(pt.year).slice(2)}
              </text>
            </g>
          ))}

          {lastPoint && (
            <circle
              cx={lastPoint.x}
              cy={lastPoint.y}
              r="6"
              fill="#1c3a2e"
              stroke="#fafaf6"
              strokeWidth="2.5"
            />
          )}
        </svg>
      </div>

      {/* Scrubber de horizonte temporal */}
      <div className="border-t border-piedra-soft pt-3">
        <div className="flex items-center justify-between text-[10px] font-mono text-bosque/60 mb-1.5">
          <span className="uppercase tracking-wider font-bold">Horizonte</span>
          <span className="font-bold text-bosque">
            {projectionYears} {projectionYears === 1 ? "año" : "años"} · target{" "}
            {valuation.currentYear + projectionYears}
          </span>
        </div>
        <input
          type="range"
          min={1}
          max={20}
          step={1}
          value={projectionYears}
          onChange={(e) => onYearsChange(parseInt(e.target.value, 10))}
          className="w-full h-1.5 appearance-none rounded-full bg-piedra-soft accent-musgo cursor-pointer"
        />
        <div className="mt-1 flex items-center justify-between text-[9px] font-mono text-piedra">
          <span>1 año</span>
          <span>20 años</span>
        </div>
      </div>
    </div>
  );
}
