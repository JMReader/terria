"use client";

import React, { useState } from "react";

export interface WhatIfAuditCardProps {
  contentHash: string;
  auditUrls?: Record<string, string>;
  className?: string;
}

export default function WhatIfAuditCard({
  contentHash,
  auditUrls = {},
  className = "",
}: WhatIfAuditCardProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard?.writeText(contentHash);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const defaultUrls = {
    "Copernicus Browser": "https://browser.dataspace.copernicus.eu/",
    "Open-Meteo ERA5": "https://open-meteo.com/en/docs/historical-weather-api",
    "SoilGrids 250m": "https://rest.isric.org/soilgrids/v2.0/docs",
    "SAGyP Estimaciones": "https://datos.magyp.gob.ar/dataset/estimaciones-agricolas",
    ...auditUrls,
  };

  return (
    <div
      className={`rounded-2xl border border-piedra-soft bg-papel p-4 shadow-xs transition-colors duration-200 hover:border-tierra/60 ${className}`}
    >
      <div className="flex items-center justify-between border-b border-piedra-soft pb-2.5">
        <span className="text-[10px] font-mono font-bold tracking-wider text-piedra uppercase">
          Auditoría Abierta & Sello Criptográfico
        </span>
        <span className="text-[10px] font-mono text-musgo font-bold">SHA-256 Verificado</span>
      </div>

      {/* Sello SHA-256 */}
      <div className="mt-3 rounded-xl bg-nube p-3 border border-piedra-soft font-mono">
        <div className="flex items-center justify-between gap-2">
          <span className="text-[9px] text-piedra uppercase">Hash Inmutable de Simulación</span>
          <button
            onClick={handleCopy}
            className="text-[10px] text-bosque hover:text-musgo font-bold transition-colors cursor-pointer"
          >
            {copied ? "Copiado ✓" : "Copiar"}
          </button>
        </div>
        <p className="mt-1 text-[11px] text-bosque font-mono break-all font-bold">
          {contentHash}
        </p>
        <span className="text-[9px] text-piedra block mt-1">
          Anclado según RFC 8785 (JCS) • Compatible con Memo Program de Solana
        </span>
      </div>

      {/* Deep links de auditoría pública */}
      <div className="mt-3 pt-2.5 border-t border-piedra-soft">
        <span className="text-[9px] font-mono font-bold tracking-wider text-piedra uppercase block mb-2">
          Fuentes Satelitales y Datos Abiertos (100% Auditables):
        </span>
        <div className="grid grid-cols-2 gap-2 text-xs font-mono">
          {Object.entries(defaultUrls).map(([label, url]) => (
            <a
              key={label}
              href={url}
              target="_blank"
              rel="noreferrer"
              className="rounded-lg bg-nube/70 hover:bg-nube px-2.5 py-1.5 border border-piedra-soft text-bosque/80 hover:text-bosque hover:border-bosque transition-all flex items-center justify-between text-[11px]"
            >
              <span className="truncate">{label}</span>
              <span className="text-piedra text-[10px]">↗</span>
            </a>
          ))}
        </div>
      </div>
    </div>
  );
}
