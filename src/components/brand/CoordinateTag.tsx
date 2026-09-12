import React from "react";

export interface CoordinateTagProps {
  children: React.ReactNode;
  tone?: "dark" | "light";
  className?: string;
}

/**
 * Microtipografía técnica: coordenadas, hashes, timestamps, versiones.
 * La voz "data" de la marca — siempre mono, tracking amplio, piedra.
 */
export default function CoordinateTag({
  children,
  tone = "dark",
  className = "",
}: CoordinateTagProps) {
  const color = tone === "light" ? "text-nube/60" : "text-piedra";
  return (
    <span
      className={`font-mono text-[10px] uppercase tracking-[0.22em] ${color} ${className}`}
    >
      {children}
    </span>
  );
}
