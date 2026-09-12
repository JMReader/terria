"use client";

import React from "react";
import { FieldItem } from "@/data/fieldsData";
import {
  MapPin,
  Droplets,
  Sparkles,
  Maximize2,
  CheckCircle2,
} from "lucide-react";

interface FieldCardProps {
  field: FieldItem;
  isSelected: boolean;
  onSelect: (field: FieldItem) => void;
  onInspect3D?: (field: FieldItem) => void;
}

export default function FieldCard({
  field,
  isSelected,
  onSelect,
  onInspect3D,
}: FieldCardProps) {
  return (
    <div
      onClick={() => onSelect(field)}
      className={`field-card-item group relative cursor-pointer rounded-2xl border transition-all duration-200 p-4 select-none ${
        isSelected
          ? "border-musgo bg-musgo/10 shadow-md ring-1 ring-musgo/30"
          : "border-piedra-soft bg-papel hover:border-piedra hover:shadow-sm"
      }`}
    >
      {/* Top Header: Code badge & Status */}
      <div className="flex items-center justify-between gap-2 mb-2">
        <div className="flex items-center gap-2">
          <span className="rounded-md bg-nube px-2 py-0.5 text-[11px] font-semibold text-bosque/80 tracking-wide font-mono">
            {field.code}
          </span>
          <span className="text-xs text-piedra flex items-center gap-1">
            <MapPin className="h-3.5 w-3.5 text-piedra" />
            {field.locality}, {field.province}
          </span>
        </div>

        <div className="flex items-center gap-1.5">
          {field.irrigation && (
            <span className="flex items-center gap-1 rounded-full bg-cielo/15 border border-cielo/40 px-2 py-0.5 text-[10px] font-medium text-cielo-deep">
              <Droplets className="h-3 w-3" /> Riego
            </span>
          )}
          <span
            className={`rounded-full px-2.5 py-0.5 text-[10px] font-medium capitalize ${
              field.status === "destacado"
                ? "bg-tierra/15 border border-tierra/50 text-tierra-deep"
                : field.status === "en_negociacion"
                ? "bg-piedra/15 border border-piedra/40 text-bosque/80"
                : "bg-musgo/10 border border-musgo/30 text-musgo"
            }`}
          >
            {field.status === "en_negociacion" ? "En Negociación" : field.status}
          </span>
        </div>
      </div>

      {/* Field Name & Agricultural Suitability */}
      <div className="flex items-start justify-between gap-2">
        <div>
          <h3 className="font-display text-lg font-semibold text-bosque group-hover:text-musgo transition-colors">
            {field.name}
          </h3>
          <p className="text-xs text-piedra mt-0.5 font-mono">
            {field.coordinates}
          </p>
        </div>

        <div className="text-right shrink-0">
          <div className="text-sm font-bold text-bosque flex items-center justify-end gap-1">
            <Sparkles className="h-3.5 w-3.5 text-tierra-deep" />
            {field.suitabilityScore}%
          </div>
          <span className="text-[10px] text-piedra block">
            Aptitud
          </span>
        </div>
      </div>

      {/* Agronomic Quick Glance */}
      <div className="grid grid-cols-3 gap-2 my-3 rounded-xl bg-nube p-2.5 border border-piedra-soft">
        <div>
          <span className="text-[10px] text-piedra block uppercase font-medium">Superficie</span>
          <span className="text-xs font-bold text-bosque">{field.hectares} ha</span>
        </div>
        <div>
          <span className="text-[10px] text-piedra block uppercase font-medium">Cultivo</span>
          <span className="text-xs font-bold text-bosque truncate block">
            {(field.primaryCrop || field.crop || "Cultivo").split(" ")[0]}
          </span>
        </div>
        <div>
          <span className="text-[10px] text-piedra block uppercase font-medium">Alquiler</span>
          <span className="text-xs font-bold text-musgo">{field.rentQqSoja != null ? `${field.rentQqSoja} qq/ha` : "N/D"}</span>
        </div>
      </div>

      {/* NDVI & Soil Series */}
      <div className="space-y-1.5 text-xs">
        <div className="flex items-center justify-between text-[11px] text-piedra">
          <span>Índice NDVI Satelital</span>
          <span className="font-semibold text-bosque/80">{field.ndvi.toFixed(2)} / 1.00</span>
        </div>
        <div className="h-1.5 w-full rounded-full bg-piedra-soft overflow-hidden">
          <div
            className="h-full rounded-full bg-musgo transition-all duration-300"
            style={{ width: `${field.ndvi * 100}%` }}
          />
        </div>

        <div className="pt-1 flex items-center justify-between text-xs text-bosque/70">
          <span className="truncate max-w-[210px]">{field.soilSeries || field.soilType || "Suelo agrícola"}</span>
          <span className="font-semibold text-bosque">{field.rentUsdHa != null ? `$${field.rentUsdHa} USD/ha` : "A consultar"}</span>
        </div>
      </div>

      {/* Tags */}
      <div className="flex flex-wrap items-center gap-1.5 mt-3 pt-2.5 border-t border-piedra-soft">
        {(field.tags || ["Lote"]).map((tag, idx) => (
          <span
            key={idx}
            className="rounded-md border border-piedra-soft bg-nube px-2 py-0.5 text-[10px] text-bosque/60"
          >
            {tag}
          </span>
        ))}
      </div>

      {/* Action Footer */}
      <div className="mt-3 flex items-center justify-between gap-2 pt-2 border-t border-piedra-soft">
        <span className="text-xs text-piedra">
          {isSelected ? (
            <span className="text-musgo font-medium flex items-center gap-1">
              <CheckCircle2 className="h-3.5 w-3.5" /> Lote seleccionado
            </span>
          ) : (
            "Clic para seleccionar"
          )}
        </span>

        {onInspect3D && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onInspect3D(field);
            }}
            className="flex items-center gap-1 rounded-lg bg-nube hover:bg-musgo/10 hover:text-musgo text-bosque/70 px-2.5 py-1 text-xs font-semibold transition-colors cursor-pointer"
          >
            <Maximize2 className="h-3 w-3" />
            <span>Ver en 3D</span>
          </button>
        )}
      </div>
    </div>
  );
}
