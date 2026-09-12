"use client";

import React, { useEffect, useRef } from "react";
import { FieldItem, FIELDS_DATA } from "@/data/fieldsData";
import FieldCard from "./FieldCard";
import {
  Filter,
  MapPin,
} from "lucide-react";
import gsap from "gsap";

interface FieldCardsListProps {
  selectedField: FieldItem;
  onSelectField: (field: FieldItem) => void;
  onInspect3D?: (field: FieldItem) => void;
  filterQuery?: string;
  className?: string;
  /** Pass backend-fetched fields to override the local FIELDS_DATA mock */
  fields?: FieldItem[];
}

export default function FieldCardsList({
  selectedField,
  onSelectField,
  onInspect3D,
  filterQuery = "",
  className = "",
  fields,
}: FieldCardsListProps) {
  const listRef = useRef<HTMLDivElement>(null);
  const sourceData = fields ?? FIELDS_DATA;

  const filteredFields = React.useMemo(() => {
    if (!filterQuery.trim()) return sourceData;
    const q = filterQuery.toLowerCase();
    return sourceData.filter((field) => {
      const matchesName = field.name.toLowerCase().includes(q);
      const matchesLoc = (field.locality ?? "").toLowerCase().includes(q) || (field.province ?? "").toLowerCase().includes(q);
      const matchesCrop = (field.primaryCrop ?? field.crop ?? "").toLowerCase().includes(q);
      const matchesSoil = (field.soilSeries ?? field.soilType ?? "").toLowerCase().includes(q);
      const matchesTags = (field.tags ?? []).some((t: string) => t.toLowerCase().includes(q));
      return matchesName || matchesLoc || matchesCrop || matchesSoil || matchesTags;
    });
  }, [filterQuery, sourceData]);

  useEffect(() => {
    if (listRef.current) {
      const cards = listRef.current.querySelectorAll(".field-card-item");
      if (cards.length > 0) {
        gsap.fromTo(
          cards,
          { autoAlpha: 0, y: 15 },
          {
            autoAlpha: 1,
            y: 0,
            stagger: 0.06,
            duration: 0.4,
            ease: "power2.out",
          }
        );
      }
    }
  }, [filteredFields]);

  return (
    <div className={`flex flex-col h-full rounded-3xl border border-gray-200 bg-white shadow-sm overflow-hidden ${className}`}>
      {/* Scrollable Cards Container */}
      <div
        ref={listRef}
        className="flex-1 min-h-0 overflow-y-auto p-4 space-y-3 custom-scrollbar"
      >
        {filteredFields.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-center text-gray-400 space-y-2">
            <Filter className="h-8 w-8 text-gray-300" />
            <p className="text-xs text-gray-600">
              No se encontraron campos para la búsqueda.
            </p>
          </div>
        ) : (
          filteredFields.map((field) => (
            <FieldCard
              key={field.id}
              field={field}
              isSelected={selectedField.id === field.id}
              onSelect={onSelectField}
              onInspect3D={onInspect3D}
            />
          ))
        )}
      </div>

      {/* Selected Field Quick Footer Stats */}
      <div className="p-3.5 border-t border-gray-100 bg-gray-50/70 shrink-0 flex items-center justify-between text-xs text-gray-600">
        <span className="flex items-center gap-1.5 truncate">
          <MapPin className="h-3.5 w-3.5 text-blue-600" />
          <span>Fijado: <strong className="text-gray-900">{selectedField.name}</strong></span>
        </span>
        <span className="font-semibold text-gray-900 shrink-0">
          {selectedField.hectares} ha • {selectedField.rentQqSoja} qq Soja
        </span>
      </div>
    </div>
  );
}
