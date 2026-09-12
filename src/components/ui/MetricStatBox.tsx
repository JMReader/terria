"use client";

import React, { useRef } from "react";
import gsap from "gsap";
import { useGSAP } from "@gsap/react";

gsap.registerPlugin(useGSAP);

export interface MetricStatBoxProps {
  label: string;
  value: string | number | null;
  unit?: string;
  subtext?: string;
  progressPercent?: number;
  highlight?: "neutral" | "emerald" | "blue" | "amber";
  className?: string;
}

export default function MetricStatBox({
  label,
  value,
  unit,
  subtext,
  progressPercent,
  highlight = "neutral",
  className = "",
}: MetricStatBoxProps) {
  const cardRef = useRef<HTMLDivElement>(null);
  const valueRef = useRef<HTMLDivElement>(null);

  useGSAP(
    () => {
      // Subtle pulse / bounce on value change
      if (valueRef.current) {
        gsap.fromTo(
          valueRef.current,
          { autoAlpha: 0.5, y: 3 },
          { autoAlpha: 1, y: 0, duration: 0.25, ease: "power2.out" }
        );
      }
    },
    { dependencies: [value], scope: cardRef }
  );

  const getHighlightColor = () => {
    switch (highlight) {
      case "emerald":
        return "hover:border-emerald-600 text-emerald-700";
      case "blue":
        return "hover:border-blue-600 text-blue-700";
      case "amber":
        return "hover:border-amber-600 text-amber-700";
      default:
        return "hover:border-gray-900 text-gray-900";
    }
  };

  const getProgressColor = () => {
    switch (highlight) {
      case "emerald":
        return "bg-emerald-600";
      case "blue":
        return "bg-blue-600";
      case "amber":
        return "bg-amber-500";
      default:
        return "bg-gray-900";
    }
  };

  return (
    <div
      ref={cardRef}
      className={`group relative flex flex-col justify-between rounded-2xl border border-gray-200 bg-white p-4 transition-all duration-200 cursor-default shadow-xs hover:shadow-sm ${getHighlightColor()} ${className}`}
    >
      <div>
        <div className="flex items-center justify-between gap-2">
          <span className="text-[10px] font-mono font-bold tracking-wider text-gray-400 uppercase">
            {label}
          </span>
          <span className="h-1.5 w-1.5 rounded-full bg-gray-200 group-hover:bg-gray-900 transition-colors" />
        </div>

        <div ref={valueRef} className="mt-2 flex items-baseline gap-1.5">
          <span className="text-2xl font-black tracking-tight text-gray-900">
            {value !== null && value !== undefined ? value : "—"}
          </span>
          {unit && (
            <span className="text-xs font-mono font-semibold text-gray-500">
              {unit}
            </span>
          )}
        </div>
      </div>

      {(progressPercent !== undefined || subtext) && (
        <div className="mt-3 space-y-1.5">
          {progressPercent !== undefined && (
            <div className="h-1 w-full overflow-hidden rounded-full bg-gray-100">
              <div
                className={`h-full rounded-full transition-all duration-300 ${getProgressColor()}`}
                style={{ width: `${Math.min(Math.max(progressPercent, 0), 100)}%` }}
              />
            </div>
          )}
          {subtext && (
            <span className="block text-[11px] font-mono text-gray-400">
              {subtext}
            </span>
          )}
        </div>
      )}
    </div>
  );
}
