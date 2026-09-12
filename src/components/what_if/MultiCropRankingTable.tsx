"use client";

import React, { useState } from "react";
import { CropEvaluation } from "@/types/whatIf";

export interface MultiCropRankingTableProps {
  ranking: CropEvaluation[];
  surfaceHa: number;
  realCrop: string;
  selectedCropId: string | null;
  onSelectCrop: (cropId: string) => void;
  className?: string;
}

const fmtUsd = (n: number) =>
  n.toLocaleString("es-AR", { maximumFractionDigits: 0 });

export default function MultiCropRankingTable({
  ranking,
  surfaceHa,
  realCrop,
  selectedCropId,
  onSelectCrop,
  className = "",
}: MultiCropRankingTableProps) {
  const [sortBy, setSortBy] = useState<"margin" | "yield">("margin");

  const sortedList = [...ranking].sort((a, b) => {
    if (sortBy === "margin") {
      return b.financials.netMarginUsdHa - a.financials.netMarginUsdHa;
    }
    return b.projectedYieldTnHa - a.projectedYieldTnHa;
  });

  return (
    <div
      className={`rounded-2xl border border-piedra-soft bg-papel p-4 shadow-xs transition-colors duration-200 hover:border-bosque/40 ${className}`}
    >
      {/* Header y Sort Toggles */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-piedra-soft pb-3">
        <div>
          <span className="text-[10px] font-mono font-bold tracking-wider text-piedra uppercase block">
            Catálogo Oficial SAGyP (10 Granos)
          </span>
          <span className="text-xs font-mono text-bosque/70">
            Comparativa contra la cosecha real de {realCrop} ({surfaceHa} ha)
          </span>
        </div>

        {/* Sort Switcher */}
        <div className="flex items-center gap-1 rounded-xl bg-nube p-1 border border-piedra-soft text-[10px] font-mono font-bold self-start sm:self-auto">
          <button
            onClick={() => setSortBy("margin")}
            className={`rounded-lg px-2.5 py-1 transition-all cursor-pointer ${
              sortBy === "margin"
                ? "bg-papel text-tierra-deep shadow-xs border border-piedra-soft"
                : "text-piedra hover:text-bosque"
            }`}
          >
            Por Margen (USD/ha)
          </button>
          <button
            onClick={() => setSortBy("yield")}
            className={`rounded-lg px-2.5 py-1 transition-all cursor-pointer ${
              sortBy === "yield"
                ? "bg-papel text-musgo shadow-xs border border-piedra-soft"
                : "text-piedra hover:text-bosque"
            }`}
          >
            Por Rinde (tn/ha)
          </button>
        </div>
      </div>

      {/* Lista / Tabla de Cultivos */}
      <div className="mt-3 divide-y divide-piedra-soft/60">
        {sortedList.map((item) => {
          const isSelected = selectedCropId === item.cropId;
          const isPositive = item.financials.diffNetMarginUsdHa >= 0;
          const rankNumber = sortBy === "margin" ? item.rankMargin : item.rankYield;

          return (
            <div
              key={item.cropId}
              onClick={() => onSelectCrop(item.cropId)}
              className={`py-2.5 px-2 rounded-xl transition-all cursor-pointer flex items-center justify-between gap-2 ${
                isSelected
                  ? "bg-nube border border-bosque/30"
                  : "hover:bg-nube/60"
              }`}
            >
              {/* Posición y Nombre del Cultivo */}
              <div className="flex items-center gap-2.5 min-w-0">
                <span
                  className={`h-6 w-6 rounded-lg flex items-center justify-center text-[10px] font-mono font-bold shrink-0 ${
                    rankNumber === 1
                      ? "bg-tierra/20 text-tierra-deep border border-tierra/40"
                      : rankNumber <= 3
                      ? "bg-musgo/15 text-musgo border border-musgo/30"
                      : "bg-nube text-piedra border border-piedra-soft"
                  }`}
                >
                  #{rankNumber}
                </span>

                <div className="min-w-0">
                  <div className="flex items-center gap-1.5">
                    <span className="font-bold text-xs text-bosque truncate font-mono">
                      {item.cropName}
                    </span>
                    <span className="rounded bg-nube px-1.5 py-0.2 text-[8px] font-mono text-piedra border border-piedra-soft shrink-0">
                      {item.season}
                    </span>
                  </div>
                  <span className="text-[10px] font-mono text-piedra block">
                    {item.projectedYieldTnHa} tn/ha{" "}
                    <span className={item.deltaYieldPct >= 0 ? "text-musgo font-bold" : "text-tierra-deep"}>
                      ({item.deltaYieldPct >= 0 ? `+${item.deltaYieldPct}%` : `${item.deltaYieldPct}%`})
                    </span>
                  </span>
                </div>
              </div>

              {/* Margen y Delta vs Real */}
              <div className="text-right shrink-0">
                <span className="font-bold text-xs text-bosque font-mono block">
                  ${fmtUsd(item.financials.netMarginUsdHa)}{" "}
                  <span className="text-[9px] font-normal text-piedra">USD/ha</span>
                </span>
                <span
                  className={`text-[10px] font-mono font-bold block ${
                    isPositive ? "text-musgo" : "text-tierra-deep"
                  }`}
                >
                  {isPositive ? `+${fmtUsd(item.financials.diffNetMarginUsdHa)}` : fmtUsd(item.financials.diffNetMarginUsdHa)} USD/ha
                </span>
              </div>
            </div>
          );
        })}
      </div>

      <div className="mt-3 pt-2.5 border-t border-piedra-soft flex items-center justify-between text-[10px] font-mono text-piedra">
        <span>Precios: MATba ROFEX</span>
        <span>Costos: BCR GEA</span>
      </div>
    </div>
  );
}
