"use client";

import React, { useState, useRef, useEffect, useCallback } from "react";
import { Search, X, Mic, Command } from "lucide-react";
import gsap from "gsap";
import { useGSAP } from "@gsap/react";
import { FieldItem } from "@/data/fieldsData";

gsap.registerPlugin(useGSAP);

interface FloatingIslandHeaderProps {
  onSearchChange?: (query: string) => void;
  onRegisterField?: () => void;
  selectedField?: FieldItem;
  totalFields?: number;
  className?: string;
}

export default function FloatingIslandHeader({
  onSearchChange,
  onRegisterField,
  className = "",
}: FloatingIslandHeaderProps) {
  const [query, setQuery] = useState("");
  const [isOpen, setIsOpen] = useState(true);
  const [isListening, setIsListening] = useState(false);
  const [isFocused, setIsFocused] = useState(false);

  const headerScopeRef = useRef<HTMLDivElement>(null);
  const islandRef = useRef<HTMLDivElement>(null);
  const peekNotchRef = useRef<HTMLButtonElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // GSAP slide down animation
  const showIsland = useCallback(() => {
    setIsOpen(true);
    if (!islandRef.current) return;

    gsap.to(islandRef.current, {
      y: 0,
      autoAlpha: 1,
      scale: 1,
      duration: 0.45,
      ease: "power3.out",
      overwrite: "auto",
    });

    if (peekNotchRef.current) {
      gsap.to(peekNotchRef.current, {
        y: -40,
        autoAlpha: 0,
        duration: 0.25,
        ease: "power2.in",
        overwrite: "auto",
      });
    }
  }, []);

  // GSAP slide up animation
  const hideIsland = useCallback(() => {
    setIsOpen(false);
    if (!islandRef.current) return;

    gsap.to(islandRef.current, {
      y: -85,
      autoAlpha: 0,
      scale: 0.97,
      duration: 0.38,
      ease: "power3.in",
      overwrite: "auto",
    });

    if (peekNotchRef.current) {
      gsap.to(peekNotchRef.current, {
        y: 0,
        autoAlpha: 1,
        duration: 0.4,
        delay: 0.12,
        ease: "back.out(1.7)",
        overwrite: "auto",
      });
    }
  }, []);

  // Initial Entrance animation with GSAP
  useGSAP(
    () => {
      if (islandRef.current) {
        gsap.from(islandRef.current, {
          y: -100,
          autoAlpha: 0,
          scale: 0.95,
          duration: 0.7,
          ease: "back.out(1.2)",
          delay: 0.15,
        });
      }
      if (peekNotchRef.current) {
        gsap.set(peekNotchRef.current, { y: -40, autoAlpha: 0 });
      }
    },
    { scope: headerScopeRef }
  );

  // Global listeners: Click outside to hide, mouse near top to reveal, Esc to close
  useEffect(() => {
    const handleDocumentClick = (e: MouseEvent) => {
      if (!islandRef.current) return;
      if (!islandRef.current.contains(e.target as Node)) {
        hideIsland();
      }
    };

    const handleMouseMove = (e: MouseEvent) => {
      if (e.clientY <= 38) {
        showIsland();
      }
    };

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        hideIsland();
        inputRef.current?.blur();
      }
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        showIsland();
        inputRef.current?.focus();
      }
    };

    document.addEventListener("mousedown", handleDocumentClick);
    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.removeEventListener("mousedown", handleDocumentClick);
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [hideIsland, showIsland]);

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
      {/* Invisible Hover Sensor Zone at the very top edge */}
      <div
        onMouseEnter={showIsland}
        className="fixed top-0 left-0 right-0 h-7 z-40 pointer-events-auto"
        aria-hidden="true"
      />

      {/* Micro Peek Notch visible when island is tucked away */}
      <button
        ref={peekNotchRef}
        onClick={showIsland}
        onMouseEnter={showIsland}
        title="Mostrar barra (o acerca el cursor arriba)"
        className="fixed top-2 left-1/2 -translate-x-1/2 z-50 flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-white/95 border border-slate-200/90 shadow-md backdrop-blur-md text-xs font-semibold text-slate-800 hover:text-blue-600 hover:border-blue-300 transition-all cursor-pointer pointer-events-auto"
      >
        <span className="h-2 w-2 rounded-full bg-blue-600" />
        <span className="text-xs font-black tracking-wider uppercase">Terra</span>
      </button>

      {/* Main Floating Dynamic Island Container */}
      <header
        ref={islandRef}
        onMouseEnter={() => {
          if (!isOpen) showIsland();
        }}
        className="fixed top-3 left-1/2 -translate-x-1/2 z-50 w-[94vw] max-w-4xl pointer-events-auto"
      >
        <div className="relative rounded-2xl sm:rounded-full bg-white/95 backdrop-blur-xl border border-slate-200/80 shadow-[0_12px_36px_-6px_rgba(15,23,42,0.12),0_2px_8px_rgba(0,0,0,0.04)] ring-1 ring-white/80 p-2 sm:px-4 sm:py-2 transition-shadow">
          <div className="flex items-center justify-between gap-3 sm:gap-4">
            {/* Left: Solo el nombre de la marca */}
            <div className="flex items-center shrink-0 pl-1 sm:pl-2">
              <span className="text-sm font-black tracking-widest text-slate-900 font-sans uppercase">
                TERRA
              </span>
            </div>

            {/* Center: Integrated Natural Language Search Field */}
            <div className="flex-1 min-w-0">
              <div
                className={`relative flex items-center h-10 w-full rounded-full bg-slate-50/90 transition-all duration-200 px-3 gap-2.5 border ${
                  isFocused
                    ? "border-blue-500 bg-white ring-2 ring-blue-500/15 shadow-sm"
                    : "border-slate-200/70 hover:border-slate-300 hover:bg-white"
                }`}
              >
                <Search className="h-4 w-4 text-slate-400 shrink-0 stroke-[2.2]" />

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
                  className="flex-1 bg-transparent text-xs sm:text-sm text-slate-800 placeholder:text-slate-400 focus:outline-none font-sans min-w-0"
                />

                {query ? (
                  <button
                    onClick={handleClear}
                    type="button"
                    title="Limpiar búsqueda"
                    className="p-1 rounded-full text-slate-400 hover:text-slate-700 hover:bg-slate-200/70 transition-colors cursor-pointer"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                ) : (
                  <kbd className="hidden md:inline-flex items-center gap-0.5 rounded border border-slate-200 bg-white px-1.5 py-0.5 text-[10px] font-mono text-slate-400 shadow-2xs">
                    <Command className="h-2.5 w-2.5" /> K
                  </kbd>
                )}

                <button
                  onClick={toggleMic}
                  type="button"
                  title={isListening ? "Detener voz" : "Búsqueda por voz"}
                  className={`p-1.5 rounded-full transition-colors cursor-pointer ${
                    isListening
                      ? "bg-red-50 text-red-500 animate-pulse"
                      : "text-slate-400 hover:text-slate-700 hover:bg-slate-200/70"
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
                className="rounded-full bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold px-4 py-2 shadow-sm transition-all cursor-pointer whitespace-nowrap active:scale-95"
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
