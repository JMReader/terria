"use client";

import React, { useState, useMemo } from "react";
import { FieldItem } from "@/data/fieldsData";
import { TimelineState } from "@/types/terria";
import { getFieldLotBreakdown, CalculatedLotInfo } from "@/data/backendParcelsGeoJson";
import {
  Layers,
  ChevronDown,
  ChevronUp,
  Maximize2,
  Sparkles,
  MapPin,
  TrendingUp,
  Compass,
} from "lucide-react";

export interface FieldHectaresInspectorProps {
  field: FieldItem;
  fieldsList: FieldItem[];
  timelineState?: TimelineState;
  selectedDate?: string;
  onSelectField: (field: FieldItem) => void;
  onFocusField: () => void;
  onFocusLot: (lng: number, lat: number) => void;
  className?: string;
}

export default function FieldHectaresInspector({
  field,
  fieldsList,
  timelineState,
  selectedDate,
  onSelectField,
  onFocusField,
  onFocusLot,
  className = "",
}: FieldHectaresInspectorProps) {
  const [isExpanded, setIsExpanded] = useState(true);
  const [selectedLotId, setSelectedLotId] = useState<string | null>(null);

  // Calculate lots breakdown dynamically
  const lots: CalculatedLotInfo[] = useMemo(() => {
    return getFieldLotBreakdown(field, timelineState, selectedDate);
  }, [field, timelineState, selectedDate]);

  const totalHectares = useMemo(() => {
    const sum = lots.reduce((acc, l) => acc + l.hectares, 0);
    return Number(sum.toFixed(1)) || field.hectares || 100;
  }, [lots, field.hectares]);

  const isLiveBackend = field.id.includes("-") && field.id.length > 20;

  return (
    <div
      className={`pointer-events-auto select-none transition-all duration-300 font-sans ${className}`}
      style={{ maxWidth: "460px", width: "100%" }}
    >
      <div className="rounded-2xl bg-papel/95 border border-piedra-soft shadow-2xl backdrop-blur-md overflow-hidden ring-1 ring-bosque/5">
        {/* Header Strip */}
        <div className="p-3.5 bg-gradient-to-r from-bosque to-bosque-deep text-nube flex items-center justify-between gap-2">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="h-8 w-8 rounded-xl bg-tierra/20 border border-tierra/40 flex items-center justify-center shrink-0">
              <Layers className="h-4 w-4 text-tierra" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-1.5">
                <span className="text-xs font-black tracking-tight truncate text-nube">
                  {field.name}
                </span>
                {isLiveBackend ? (
                  <span className="px-1.5 py-0.2 rounded-full bg-musgo/40 text-nube text-[9px] font-extrabold tracking-wide uppercase border border-musgo/50">
                    Live
                  </span>
                ) : (
                  <span className="px-1.5 py-0.2 rounded-full bg-cielo/25 text-cielo text-[9px] font-bold tracking-wide border border-cielo/40">
                    Portfolio
                  </span>
                )}
              </div>
              <div className="text-[11px] text-nube/70 flex items-center gap-2 mt-0.5">
                <span className="flex items-center gap-0.5 text-nube/50">
                  <MapPin className="h-3 w-3 text-nube/50" />
                  {field.locality || "Zona Núcleo"}, {field.province || "Argentina"}
                </span>
                <span>•</span>
                <span className="font-extrabold text-nube text-xs">
                  {totalHectares} ha
                </span>
                <span>•</span>
                <span className="text-tierra font-semibold text-[10px]">
                  {lots.length} lotes
                </span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-1 shrink-0">
            <button
              onClick={onFocusField}
              title="Enfocar campo y parcelas a escala 1:1"
              className="h-7 px-2.5 rounded-lg bg-tierra hover:bg-tierra-deep text-bosque-deep text-[11px] font-black flex items-center gap-1 transition-all active:scale-95 cursor-pointer shadow-sm shadow-bosque-deep/30"
            >
              <Maximize2 className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">Enfocar</span>
            </button>
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              title={isExpanded ? "Colapsar panel" : "Expandir panel"}
              className="h-7 w-7 rounded-lg bg-white/10 hover:bg-white/20 text-nube flex items-center justify-center transition-all cursor-pointer"
            >
              {isExpanded ? (
                <ChevronUp className="h-4 w-4 text-nube/70" />
              ) : (
                <ChevronDown className="h-4 w-4 text-nube/70" />
              )}
            </button>
          </div>
        </div>

        {/* Quick Field Switcher Carousel */}
        <div className="px-3 py-2 bg-nube border-b border-piedra-soft flex items-center gap-1.5 overflow-x-auto scrollbar-none">
          <span className="text-[10px] font-extrabold uppercase text-piedra shrink-0 mr-1 flex items-center gap-1">
            <Compass className="h-3 w-3" /> Campos:
          </span>
          {fieldsList.slice(0, 8).map((f) => {
            const isSelected = f.id === field.id;
            return (
              <button
                key={f.id}
                onClick={() => onSelectField(f)}
                className={`px-2.5 py-1 rounded-full text-[10px] font-bold shrink-0 transition-all cursor-pointer flex items-center gap-1.5 ${
                  isSelected
                    ? "bg-bosque text-nube shadow-xs"
                    : "bg-papel text-bosque/70 border border-piedra-soft hover:border-musgo"
                }`}
              >
                <span className="truncate max-w-[100px]">{f.name.replace("Establecimiento ", "").replace("Campo ", "").replace("Lote ", "")}</span>
                <span className={`px-1 rounded-full text-[9px] font-extrabold ${isSelected ? "bg-nube/20 text-tierra" : "bg-nube text-bosque/60"}`}>
                  {f.hectares} ha
                </span>
              </button>
            );
          })}
        </div>

        {isExpanded && (
          <div className="p-3 space-y-3">
            {/* Proportional Hectares Distribution Bar */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-[11px]">
                <span className="font-extrabold text-bosque/80 flex items-center gap-1">
                  Distribución de Hectáreas
                </span>
                <span className="text-piedra font-medium text-[10px]">
                  Total: <b className="text-bosque">{totalHectares} ha</b>
                </span>
              </div>

              {/* Segmented bar */}
              <div className="h-4 w-full rounded-lg bg-piedra-soft/50 overflow-hidden flex shadow-inner border border-piedra-soft">
                {lots.map((lot) => (
                  <div
                    key={lot.id}
                    title={`${lot.name}: ${lot.hectares} ha (${lot.percent}%) · NDVI ${lot.ndvi}`}
                    onClick={() => {
                      setSelectedLotId(lot.id);
                      onFocusLot(lot.centroid[0], lot.centroid[1]);
                    }}
                    style={{
                      width: `${lot.percent}%`,
                      backgroundColor: lot.color,
                    }}
                    className="h-full transition-all hover:brightness-110 cursor-pointer relative group flex items-center justify-center text-[9px] font-extrabold text-white"
                  >
                    {lot.percent >= 15 && (
                      <span className="truncate px-1 drop-shadow-xs">
                        {lot.hectares} ha
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Interactive Lots Grid / Cards */}
            <div className="space-y-2 max-h-[260px] overflow-y-auto pr-1">
              {lots.map((lot, idx) => {
                const isSelected = selectedLotId === lot.id;
                return (
                  <div
                    key={lot.id}
                    onClick={() => {
                      setSelectedLotId(lot.id);
                      onFocusLot(lot.centroid[0], lot.centroid[1]);
                    }}
                    className={`p-2.5 rounded-xl border transition-all cursor-pointer flex items-center justify-between gap-2.5 ${
                      isSelected
                        ? "bg-musgo/10 border-musgo ring-2 ring-musgo/20 shadow-xs"
                        : "bg-nube border-piedra-soft hover:bg-papel hover:border-musgo/50"
                    }`}
                  >
                    <div className="flex items-center gap-2.5 min-w-0">
                      {/* NDVI Color pill indicator */}
                      <div
                        className="h-9 w-9 rounded-xl flex flex-col items-center justify-center shrink-0 text-white font-black text-[10px] shadow-xs"
                        style={{ backgroundColor: lot.color }}
                      >
                        <span className="text-[8px] font-normal leading-none opacity-90">NDVI</span>
                        <span className="leading-tight">{lot.ndvi.toFixed(2)}</span>
                      </div>

                      <div className="min-w-0">
                        <div className="flex items-center gap-1.5">
                          <span className="text-xs font-bold text-bosque truncate">
                            {lot.name}
                          </span>
                        </div>
                        <div className="text-[11px] text-piedra truncate mt-0.5">
                          {lot.crop} • <span className="text-musgo font-semibold">{lot.statusLabel}</span>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      <div className="text-right">
                        <div className="text-xs font-extrabold text-bosque">
                          {lot.hectares} ha
                        </div>
                        <div className="text-[10px] font-semibold text-piedra">
                          {lot.percent}% del lote
                        </div>
                      </div>

                      <button
                        title="Hacer zoom a esta parcela"
                        className="h-6 w-6 rounded-md bg-papel border border-piedra-soft text-bosque/60 hover:text-musgo hover:border-musgo flex items-center justify-center text-[10px] shadow-2xs"
                      >
                        ➔
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Footer Hint */}
            <div className="pt-2 border-t border-piedra-soft flex items-center justify-between text-[10px] text-piedra">
              <span className="flex items-center gap-1">
                <Sparkles className="h-3 w-3 text-tierra-deep" /> Colores sincronizados con Sentinel-2 y ERA5
              </span>
              <span>
                📅 {selectedDate || "Fecha activa"}
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
