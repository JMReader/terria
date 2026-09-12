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
          ? "border-blue-600 bg-blue-50/25 shadow-md ring-1 ring-blue-600/30"
          : "border-gray-200 bg-white hover:border-gray-300 hover:shadow-sm"
      }`}
    >
      {/* Top Header: Code badge & Status */}
      <div className="flex items-center justify-between gap-2 mb-2">
        <div className="flex items-center gap-2">
          <span className="rounded-md bg-gray-100 px-2 py-0.5 text-[11px] font-semibold text-gray-700 tracking-wide font-mono">
            {field.code}
          </span>
          <span className="text-xs text-gray-500 flex items-center gap-1">
            <MapPin className="h-3.5 w-3.5 text-gray-400" />
            {field.locality}, {field.province}
          </span>
        </div>

        <div className="flex items-center gap-1.5">
          {field.irrigation && (
            <span className="flex items-center gap-1 rounded-full bg-sky-50 border border-sky-200 px-2 py-0.5 text-[10px] font-medium text-sky-700">
              <Droplets className="h-3 w-3" /> Riego
            </span>
          )}
          <span
            className={`rounded-full px-2.5 py-0.5 text-[10px] font-medium capitalize ${
              field.status === "destacado"
                ? "bg-amber-50 border border-amber-200 text-amber-800"
                : field.status === "en_negociacion"
                ? "bg-purple-50 border border-purple-200 text-purple-800"
                : "bg-emerald-50 border border-emerald-200 text-emerald-800"
            }`}
          >
            {field.status === "en_negociacion" ? "En Negociación" : field.status}
          </span>
        </div>
      </div>

      {/* Field Name & Agricultural Suitability */}
      <div className="flex items-start justify-between gap-2">
        <div>
          <h3 className="text-base font-bold text-gray-900 group-hover:text-blue-600 transition-colors">
            {field.name}
          </h3>
          <p className="text-xs text-gray-400 mt-0.5 font-mono">
            {field.coordinates}
          </p>
        </div>

        <div className="text-right shrink-0">
          <div className="text-sm font-bold text-gray-900 flex items-center justify-end gap-1">
            <Sparkles className="h-3.5 w-3.5 text-amber-500" />
            {field.suitabilityScore}%
          </div>
          <span className="text-[10px] text-gray-500 block">
            Aptitud
          </span>
        </div>
      </div>

      {/* Key Agronomic Metrics Box */}
      <div className="grid grid-cols-3 gap-2 my-3 rounded-xl bg-gray-50 p-2.5 border border-gray-100">
        <div>
          <span className="text-[10px] text-gray-400 block uppercase font-medium">Superficie</span>
          <span className="text-xs font-bold text-gray-800">{field.hectares} ha</span>
        </div>
        <div>
          <span className="text-[10px] text-gray-400 block uppercase font-medium">Cultivo</span>
          <span className="text-xs font-bold text-gray-800 truncate block">
            {field.primaryCrop.split(" ")[0]}
          </span>
        </div>
        <div>
          <span className="text-[10px] text-gray-400 block uppercase font-medium">Alquiler</span>
          <span className="text-xs font-bold text-blue-600">{field.rentQqSoja} qq/ha</span>
        </div>
      </div>

      {/* NDVI & Soil Series */}
      <div className="space-y-1.5 text-xs">
        <div className="flex items-center justify-between text-[11px] text-gray-500">
          <span>Índice NDVI Satelital</span>
          <span className="font-semibold text-gray-700">{field.ndvi.toFixed(2)} / 1.00</span>
        </div>
        <div className="h-1.5 w-full rounded-full bg-gray-200 overflow-hidden">
          <div
            className="h-full rounded-full bg-blue-600 transition-all duration-300"
            style={{ width: `${field.ndvi * 100}%` }}
          />
        </div>

        <div className="pt-1 flex items-center justify-between text-xs text-gray-600">
          <span className="truncate max-w-[210px]">{field.soilSeries}</span>
          <span className="font-semibold text-gray-900">${field.rentUsdHa} USD/ha</span>
        </div>
      </div>

      {/* Tags */}
      <div className="flex flex-wrap items-center gap-1.5 mt-3 pt-2.5 border-t border-gray-100">
        {field.tags.map((tag, idx) => (
          <span
            key={idx}
            className="rounded-md bg-gray-100 px-2 py-0.5 text-[10px] text-gray-600"
          >
            {tag}
          </span>
        ))}
      </div>

      {/* Action Footer */}
      <div className="mt-3 flex items-center justify-between gap-2 pt-2 border-t border-gray-100">
        <span className="text-xs text-gray-500">
          {isSelected ? (
            <span className="text-blue-600 font-medium flex items-center gap-1">
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
            className="flex items-center gap-1 rounded-lg bg-gray-100 hover:bg-blue-50 hover:text-blue-600 text-gray-700 px-2.5 py-1 text-xs font-semibold transition-colors cursor-pointer"
          >
            <Maximize2 className="h-3 w-3" />
            <span>Ver en 3D</span>
          </button>
        )}
      </div>
    </div>
  );
}
