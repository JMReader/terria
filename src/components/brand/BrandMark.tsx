import React from "react";

export interface BrandMarkProps {
  /** light = tinta nube sobre fondo oscuro · dark = tinta bosque sobre claro */
  tone?: "dark" | "light";
  withWordmark?: boolean;
  size?: number;
  className?: string;
}

/**
 * Marca TERRIA: estratos de tierra (4 curvas de nivel ascendiendo) + wordmark
 * serif. Un solo componente para header, hero, certificado, footer y favicon.
 */
export function StrataGlyph({
  size = 28,
  className = "",
}: {
  size?: number;
  className?: string;
}) {
  return (
    <svg
      viewBox="0 0 48 48"
      width={size}
      height={size}
      fill="none"
      stroke="currentColor"
      strokeWidth={3}
      strokeLinecap="round"
      aria-hidden="true"
      className={className}
    >
      <path d="M5 14 C13 14 15 7 24 7 C33 7 35 14 43 14" />
      <path d="M5 22 C13 22 15 15 24 15 C33 15 35 22 43 22" />
      <path d="M5 30 C13 30 15 23 24 23 C33 23 35 30 43 30" />
      <path d="M5 38 C13 38 15 31 24 31 C33 31 35 38 43 38" />
    </svg>
  );
}

export default function BrandMark({
  tone = "dark",
  withWordmark = true,
  size = 28,
  className = "",
}: BrandMarkProps) {
  const ink = tone === "light" ? "text-nube" : "text-bosque";
  const rule = tone === "light" ? "text-tierra" : "text-musgo";
  return (
    <span className={`inline-flex items-center gap-2.5 ${ink} ${className}`}>
      <StrataGlyph size={size} />
      {withWordmark && (
        <span className="flex flex-col leading-none">
          <span
            className="font-display font-semibold tracking-[0.22em] uppercase"
            style={{ fontSize: size * 0.62 }}
          >
            Terria
          </span>
          <span
            className={`font-mono uppercase tracking-[0.3em] ${rule}`}
            style={{ fontSize: Math.max(7, size * 0.24) }}
          >
            Certificación de parcelas
          </span>
        </span>
      )}
    </span>
  );
}
