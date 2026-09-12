"use client";

import React, { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import gsap from "gsap";
import { useGSAP } from "@gsap/react";
import { FieldItem } from "@/data/fieldsData";
import { useFieldWhatIf } from "@/hooks/useFieldWhatIf";
import { CROP_OPTIONS } from "@/types/whatIf";
import WhatIfHeroCard from "./WhatIfHeroCard";
import TwinLotsMetricCard from "./TwinLotsMetricCard";
import MultiCropRankingTable from "./MultiCropRankingTable";
import WhatIfAuditCard from "./WhatIfAuditCard";
import { X, SlidersHorizontal, Sparkles, AlertCircle, CheckCircle2 } from "lucide-react";

gsap.registerPlugin(useGSAP);

export interface WhatIfModalViewProps {
  field: FieldItem;
  isOpen: boolean;
  onClose: () => void;
}

export default function WhatIfModalView({
  field,
  isOpen,
  onClose,
}: WhatIfModalViewProps) {
  const [mounted, setMounted] = useState(false);
  const modalRef = useRef<HTMLDivElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setMounted(true);
  }, []);

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

  // Bloquear scroll del body al abrir el modal
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [isOpen]);

  useGSAP(
    () => {
      if (isOpen && modalRef.current) {
        gsap.fromTo(
          modalRef.current,
          { autoAlpha: 0 },
          { autoAlpha: 1, duration: 0.25, ease: "power2.out" }
        );
        if (contentRef.current) {
          gsap.fromTo(
            contentRef.current,
            { y: 24, scale: 0.98 },
            { y: 0, scale: 1, duration: 0.35, ease: "power3.out" }
          );
        }
      }
    },
    { dependencies: [isOpen] }
  );

  if (!isOpen || !mounted) return null;

  return createPortal(
    <div
      ref={modalRef}
      className="fixed inset-0 z-[9999] flex items-center justify-center bg-bosque-deep/80 backdrop-blur-md p-3 sm:p-6 overflow-y-auto"
    >
      <div
        ref={contentRef}
        className="relative w-full max-w-6xl max-h-[92vh] flex flex-col rounded-3xl border border-piedra-soft bg-papel shadow-2xl overflow-hidden"
      >
        {/* Header Superior con Marca y Cierre */}
        <div className="p-5 sm:p-6 border-b border-piedra-soft bg-papel flex items-center justify-between shrink-0">
          <div>
            <div className="flex items-center gap-2">
              <span className="rounded-lg bg-bosque text-nube px-2 py-0.5 text-[10px] font-mono font-bold uppercase tracking-wider">
                What-If Multicultivo v2.2
              </span>
              <span className="rounded-lg bg-tierra/15 border border-tierra/40 text-tierra-deep px-2 py-0.5 text-[10px] font-mono font-bold uppercase">
                {field.code || "CAMPO OFICIAL"}
              </span>
              {isFieldPreloaded && (
                <span className="rounded-lg bg-musgo/10 border border-musgo/30 text-musgo px-2 py-0.5 text-[10px] font-mono font-bold">
                  Sincronizado Supabase
                </span>
              )}
            </div>

            <h1 className="font-display text-2xl sm:text-3xl font-medium text-bosque tracking-tight mt-1.5">
              {field.name}
            </h1>
            <p className="text-xs font-mono text-piedra mt-0.5">
              {field.locality}, {field.province} • {field.hectares} ha • {field.coordinates}
            </p>
          </div>

          <button
            onClick={onClose}
            className="rounded-2xl border border-piedra-soft bg-nube hover:bg-papel hover:border-bosque p-2.5 text-bosque transition-colors cursor-pointer"
            title="Cerrar vista expandida"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Cuerpo Scrollable con Máximo Espaciado */}
        <div className="flex-1 overflow-y-auto p-5 sm:p-8 space-y-6 custom-scrollbar">
          {/* BARRA DE CONTROLES: Entrada libre de Año, Selector de Cultivo y Margen */}
          <div className="rounded-3xl border border-piedra-soft bg-nube/60 p-5 sm:p-6 space-y-4">
            <div className="flex items-center gap-2 border-b border-piedra-soft pb-2.5">
              <SlidersHorizontal className="h-4 w-4 text-musgo" />
              <span className="text-xs font-mono font-bold tracking-wider text-bosque uppercase">
                Parámetros de la Simulación Contrafáctica
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* 1. Año Numérico Libre */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <label className="text-[11px] font-mono font-bold text-bosque uppercase">
                    Campaña (Año Libre)
                  </label>
                  <span className="text-[10px] font-mono text-piedra">Rango: 2015 - 2030</span>
                </div>

                <div className="relative">
                  <input
                    type="number"
                    min={2015}
                    max={2030}
                    value={targetYear}
                    onChange={(e) => setTargetYear(parseInt(e.target.value) || 2023)}
                    className="w-full rounded-xl border border-piedra-soft bg-papel px-3.5 py-2.5 text-sm font-mono font-bold text-bosque focus:border-bosque focus:outline-none transition-colors"
                  />
                  <div className="absolute right-2.5 top-2.5 flex items-center gap-1">
                    <button
                      onClick={() => setTargetYear((y) => Math.max(2015, y - 1))}
                      className="px-1.5 py-0.5 text-xs font-mono bg-nube border border-piedra-soft rounded hover:border-bosque"
                    >
                      -
                    </button>
                    <button
                      onClick={() => setTargetYear((y) => Math.min(2030, y + 1))}
                      className="px-1.5 py-0.5 text-xs font-mono bg-nube border border-piedra-soft rounded hover:border-bosque"
                    >
                      +
                    </button>
                  </div>
                </div>

                {/* Badge de Disponibilidad de Datos Satelitales */}
                <div className="flex items-start gap-1.5 mt-2">
                  {availability.hasSatellite ? (
                    <CheckCircle2 className="h-3.5 w-3.5 text-musgo shrink-0 mt-0.5" />
                  ) : (
                    <AlertCircle className="h-3.5 w-3.5 text-tierra-deep shrink-0 mt-0.5" />
                  )}
                  <div className="text-[10px] font-mono leading-tight">
                    <span className="font-bold text-bosque block">{availability.label}</span>
                    <span className="text-piedra block mt-0.5">{availability.details}</span>
                  </div>
                </div>

                {/* Accesos Rápidos a Campañas Clave */}
                <div className="flex flex-wrap gap-1 mt-2">
                  {[
                    { year: 2023, label: "2022/23 Sequía" },
                    { year: 2024, label: "2023/24" },
                    { year: 2025, label: "2024/25" },
                    { year: 2022, label: "2021/22" },
                  ].map((p) => (
                    <button
                      key={p.year}
                      onClick={() => setTargetYear(p.year)}
                      className={`text-[10px] font-mono px-2 py-0.5 rounded-lg border transition-all cursor-pointer ${
                        targetYear === p.year
                          ? "bg-bosque text-nube border-bosque font-bold"
                          : "bg-papel text-piedra border-piedra-soft hover:text-bosque hover:border-bosque"
                      }`}
                    >
                      {p.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* 2. Cultivo Cosechado en la Realidad (Selector de Lista) */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <label className="text-[11px] font-mono font-bold text-bosque uppercase">
                    Cultivo Real Cosechado
                  </label>
                  {field.primaryCrop && (
                    <span className="text-[10px] font-mono text-musgo font-bold truncate max-w-[150px]">
                      Detectado: {field.primaryCrop}
                    </span>
                  )}
                </div>

                <select
                  value={realCrop}
                  onChange={(e) => setRealCrop(e.target.value)}
                  className="w-full rounded-xl border border-piedra-soft bg-papel px-3 py-2.5 text-sm font-mono font-bold text-bosque focus:border-bosque focus:outline-none transition-colors cursor-pointer"
                >
                  {CROP_OPTIONS.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name} ({c.season} • {c.category})
                    </option>
                  ))}
                </select>

                <p className="text-[10px] font-mono text-piedra mt-1 leading-tight">
                  Este grano sirve como línea base contrafáctica para calcular si convino rotar o sembrar otro cultivo en esa campaña.
                </p>
              </div>

              {/* 3. Margen Neto Real Obtenido (USD/ha) */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <label className="text-[11px] font-mono font-bold text-bosque uppercase">
                    Margen Real Obtenido
                  </label>
                  <span className="text-[10px] font-mono text-piedra">USD por hectárea</span>
                </div>

                <div className="relative">
                  <span className="absolute left-3.5 top-2.5 text-sm font-mono text-piedra font-bold">
                    $
                  </span>
                  <input
                    type="number"
                    step={10}
                    min={0}
                    max={5000}
                    value={realMarginUsdHa}
                    onChange={(e) => setRealMarginUsdHa(parseFloat(e.target.value) || 0)}
                    className="w-full rounded-xl border border-piedra-soft bg-papel pl-8 pr-16 py-2.5 text-sm font-mono font-bold text-bosque focus:border-bosque focus:outline-none transition-colors"
                  />
                  <span className="absolute right-3.5 top-2.5 text-xs font-mono text-piedra">
                    USD/ha
                  </span>
                </div>

                <p className="text-[10px] font-mono text-piedra mt-1 leading-tight">
                  {field.rentUsdHa
                    ? `Valor de referencia sugerido según alquiler registrado en el campo: $${field.rentUsdHa} USD/ha.`
                    : "Referencia agronómica promedio del departamento: $350 USD/ha."}
                </p>
              </div>
            </div>
          </div>

          {/* HERO PRINCIPAL: Podio y Veredicto Contrafáctico */}
          <WhatIfHeroCard simulation={simulation} source={source} />

          {/* GRID INFERIOR: Tabla de 10 Granos + Desglose Vectorial 5D y Auditoría */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* TABLA DE 10 GRANOS SAGYP (7 / 12 cols) */}
            <div className="lg:col-span-7">
              <MultiCropRankingTable
                ranking={simulation.ranking}
                surfaceHa={simulation.surfaceHa}
                realCrop={simulation.realCrop}
                selectedCropId={selectedCropId}
                onSelectCrop={setSelectedCropId}
              />
            </div>

            {/* VECTOR 5D + AUDITORÍA (5 / 12 cols) */}
            <div className="lg:col-span-5 space-y-4">
              <TwinLotsMetricCard
                metrics={simulation.modelMetrics}
                targetYear={targetYear}
              />

              <WhatIfAuditCard
                contentHash={simulation.contentHash}
                auditUrls={simulation.auditUrls}
              />
            </div>
          </div>
        </div>
      </div>
    </div>,
    document.body
  );
}
