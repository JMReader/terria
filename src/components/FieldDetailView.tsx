"use client";

import React, { useState, useRef } from "react";
import gsap from "gsap";
import { useGSAP } from "@gsap/react";
import { FieldItem } from "@/data/fieldsData";
import { DEMO_TIMELAPSE_MANIFEST, DEMO_SOLANA_CERTIFICATION } from "@/data/timelapseMockData";
import { useFieldTimelapse } from "@/hooks/useFieldTimelapse";
import MetricStatBox from "@/components/ui/MetricStatBox";
import NdviMetricCard from "@/components/timelapse/NdviMetricCard";
import WeatherDailyCard from "@/components/timelapse/WeatherDailyCard";
import NdviSparklineChart from "@/components/timelapse/NdviSparklineChart";
import SolanaAuditCard from "@/components/certification/SolanaAuditCard";

gsap.registerPlugin(useGSAP);

export interface FieldDetailViewProps {
  field: FieldItem;
  onBack: () => void;
  onSelectCropZone?: (zone: string) => void;
  onToggleIsolate3D?: () => void;
  isIsolated3D?: boolean;
  sharedTimelapse?: ReturnType<typeof useFieldTimelapse>;
}

export default function FieldDetailView({
  field,
  onBack,
  onToggleIsolate3D,
  isIsolated3D = false,
  sharedTimelapse,
}: FieldDetailViewProps) {
  const [activeTab, setActiveTab] = useState<"summary" | "timelapse" | "audit">("summary");
  const containerRef = useRef<HTMLDivElement>(null);
  const tabContentRef = useRef<HTMLDivElement>(null);

  // Hook for full deterministic timelapse data (use shared if provided, otherwise internal)
  const internalTimelapse = useFieldTimelapse({ manifest: DEMO_TIMELAPSE_MANIFEST });
  const timelapse = sharedTimelapse || internalTimelapse;

  // GSAP Entrance
  useGSAP(
    () => {
      const tl = gsap.timeline({ defaults: { ease: "power3.out" } });

      tl.fromTo(
        containerRef.current,
        { autoAlpha: 0, scale: 0.98 },
        { autoAlpha: 1, scale: 1, duration: 0.35 }
      );
    },
    { dependencies: [field.id], scope: containerRef }
  );

  // Tab switch animation
  useGSAP(
    () => {
      if (tabContentRef.current) {
        gsap.fromTo(
          tabContentRef.current.children,
          { autoAlpha: 0, y: 12 },
          { autoAlpha: 1, y: 0, stagger: 0.05, duration: 0.3, ease: "power2.out" }
        );
      }
    },
    { dependencies: [activeTab], scope: containerRef }
  );

  const handleBackClick = () => {
    if (!containerRef.current) {
      onBack();
      return;
    }
    gsap.to(containerRef.current, {
      autoAlpha: 0,
      scale: 0.98,
      duration: 0.2,
      ease: "power2.in",
      onComplete: onBack,
    });
  };

  return (
    <div
      ref={containerRef}
      className="flex flex-col h-full rounded-3xl border border-gray-200 bg-white shadow-sm overflow-hidden select-none"
    >
      {/* Top Header: No icons, pure typography and minimalist badges */}
      <div className="p-4 sm:p-5 border-b border-gray-100 bg-white shrink-0 space-y-3">
        <div className="flex items-center justify-between gap-2">
          <button
            onClick={handleBackClick}
            className="rounded-xl border border-gray-200 bg-white hover:border-gray-900 px-3 py-1.5 text-xs font-mono font-bold text-gray-700 transition-colors cursor-pointer"
          >
            ‹ Catálogo
          </button>

          <div className="flex items-center gap-2">
            {onToggleIsolate3D && (
              <button
                onClick={onToggleIsolate3D}
                className={`rounded-xl px-3 py-1.5 text-xs font-mono font-bold transition-all cursor-pointer border ${
                  isIsolated3D
                    ? "bg-gray-900 text-white border-gray-900"
                    : "bg-white text-gray-700 border-gray-200 hover:border-gray-900"
                }`}
              >
                {isIsolated3D ? "Ver Mapa" : "Maqueta 3D"}
              </button>
            )}

            <span className="rounded-lg bg-gray-100 border border-gray-200 px-2 py-1 text-[10px] font-mono font-bold text-gray-600">
              {field.code || "CAMPO"}
            </span>

            <span className="rounded-lg bg-emerald-50 border border-emerald-200 px-2 py-1 text-[10px] font-mono font-bold text-emerald-800 uppercase">
              Verificado
            </span>
          </div>
        </div>

        <div>
          <h1 className="text-xl font-black text-gray-900 tracking-tight">
            {field.name}
          </h1>
          <p className="text-xs font-mono text-gray-400 mt-0.5">
            {field.locality || "Argentina"}{field.province ? `, ${field.province}` : ""} {field.coordinates ? `• ${field.coordinates}` : ""}
          </p>
        </div>

        {/* Minimalist Segmented Tab Switcher */}
        <div className="grid grid-cols-3 gap-1 rounded-2xl bg-gray-100 p-1 border border-gray-200 text-[11px] font-mono font-bold">
          <button
            onClick={() => setActiveTab("summary")}
            className={`rounded-xl py-1.5 transition-all cursor-pointer uppercase ${
              activeTab === "summary"
                ? "bg-white text-gray-900 shadow-xs border border-gray-200"
                : "text-gray-500 hover:text-gray-900"
            }`}
          >
            Resumen
          </button>
          <button
            onClick={() => setActiveTab("timelapse")}
            className={`rounded-xl py-1.5 transition-all cursor-pointer uppercase ${
              activeTab === "timelapse"
                ? "bg-white text-emerald-800 shadow-xs border border-gray-200"
                : "text-gray-500 hover:text-gray-900"
            }`}
          >
            Timelapse
          </button>
          <button
            onClick={() => setActiveTab("audit")}
            className={`rounded-xl py-1.5 transition-all cursor-pointer uppercase ${
              activeTab === "audit"
                ? "bg-white text-blue-800 shadow-xs border border-gray-200"
                : "text-gray-500 hover:text-gray-900"
            }`}
          >
            Solana
          </button>
        </div>
      </div>

      {/* Scrollable Body Content */}
      <div className="flex-1 min-h-0 overflow-y-auto p-4 sm:p-5 custom-scrollbar">
        <div ref={tabContentRef} className="space-y-4">
          {/* TAB 1: RESUMEN AGRONÓMICO */}
          {activeTab === "summary" && (
            <>
              {/* 4 Scorecard boxes */}
              <div className="grid grid-cols-2 gap-2.5">
                <MetricStatBox
                  label="Superficie"
                  value={field.hectares}
                  unit="ha"
                  subtext={field.primaryCrop || field.crop || "Cultivo activo"}
                  highlight="neutral"
                />
                <MetricStatBox
                  label="Aptitud"
                  value={field.suitabilityScore != null ? `${field.suitabilityScore}%` : (field.aptitude || "Alta")}
                  subtext="Clase I-II Agrícola"
                  progressPercent={field.suitabilityScore ?? 90}
                  highlight="emerald"
                />
                <MetricStatBox
                  label="NDVI Activo"
                  value={field.ndvi.toFixed(2)}
                  unit="/ 1.00"
                  progressPercent={field.ndvi * 100}
                  highlight="emerald"
                />
                <MetricStatBox
                  label="Alquiler"
                  value={field.rentQqSoja ?? "-"}
                  unit="qq/ha"
                  subtext={field.rentUsdHa != null ? `$${field.rentUsdHa} USD/ha` : "A consultar"}
                  highlight="blue"
                />
              </div>

              {/* Suelo y Régimen Hídrico */}
              <div className="group rounded-2xl border border-gray-200 bg-white p-4 shadow-xs transition-colors duration-200 hover:border-gray-900">
                <div className="flex items-center justify-between border-b border-gray-100 pb-2">
                  <span className="text-[10px] font-mono font-bold tracking-wider text-gray-400 uppercase">
                    Suelo & Napa (INTA)
                  </span>
                  <span className="text-[10px] font-mono text-gray-500">
                    {field.soilSeries || field.soilType || "Suelo agrícola"}
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-2 mt-3 text-xs font-mono">
                  <div className="rounded-xl bg-gray-50 p-2.5 border border-gray-100">
                    <span className="text-[9px] text-gray-400 uppercase block">Napa Freática</span>
                    <span className="font-bold text-gray-800">{field.waterTable || "Cota normal"}</span>
                  </div>
                  <div className="rounded-xl bg-gray-50 p-2.5 border border-gray-100">
                    <span className="text-[9px] text-gray-400 uppercase block">Régimen Hídrico</span>
                    <span className="font-bold text-gray-800">
                      {field.irrigation ? "Riego Pivote" : "Secano"}
                    </span>
                  </div>
                </div>
              </div>

              {/* Campañas Históricas */}
              <div className="group rounded-2xl border border-gray-200 bg-white p-4 shadow-xs transition-colors duration-200 hover:border-gray-900">
                <span className="text-[10px] font-mono font-bold tracking-wider text-gray-400 uppercase block mb-3">
                  Historial de Campañas
                </span>
                <div className="space-y-2 text-xs font-mono">
                  <div className="flex items-center justify-between border-b border-gray-100 pb-2">
                    <span className="text-gray-700">2024/25 • Maíz Tardío</span>
                    <span className="font-bold text-emerald-700">98 qq/ha</span>
                  </div>
                  <div className="flex items-center justify-between border-b border-gray-100 pb-2">
                    <span className="text-gray-700">2023/24 • Soja 1ra</span>
                    <span className="font-bold text-blue-700">41 qq/ha</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-gray-700">2022/23 • Trigo / Soja</span>
                    <span className="font-bold text-amber-700">44 qq/ha</span>
                  </div>
                </div>
              </div>
            </>
          )}

          {/* TAB 2: MONITOR SATELITAL & TIMELAPSE */}
          {activeTab === "timelapse" && (
            <>
              {/* Daily Weather & NDVI cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <NdviMetricCard timelineState={timelapse.timelineState} />
                <WeatherDailyCard
                  weather={timelapse.timelineState.weather}
                  selectedDate={timelapse.selectedDate}
                />
              </div>

              {/* Sparkline curve across the whole season */}
              <NdviSparklineChart
                frames={timelapse.manifest?.frames || []}
                selectedDate={timelapse.selectedDate}
                activeFrameId={timelapse.timelineState.satellite?.id}
                onSelectDate={(d) => {
                  const idx = timelapse.dates.indexOf(d);
                  if (idx !== -1) timelapse.setDateIndex(idx);
                }}
              />

              {/* Mini stepper for inline date exploration */}
              <div className="rounded-2xl border border-gray-200 bg-white p-3 flex items-center justify-between text-xs font-mono transition-colors hover:border-gray-900">
                <button
                  onClick={timelapse.stepPrev}
                  className="rounded-lg border border-gray-200 px-2.5 py-1 text-gray-700 hover:border-gray-900 transition-colors cursor-pointer"
                >
                  ‹ Día
                </button>
                <div className="text-center">
                  <span className="font-bold text-gray-900 block">
                    {timelapse.selectedDate}
                  </span>
                  <span className="text-[10px] text-gray-400">
                    Paso {timelapse.dateIndex + 1} de {timelapse.dates.length}
                  </span>
                </div>
                <button
                  onClick={timelapse.stepNext}
                  className="rounded-lg border border-gray-200 px-2.5 py-1 text-gray-700 hover:border-gray-900 transition-colors cursor-pointer"
                >
                  Día ›
                </button>
              </div>
            </>
          )}

          {/* TAB 3: AUDITORÍA SOLANA */}
          {activeTab === "audit" && (
            <>
              <SolanaAuditCard certification={DEMO_SOLANA_CERTIFICATION} />

              <div className="group rounded-2xl border border-gray-200 bg-white p-4 shadow-xs transition-colors duration-200 hover:border-emerald-600">
                <span className="text-[10px] font-mono font-bold tracking-wider text-gray-400 uppercase block mb-2">
                  Regla de Integridad Criptográfica
                </span>
                <p className="text-xs font-mono text-gray-600 leading-relaxed">
                  El snapshot canónico mensual (2018-2026) queda sellado bajo SHA-256 e inyectado en el Memo Program de Solana Devnet. La firma demuestra existencia inmutable de la serie agronómica.
                </p>
                <div className="mt-3 flex items-center justify-between text-[10px] font-mono text-gray-400 border-t border-gray-100 pt-2">
                  <span>RFC 8785 (JCS)</span>
                  <span className="text-emerald-700 font-bold">Estado: Confirmado</span>
                </div>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Sticky Bottom Actions: Zero icons, clean typography */}
      <div className="p-4 border-t border-gray-100 bg-white shrink-0 flex items-center gap-2">
        <button className="flex-1 rounded-2xl bg-gray-900 hover:bg-black active:scale-[0.98] text-white px-4 py-3 text-xs font-mono font-bold tracking-wider uppercase transition-all cursor-pointer shadow-xs">
          Solicitar Arrendamiento
        </button>

        <button
          title="Descargar Ficha en PDF"
          className="rounded-2xl border border-gray-200 bg-white hover:border-gray-900 text-gray-700 px-3.5 py-3 text-xs font-mono font-bold uppercase transition-colors cursor-pointer shrink-0"
        >
          PDF
        </button>

        <button
          title="Compartir Lote"
          className="rounded-2xl border border-gray-200 bg-white hover:border-gray-900 text-gray-700 px-3.5 py-3 text-xs font-mono font-bold uppercase transition-colors cursor-pointer shrink-0"
        >
          Link
        </button>
      </div>
    </div>
  );
}
