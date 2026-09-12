"use client";

import React, { useRef, useMemo } from "react";
import gsap from "gsap";
import { useGSAP } from "@gsap/react";
import { TimelapseFrame } from "@/types/terria";

gsap.registerPlugin(useGSAP);

export interface NdviSparklineChartProps {
  frames: TimelapseFrame[];
  selectedDate: string;
  activeFrameId?: string;
  onSelectDate?: (date: string) => void;
  className?: string;
}

export default function NdviSparklineChart({
  frames,
  selectedDate,
  activeFrameId,
  onSelectDate,
  className = "",
}: NdviSparklineChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const activeDotRef = useRef<SVGCircleElement>(null);

  const usableFrames = useMemo(
    () => frames.filter((f) => f.usable && f.ndvi.mean.value !== null),
    [frames]
  );

  const width = 340;
  const height = 90;
  const paddingX = 14;
  const paddingY = 16;

  // Compute SVG points
  const points = useMemo(() => {
    if (usableFrames.length === 0) return [];
    const minVal = 0.2;
    const maxVal = 0.9;
    const stepX = (width - paddingX * 2) / Math.max(1, usableFrames.length - 1);

    return usableFrames.map((f, i) => {
      const val = f.ndvi.mean.value ?? 0.3;
      const x = paddingX + i * stepX;
      const normalized = (val - minVal) / (maxVal - minVal);
      const y = height - paddingY - normalized * (height - paddingY * 2);
      return { x, y, frame: f };
    });
  }, [usableFrames, width, height]);

  const pathData = useMemo(() => {
    if (points.length === 0) return "";
    return points.reduce((acc, pt, i) => {
      if (i === 0) return `M ${pt.x} ${pt.y}`;
      // Smooth cubic bezier or straight lines
      const prev = points[i - 1];
      const cx1 = prev.x + (pt.x - prev.x) / 2;
      const cy1 = prev.y;
      const cx2 = prev.x + (pt.x - prev.x) / 2;
      const cy2 = pt.y;
      return `${acc} C ${cx1} ${cy1}, ${cx2} ${cy2}, ${pt.x} ${pt.y}`;
    }, "");
  }, [points]);

  const activePoint = useMemo(() => {
    if (!activeFrameId) {
      return points.find((p) => p.frame.localDate <= selectedDate) || points[0];
    }
    return points.find((p) => p.frame.id === activeFrameId) || points[0];
  }, [points, activeFrameId, selectedDate]);

  useGSAP(
    () => {
      if (activeDotRef.current && activePoint) {
        gsap.to(activeDotRef.current, {
          cx: activePoint.x,
          cy: activePoint.y,
          duration: 0.35,
          ease: "power2.out",
        });
      }
    },
    { dependencies: [activePoint?.x, activePoint?.y], scope: containerRef }
  );

  return (
    <div
      ref={containerRef}
      className={`group relative flex flex-col justify-between rounded-2xl border border-piedra-soft bg-papel p-4 shadow-xs transition-colors duration-200 hover:border-bosque select-none ${className}`}
    >
      <div className="flex items-center justify-between border-b border-piedra-soft pb-2">
        <span className="text-[10px] font-mono font-bold tracking-wider text-piedra uppercase">
          Curva Fenológica (Campaña Completa)
        </span>
        <span className="text-[10px] font-mono font-bold text-bosque/80">
          Pico: 0.81
        </span>
      </div>

      <div className="relative my-2 w-full flex justify-center">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="w-full h-22 overflow-visible"
        >
          {/* Baseline grid lines */}
          <line
            x1={paddingX}
            y1={height - paddingY}
            x2={width - paddingX}
            y2={height - paddingY}
            stroke="#dcdcd2"
            strokeWidth="1.5"
          />
          <line
            x1={paddingX}
            y1={paddingY}
            x2={width - paddingX}
            y2={paddingY}
            stroke="#dcdcd2"
            strokeWidth="1.5"
            strokeDasharray="3 3"
          />

          {/* Smooth path */}
          <path
            d={pathData}
            fill="none"
            stroke="#4a6b46"
            strokeWidth="2.5"
            strokeLinecap="round"
          />

          {/* Observation dots */}
          {points.map((pt, idx) => (
            <circle
              key={idx}
              cx={pt.x}
              cy={pt.y}
              r="3"
              fill="#fafaf6"
              stroke="#4a6b46"
              strokeWidth="2"
              className="cursor-pointer hover:r-4 transition-all"
              onClick={() => onSelectDate && onSelectDate(pt.frame.localDate)}
            />
          ))}

          {/* Animated active observation dot */}
          {activePoint && (
            <circle
              ref={activeDotRef}
              cx={activePoint.x}
              cy={activePoint.y}
              r="5.5"
              fill="#1c3a2e"
              stroke="#fafaf6"
              strokeWidth="2.5"
            />
          )}
        </svg>
      </div>

      <div className="flex items-center justify-between text-[10px] font-mono text-piedra border-t border-piedra-soft pt-2">
        <span>{usableFrames[0]?.localDate || "01 Ene"}</span>
        <span className="text-bosque/60 font-bold">Puntos: Observaciones S2</span>
        <span>{usableFrames[usableFrames.length - 1]?.localDate || "01 Mar"}</span>
      </div>
    </div>
  );
}
