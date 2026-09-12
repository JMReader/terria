"use client";

import React, { useState, useRef, useEffect, useCallback } from "react";
import { Search, X, Mic, Command } from "lucide-react";
import gsap from "gsap";
import { useGSAP } from "@gsap/react";
import { FieldItem } from "@/data/fieldsData";
import BrandMark from "@/components/brand/BrandMark";

gsap.registerPlugin(useGSAP);

interface FloatingIslandHeaderProps {
  onSearchChange?: (query: string) => void;
  onRegisterField?: () => void;
  selectedField?: FieldItem;
  totalFields?: number;
  className?: string;
  backendStatus?: "loading" | "connected" | "offline";
}

export default function FloatingIslandHeader({
  onSearchChange,
  onRegisterField,
  className = "",
}: FloatingIslandHeaderProps) {
  const [query, setQuery] = useState("");
  const [isListening, setIsListening] = useState(false);
  const [isFocused, setIsFocused] = useState(false);

  const headerScopeRef = useRef<HTMLDivElement>(null);
  const islandRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Subtle GSAP entrance
  useGSAP(
    () => {
      if (islandRef.current) {
        gsap.from(islandRef.current, {
          y: -16,
          autoAlpha: 0,
          duration: 0.5,
          ease: "power3.out",
        });
      }
    },
    { scope: headerScopeRef }
  );

  // Shortcut Ctrl/Cmd + K to focus search
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        inputRef.current?.focus();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const handleClear = () => {
    setQuery("");
    if (onSearchChange) onSearchChange("");
    inputRef.current?.focus();
  };

  const toggleMic = () => {
    setIsListening((prev) => !prev);
  };

  return (
    <div ref={headerScopeRef} className={`select-none ${className}`}>
      {/* Main Island Container — normal layout element, not fixed */}
      <header
        ref={islandRef}
      >
        <div className="relative rounded-2xl sm:rounded-full bg-papel/95 backdrop-blur-xl border border-piedra-soft/80 shadow-[0_12px_36px_-6px_rgba(28,58,46,0.14),0_2px_8px_rgba(0,0,0,0.04)] ring-1 ring-papel/80 p-2 sm:px-4 sm:py-2 transition-shadow">
          <div className="flex items-center justify-between gap-3 sm:gap-4">
            {/* Left: Brand */}
            <div className="flex items-center shrink-0 pl-1 sm:pl-2 gap-2">
              <BrandMark tone="dark" size={20} />
            </div>

            {/* Center: Integrated Natural Language Search Field */}
            <div className="flex-1 min-w-0">
              <div
                className={`relative flex items-center h-10 w-full rounded-full bg-nube/90 transition-all duration-200 px-3 gap-2.5 border ${
                  isFocused
                    ? "border-musgo bg-papel ring-2 ring-musgo/20 shadow-sm"
                    : "border-piedra-soft/70 hover:border-piedra hover:bg-papel"
                }`}
              >
                <Search className="h-4 w-4 text-piedra shrink-0 stroke-[2.2]" />

                <input
                  ref={inputRef}
                  type="text"
                  value={query}
                  onChange={(e) => {
                    setQuery(e.target.value);
                    if (onSearchChange) onSearchChange(e.target.value);
                  }}
                  onFocus={() => setIsFocused(true)}
                  onBlur={() => setIsFocused(false)}
                  placeholder="Buscar campo, cultivo, zona..."
                  className="flex-1 bg-transparent text-xs sm:text-sm text-bosque placeholder:text-piedra focus:outline-none font-sans min-w-0"
                />

                {query ? (
                  <button
                    onClick={handleClear}
                    type="button"
                    title="Limpiar búsqueda"
                    className="p-1 rounded-full text-piedra hover:text-bosque hover:bg-piedra-soft/60 transition-colors cursor-pointer"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                ) : (
                  <kbd className="hidden md:inline-flex items-center gap-0.5 rounded border border-piedra-soft bg-papel px-1.5 py-0.5 text-[10px] font-mono text-piedra shadow-2xs">
                    <Command className="h-2.5 w-2.5" /> K
                  </kbd>
                )}

                <button
                  onClick={toggleMic}
                  type="button"
                  title={isListening ? "Detener voz" : "Búsqueda por voz"}
                  className={`p-1.5 rounded-full transition-colors cursor-pointer ${
                    isListening
                      ? "bg-tierra/20 text-tierra-deep animate-pulse"
                      : "text-piedra hover:text-bosque hover:bg-piedra-soft/60"
                  }`}
                >
                  <Mic className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>

            {/* Right: Botón Registra tu campo */}
            <div className="flex items-center shrink-0 pr-1">
              <button
                type="button"
                onClick={onRegisterField}
                className="rounded-full bg-bosque hover:bg-bosque-deep text-nube text-xs font-bold px-4 py-2 shadow-sm transition-all cursor-pointer whitespace-nowrap active:scale-95"
              >
                Registra tu campo
              </button>
            </div>
          </div>
        </div>
      </header>
    </div>
  );
}
