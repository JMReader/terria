import React, { useMemo } from "react";

export interface ContourLinesProps {
  /** dark = líneas claras sobre bosque · light = líneas piedra sobre nube */
  tone?: "dark" | "light";
  /** cantidad de estratos */
  lines?: number;
  className?: string;
}

/**
 * Textura de curvas de nivel / estratos de tierra. Fondo editorial reutilizable
 * para hero, certificado y footer. Determinista (sin random en render).
 */
export default function ContourLines({
  tone = "dark",
  lines = 12,
  className = "",
}: ContourLinesProps) {
  const paths = useMemo(() => {
    const w = 1440;
    const h = 400;
    return Array.from({ length: lines }, (_, i) => {
      const yBase = (h / (lines - 1)) * i;
      const amp = 14 + ((i * 37) % 22);
      const phase = (i * 53) % 100;
      // Curva suave: dos ondas con desfase — parece relieve, no ruido.
      const d = `M -20 ${yBase}
        C ${w * 0.18} ${yBase - amp + (phase % 7)},
          ${w * 0.32} ${yBase + amp - (phase % 5)},
          ${w * 0.5} ${yBase + (phase % 9) - 4}
        S ${w * 0.82} ${yBase - amp * 0.7},
          ${w + 20} ${yBase + (phase % 6)}`;
      return d;
    });
  }, [lines]);

  const stroke = tone === "dark" ? "#8a9a6b" : "#a7a7a0";

  return (
    <svg
      viewBox="0 0 1440 400"
      preserveAspectRatio="xMidYMid slice"
      aria-hidden="true"
      className={`pointer-events-none h-full w-full ${className}`}
    >
      {paths.map((d, i) => (
        <path
          key={i}
          d={d}
          fill="none"
          stroke={stroke}
          strokeWidth={1}
          strokeOpacity={tone === "dark" ? 0.22 : 0.35}
          className="contour-line"
        />
      ))}
    </svg>
  );
}
