"use client";

import React, { useRef } from "react";
import gsap from "gsap";
import { useGSAP } from "@gsap/react";
import { ValuationDriver } from "@/types/valuation";

gsap.registerPlugin(useGSAP);

export type DriverAccent = "blue" | "emerald" | "amber";

export interface DriverMultiplierCardProps {
  title: string;
  tag: string;
  driver: ValuationDriver;
  /** Porcentaje que este driver aporta dentro del impacto total (0-100). */
  sharePercent: number;
  accent: DriverAccent;
  extraRows?: { label: string; value: string }[];
  className?: string;
}

const ACCENT_STYLES: Record<
  DriverAccent,
  { chip: string; bar: string; hover: string; value: string }
> = {
  blue: {
    chip: "bg-cielo/15 border-cielo/40 text-cielo-deep",
    bar: "bg-cielo-deep",
    hover: "hover:border-cielo-deep",
    value: "text-cielo-deep",
  },
  emerald: {
    chip: "bg-musgo/10 border-musgo/30 text-musgo",
    bar: "bg-musgo",
    hover: "hover:border-musgo",
    value: "text-musgo",
  },
  amber: {
    chip: "bg-tierra/15 border-tierra/50 text-tierra-deep",
    bar: "bg-tierra-deep",
    hover: "hover:border-tierra-deep",
    value: "text-tierra-deep",
  },
};

export default function DriverMultiplierCard({
  title,
  tag,
  driver,
  sharePercent,
  accent,
  extraRows = [],
  className = "",
}: DriverMultiplierCardProps) {
  const cardRef = useRef<HTMLDivElement>(null);
  const neutral = driver.multiplier <= 1.0001;
  const styles = ACCENT_STYLES[accent];

  useGSAP(
    () => {
      gsap.fromTo(
        cardRef.current,
        { autoAlpha: 0, y: 10 },
        { autoAlpha: 1, y: 0, duration: 0.3, ease: "power2.out" }
      );
    },
    { dependencies: [driver.multiplier], scope: cardRef }
  );

  return (
    <div
      ref={cardRef}
      className={`group relative flex flex-col justify-between rounded-2xl border border-piedra-soft bg-papel p-4 shadow-xs transition-colors duration-200 cursor-default select-none ${
        neutral ? "hover:border-piedra" : styles.hover
      } ${className}`}
    >
      <div className="flex items-center justify-between border-b border-piedra-soft pb-2">
        <span className="text-[10px] font-mono font-bold tracking-wider text-piedra uppercase">
          {title}
        </span>
        <span
          className={`rounded-full px-2 py-0.5 text-[9px] font-mono font-bold tracking-wider uppercase border ${
            neutral
              ? "bg-nube border-piedra-soft text-piedra"
              : styles.chip
          }`}
        >
          {tag}
        </span>
      </div>

      <div className="py-2.5">
        <div className="flex items-baseline gap-2">
          <span
            className={`text-2xl font-black tracking-tight ${
              neutral ? "text-piedra" : styles.value
            }`}
          >
            ×{driver.multiplier.toFixed(3)}
          </span>
          <span
            className={`text-xs font-mono font-bold ${
              neutral ? "text-piedra" : "text-bosque/80"
            }`}
          >
            {neutral ? "±0.0%" : `+${driver.impactPercentage.toFixed(1)}%`}
          </span>
        </div>

        {/* Contribution bar: cuánto pesa este driver dentro del impacto total */}
        <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-piedra-soft">
          <div
            className={`h-full rounded-full transition-all duration-500 ${
              neutral ? "bg-piedra" : styles.bar
            }`}
            style={{ width: `${Math.min(Math.max(sharePercent, 0), 100)}%` }}
          />
        </div>

        <p className="mt-2 text-[10px] font-mono leading-relaxed text-bosque/60">
          {driver.detail}
        </p>

        {extraRows.length > 0 && (
          <div className="mt-2 grid grid-cols-2 gap-1.5">
            {extraRows.map((row) => (
              <div
                key={row.label}
                className="rounded-lg bg-nube border border-piedra-soft px-2 py-1.5"
              >
                <span className="block text-[8px] font-mono font-bold uppercase tracking-wider text-piedra">
                  {row.label}
                </span>
                <span className="block text-[11px] font-mono font-bold text-bosque/80">
                  {row.value}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="border-t border-piedra-soft pt-2 flex items-center justify-between text-[9px] font-mono text-piedra">
        <span>Peso en apreciación</span>
        <span className="font-bold text-bosque/60">
          {neutral ? "—" : `${sharePercent.toFixed(0)}%`}
        </span>
      </div>
    </div>
  );
}
