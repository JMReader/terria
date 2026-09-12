"use client";

import React from "react";
import { ModelMetrics } from "@/types/whatIf";

export interface TwinLotsMetricCardProps {
  metrics: ModelMetrics;
  targetYear: number;
  className?: string;
}

export default function TwinLotsMetricCard({
  metrics,
  targetYear,
  className = "",
}: TwinLotsMetricCardProps) {
  const dimensions = [
    { label: "Suelo (F_soil)", desc: "Textura & Arcilla SoilGrids", status: "Activo" },
    { label: "Topografía (F_topo)", desc: "Pendiente Copernicus DEM", status: "Activo" },
    { label: "Humedad (F_init)", desc: "Radar Sentinel-1 SAR", status: "Activo" },
    { label: "Balance Hídrico", desc: "AgERA5 Lluvia vs ETo", status: "Activo" },
    { label: "Historial NDVI", desc: "Serie temporal Sentinel-2", status: "Activo" },
  ];

  return (
    <div
      className={`rounded-2xl border border-piedra-soft bg-papel p-4 shadow-xs transition-colors duration-200 hover:border-bosque/40 ${className}`}
    >
      <div className="flex items-center justify-between border-b border-piedra-soft pb-2.5">
        <span className="text-[10px] font-mono font-bold tracking-wider text-piedra uppercase">
          Algoritmo Lotes Gemelos (Vector 5D)
        </span>
        <span className="text-[10px] font-mono text-musgo font-bold">
          Similitud {(metrics.avgSimilarityScore * 100).toFixed(1)}%
        </span>
      </div>

      {/* Grid de Métricas de Similitud Espacial */}
      <div className="grid grid-cols-3 gap-2 mt-3 text-xs font-mono">
        <div className="rounded-xl bg-nube p-2.5 border border-piedra-soft text-center">
          <span className="text-[9px] text-piedra uppercase block">Candidatos (50 km)</span>
          <span className="font-bold text-bosque text-sm">{metrics.candidateLotsScanned}</span>
        </div>

        <div className="rounded-xl bg-nube p-2.5 border border-piedra-soft text-center">
          <span className="text-[9px] text-piedra uppercase block">Gemelos Calibrados</span>
          <span className="font-bold text-musgo text-sm">{metrics.strictTwinLotsMatched}</span>
        </div>

        <div className="rounded-xl bg-nube p-2.5 border border-piedra-soft text-center">
          <span className="text-[9px] text-piedra uppercase block">NDVI Zonal ({targetYear})</span>
          <span className="font-bold text-bosque text-sm">{metrics.zoneMeanNdvi.toFixed(3)}</span>
        </div>
      </div>

      {/* Vector 5D Chips */}
      <div className="mt-3 pt-2.5 border-t border-piedra-soft">
        <span className="text-[9px] font-mono font-bold tracking-wider text-piedra uppercase block mb-2">
          Dimensiones Biofísicas Evaluadas:
        </span>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-1.5 text-[10px] font-mono">
          {dimensions.map((dim, i) => (
            <div
              key={i}
              className="rounded-lg bg-nube/80 px-2 py-1 border border-piedra-soft/80 flex items-center justify-between"
            >
              <span className="font-medium text-bosque truncate">{dim.label}</span>
              <span className="text-[8px] text-musgo font-bold shrink-0">OK</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
