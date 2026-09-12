"use client";

import React, { useState, useRef } from "react";
import {
  Search,
  Mic,
  X,
} from "lucide-react";
import gsap from "gsap";

interface NaturalLanguageSearchProps {
  onSearchChange?: (query: string) => void;
  className?: string;
}

export default function NaturalLanguageSearch({
  onSearchChange,
  className = "",
}: NaturalLanguageSearchProps) {
  const [query, setQuery] = useState("");
  const [isFocused, setIsFocused] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const detectedTags = React.useMemo(() => {
    const q = query.toLowerCase();
    const tags: string[] = [];
    if (q.includes("córdoba") || q.includes("cordoba") || q.includes("río cuarto")) {
      tags.push("Córdoba");
    }
    if (q.includes("buenos aires") || q.includes("pergamino") || q.includes("balcarce")) {
      tags.push("Buenos Aires");
    }
    if (q.includes("santa fe") || q.includes("venado tuerto")) {
      tags.push("Santa Fe");
    }
    if (q.includes("maíz") || q.includes("maiz")) {
      tags.push("Cultivo: Maíz");
    }
    if (q.includes("soja")) {
      tags.push("Cultivo: Soja");
    }
    if (q.includes("riego") || q.includes("pivote")) {
      tags.push("Riego Mecanizado");
    }
    if (q.includes("clase i") || q.includes("suelo")) {
      tags.push("Suelo Clase I");
    }
    if (q.includes("300") || q.includes("ha") || q.includes("hectárea")) {
      tags.push("> 300 ha");
    }
    return tags;
  }, [query]);


  const handleClear = () => {
    setQuery("");
    if (onSearchChange) onSearchChange("");
  };

  const toggleMic = () => {
    setIsListening((prev) => !prev);
  };

  return (
    <div className={`w-full max-w-4xl mx-auto space-y-2.5 ${className}`}>
      {/* Rectángulo largo y bajo con bordes super redondeados estilo Google */}
      <div
        ref={containerRef}
        className={`relative flex items-center h-12 w-full rounded-full bg-white transition-all duration-200 ${
          isFocused
            ? "shadow-[0_2px_10px_rgba(32,33,36,0.22)] border border-transparent ring-1 ring-gray-300"
            : "border border-gray-200 shadow-[0_1px_6px_rgba(32,33,36,0.1)] hover:shadow-[0_2px_8px_rgba(32,33,36,0.16)] hover:border-gray-300"
        } px-4 gap-3`}
      >
        {/* Google Style Search Magnifier Icon */}
        <Search className="h-4 w-4 text-gray-400 shrink-0 stroke-[2.2]" />

        {/* Input Text */}
        <input
          type="text"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            if (onSearchChange) onSearchChange(e.target.value);
          }}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          placeholder="Busca en lenguaje natural, ej: 'Campos de más de 300 ha en Córdoba para maíz con napa óptima'..."
          className="flex-1 bg-transparent text-sm text-gray-800 placeholder:text-gray-400 focus:outline-none font-sans"
        />

        {/* Clear Button */}
        {query && (
          <button
            onClick={handleClear}
            type="button"
            className="p-1 rounded-full text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        )}

        {/* Google Style Mic Button */}
        <button
          onClick={toggleMic}
          type="button"
          title={isListening ? "Detener voz" : "Búsqueda por voz"}
          className={`p-1.5 rounded-full transition-colors ${
            isListening
              ? "bg-red-50 text-red-500 animate-pulse"
              : "text-gray-400 hover:text-gray-700 hover:bg-gray-100"
          }`}
        >
          <Mic className="h-4 w-4" />
        </button>

        {/* Search Button (Minimalist pill) */}
        <button
          type="button"
          className="flex items-center gap-1.5 rounded-full bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold px-4 py-1.5 shadow-xs transition-colors cursor-pointer"
        >
          <span>Buscar</span>
        </button>
      </div>

      {/* Detected Entities Tags */}
      {detectedTags.length > 0 && (
        <div className="flex items-center gap-1.5 px-3 overflow-x-auto text-xs no-scrollbar">
          <span className="text-gray-400 text-[11px] font-medium shrink-0">
            Filtros reconocidos:
          </span>
          {detectedTags.map((tag, idx) => (
            <span
              key={idx}
              className="inline-flex items-center rounded-full bg-blue-50 border border-blue-200/70 px-2.5 py-0.5 text-[11px] font-medium text-blue-700 shrink-0"
            >
              {tag}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
