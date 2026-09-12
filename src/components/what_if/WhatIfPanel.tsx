"use client";

import React, { useState } from "react";
import { FieldItem } from "@/data/fieldsData";
import { useFieldWhatIf } from "@/hooks/useFieldWhatIf";
import { CROP_OPTIONS } from "@/types/whatIf";
import WhatIfHeroCard from "./WhatIfHeroCard";
import TwinLotsMetricCard from "./TwinLotsMetricCard";
import MultiCropRankingTable from "./MultiCropRankingTable";
import WhatIfAuditCard from "./WhatIfAuditCard";
import WhatIfModalView from "./WhatIfModalView";
import { Maximize2, AlertCircle, CheckCircle2 } from "lucide-react";

export interface WhatIfPanelProps {
  field: FieldItem;
  className?: string;
}

export default function WhatIfPanel({
  field,
  className = "",
}: WhatIfPanelProps) {
  const [isModalOpen, setIsModalOpen] = useState(false);

  const {
    simulation,
    source,
    targetYear,
    setTargetYear,
    realCrop,
    setRealCrop,
    realMarginUsdHa,
    setRealMarginUsdHa,
    selectedCropId,
    setSelectedCropId,
    availability,
    isFieldPreloaded,
  } = useFieldWhatIf(field);

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Botón de Expansión a Pantalla Completa / Vista Amplia */}
      <div className="flex items-center justify-between gap-2">
        <span className="text-[10px] font-mono font-bold tracking-wider text-piedra uppercase">
          Simulador Retrospectivo Multicultivo
        </span>

        <button
          onClick={() => setIsModalOpen(true)}
          className="flex items-center gap-1.5 rounded-xl border border-piedra-soft bg-papel hover:border-bosque hover:bg-nube px-3 py-1.5 text-xs font-mono font-bold text-bosque transition-all cursor-pointer shadow-xs"
        >
          <Maximize2 className="h-3.5 w-3.5 text-musgo" />
          <span>Vista Amplia</span>
        </button>
      </div>

      {/* FORMULARIO DE PARÁMETROS: Año libre, Selector de Cultivo y Margen numérico */}
      <div className="rounded-2xl border border-piedra-soft bg-papel p-4 shadow-xs space-y-3.5">
        {/* 1. Año Numérico Libre */}
        <div>
          <div className="flex items-center justify-between mb-1">
            <label className="text-[10px] font-mono font-bold tracking-wider text-piedra uppercase">
              Campaña (Año Numérico Libre)
            </label>
            <span className="text-[9px] font-mono text-piedra">2015 — 2030</span>
          </div>

          <div className="flex items-center gap-2">
            <input
              type="number"
              min={2015}
              max={2030}
              value={targetYear}
              onChange={(e) => setTargetYear(parseInt(e.target.value) || 2023)}
              className="flex-1 rounded-xl border border-piedra-soft bg-nube px-3 py-1.5 text-xs font-mono font-bold text-bosque focus:border-bosque focus:outline-none transition-colors"
            />
            {/* Quick shortcuts */}
            <button
              onClick={() => setTargetYear(2023)}
              className={`rounded-lg border px-2 py-1 text-[10px] font-mono transition-colors ${
                targetYear === 2023
                  ? "bg-bosque text-nube border-bosque font-bold"
                  : "bg-nube border-piedra-soft text-piedra hover:text-bosque"
              }`}
            >
              '23 Sequía
            </button>
            <button
              onClick={() => setTargetYear(2024)}
              className={`rounded-lg border px-2 py-1 text-[10px] font-mono transition-colors ${
                targetYear === 2024
                  ? "bg-bosque text-nube border-bosque font-bold"
                  : "bg-nube border-piedra-soft text-piedra hover:text-bosque"
              }`}
            >
              '24
            </button>
          </div>

          {/* Feedback de disponibilidad de datos */}
          <div className="mt-1.5 flex items-start gap-1.5 text-[10px] font-mono">
            {availability.hasSatellite ? (
              <CheckCircle2 className="h-3 w-3 text-musgo shrink-0 mt-0.5" />
            ) : (
              <AlertCircle className="h-3 w-3 text-tierra-deep shrink-0 mt-0.5" />
            )}
            <span className="text-bosque/80 leading-tight">{availability.label}</span>
          </div>
        </div>

        {/* 2. Selector de Cultivo Cosechado en la Realidad */}
        <div className="pt-2 border-t border-piedra-soft/70">
          <div className="flex items-center justify-between mb-1">
            <label className="text-[10px] font-mono font-bold tracking-wider text-piedra uppercase">
              Cultivo Real Cosechado
            </label>
            {isFieldPreloaded && (
              <span className="text-[9px] font-mono text-musgo font-bold">
                Pre-cargado del campo
              </span>
            )}
          </div>

          <select
            value={realCrop}
            onChange={(e) => setRealCrop(e.target.value)}
            className="w-full rounded-xl border border-piedra-soft bg-nube px-2.5 py-1.5 text-xs font-mono font-bold text-bosque focus:border-bosque focus:outline-none transition-colors cursor-pointer"
          >
            {CROP_OPTIONS.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name} ({c.season} • {c.category})
              </option>
            ))}
          </select>
        </div>

        {/* 3. Margen Obtenido en USD/ha */}
        <div className="pt-2 border-t border-piedra-soft/70">
          <div className="flex items-center justify-between mb-1">
            <label className="text-[10px] font-mono font-bold tracking-wider text-piedra uppercase">
              Margen Real Obtenido
            </label>
            <span className="text-[9px] font-mono text-piedra">USD por hectárea</span>
          </div>

          <div className="relative">
            <span className="absolute left-3 top-1.5 text-xs font-mono text-piedra font-bold">
              $
            </span>
            <input
              type="number"
              step={10}
              min={0}
              max={5000}
              value={realMarginUsdHa}
              onChange={(e) => setRealMarginUsdHa(parseFloat(e.target.value) || 0)}
              className="w-full rounded-xl border border-piedra-soft bg-nube pl-7 pr-16 py-1.5 text-xs font-mono font-bold text-bosque focus:border-bosque focus:outline-none transition-colors"
            />
            <span className="absolute right-3 top-1.5 text-[10px] font-mono text-piedra">
              USD/ha
            </span>
          </div>
        </div>
      </div>

      {/* Hero Principal con Podio de Ganadores */}
      <WhatIfHeroCard simulation={simulation} source={source} />

      {/* Métricas de Lotes Gemelos (Vector 5D) */}
      <TwinLotsMetricCard
        metrics={simulation.modelMetrics}
        targetYear={targetYear}
      />

      {/* Leaderboard Multicultivo de 10 Granos */}
      <MultiCropRankingTable
        ranking={simulation.ranking}
        surfaceHa={simulation.surfaceHa}
        realCrop={simulation.realCrop}
        selectedCropId={selectedCropId}
        onSelectCrop={setSelectedCropId}
      />

      {/* Tarjeta de Sello Criptográfico y Auditoría Pública */}
      <WhatIfAuditCard
        contentHash={simulation.contentHash}
        auditUrls={simulation.auditUrls}
      />

      {/* Modal Expandido de Pantalla Completa */}
      <WhatIfModalView
        field={field}
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
      />
    </div>
  );
}
