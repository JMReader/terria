"use client";

import React, { useRef, useState } from "react";
import gsap from "gsap";
import { useGSAP } from "@gsap/react";
import { LandValuation } from "@/types/valuation";

gsap.registerPlugin(useGSAP);

export interface ValuationAuditCardProps {
  valuation: LandValuation;
  className?: string;
}

const AUDIT_LABELS: Record<string, string> = {
  idecor: "IDECOR · Catastro Córdoba",
  overpass: "Overpass · OSM Vial",
  osm: "Overpass · OSM Vial",
  sagyp: "SAGyP · Rindes",
};

export default function ValuationAuditCard({
  valuation,
  className = "",
}: ValuationAuditCardProps) {
  const [copied, setCopied] = useState(false);
  const cardRef = useRef<HTMLDivElement>(null);

  useGSAP(
    () => {
      gsap.fromTo(
        cardRef.current,
        { autoAlpha: 0, y: 12 },
        { autoAlpha: 1, y: 0, duration: 0.4, ease: "power3.out" }
      );
    },
    { scope: cardRef }
  );

  const handleCopy = () => {
    navigator.clipboard.writeText(valuation.contentHash);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const shortHash = valuation.contentHash
    ? `${valuation.contentHash.slice(0, 12)}…${valuation.contentHash.slice(-8)}`
    : "—";
  const auditEntries = Object.entries(valuation.auditUrls ?? {});

  return (
    <div
      ref={cardRef}
      className={`group relative flex flex-col rounded-2xl border border-piedra-soft bg-papel p-4.5 shadow-xs transition-colors duration-200 hover:border-tierra-deep select-none ${className}`}
    >
      <div className="flex items-center justify-between border-b border-piedra-soft pb-2.5">
        <span className="text-[10px] font-mono font-bold tracking-wider text-piedra uppercase">
          Trazabilidad del Cálculo
        </span>
        <span className="rounded-full bg-tierra/15 border border-tierra/50 px-2 py-0.5 text-[9px] font-mono font-bold text-tierra-deep tracking-wider uppercase">
          SHA-256
        </span>
      </div>

      <div className="py-3 space-y-3">
        {/* Content hash — listo para anclaje Solana memo */}
        <div className="rounded-xl bg-nube border border-piedra-soft p-2.5 transition-colors group-hover:bg-tierra/10">
          <div className="flex items-center justify-between">
            <span className="text-[9px] font-mono font-bold text-piedra uppercase tracking-wider">
              Content Hash (inputs congelados)
            </span>
            <button
              onClick={handleCopy}
              className="text-[9px] font-mono font-bold text-bosque/60 hover:text-bosque transition-colors uppercase cursor-pointer"
            >
              {copied ? "Copiado" : "Copiar"}
            </button>
          </div>
          <div className="mt-1 font-mono text-xs font-bold text-bosque break-all">
            {shortHash}
          </div>
        </div>

        {/* Audit URLs de las fuentes del motor */}
        {auditEntries.length > 0 && (
          <div className="space-y-1.5">
            {auditEntries.map(([key, url]) => (
              <a
                key={key}
                href={url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center justify-between rounded-lg border border-piedra-soft bg-nube px-2.5 py-1.5 text-[10px] font-mono text-bosque/70 transition-colors hover:border-bosque hover:text-bosque"
              >
                <span className="font-bold uppercase tracking-wider">
                  {AUDIT_LABELS[key] ?? key}
                </span>
                <span className="text-piedra">↗</span>
              </a>
            ))}
          </div>
        )}
      </div>

      <div className="border-t border-piedra-soft pt-2.5">
        <p className="text-[10px] font-mono leading-relaxed text-bosque/60">
          Hash determinista de los inputs congelados de la valuación — formato
          compatible con anclaje en el Memo Program de Solana (cert.inputs).
        </p>
      </div>
    </div>
  );
}
