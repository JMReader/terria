import React from "react";
import { StrataGlyph } from "./BrandMark";

export type SealState = "verified" | "demo" | "partial";

export interface SealProps {
  state?: SealState;
  label?: string;
  className?: string;
}

const STATE_STYLES: Record<SealState, { ring: string; text: string; defaultLabel: string }> = {
  verified: {
    ring: "border-tierra text-tierra-deep",
    text: "text-tierra-deep",
    defaultLabel: "Verified",
  },
  demo: {
    ring: "border-piedra text-piedra",
    text: "text-piedra",
    defaultLabel: "Demo",
  },
  partial: {
    ring: "border-cielo text-cielo-deep",
    text: "text-cielo-deep",
    defaultLabel: "Parcial",
  },
};

/**
 * Sello de autenticidad TERRIA — la certificación hecha marca.
 * Uso: certificados, cards de campo, estados de dataset.
 */
export default function Seal({ state = "verified", label, className = "" }: SealProps) {
  const s = STATE_STYLES[state];
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border bg-papel/80 px-2.5 py-1 font-mono text-[9px] font-bold uppercase tracking-[0.18em] ${s.ring} ${className}`}
    >
      <StrataGlyph size={11} className={s.text} />
      <span className={s.text}>{label ?? s.defaultLabel}</span>
    </span>
  );
}
