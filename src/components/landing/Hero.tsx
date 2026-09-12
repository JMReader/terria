"use client";

import React, { useRef } from "react";
import gsap from "gsap";
import { useGSAP } from "@gsap/react";
import BrandMark from "@/components/brand/BrandMark";
import ContourLines from "@/components/brand/ContourLines";
import CoordinateTag from "@/components/brand/CoordinateTag";
import Seal from "@/components/brand/Seal";

gsap.registerPlugin(useGSAP);

/**
 * Hero de marca — Verde Bosque + foto aérea (public/brand/hero-bg.jpg).
 * Si la imagen no existe, queda el bosque con estratos SVG (fallback nativo).
 */
export default function Hero() {
  const scopeRef = useRef<HTMLElement>(null);

  useGSAP(
    () => {
      const tl = gsap.timeline({ defaults: { ease: "power3.out" } });
      tl.fromTo(
        ".hero-bg",
        { scale: 1.08, autoAlpha: 0 },
        { scale: 1, autoAlpha: 1, duration: 1.4 }
      )
        .fromTo(
          ".hero-topbar",
          { y: -18, autoAlpha: 0 },
          { y: 0, autoAlpha: 1, duration: 0.6 },
          "-=1.0"
        )
        .fromTo(
          ".hero-kicker",
          { y: 16, autoAlpha: 0 },
          { y: 0, autoAlpha: 1, duration: 0.55 },
          "-=0.6"
        )
        .fromTo(
          ".hero-title",
          { y: 34, autoAlpha: 0 },
          { y: 0, autoAlpha: 1, duration: 0.8 },
          "-=0.4"
        )
        .fromTo(
          ".hero-sub, .hero-meta, .hero-ctas",
          { y: 20, autoAlpha: 0 },
          { y: 0, autoAlpha: 1, stagger: 0.1, duration: 0.6 },
          "-=0.5"
        )
        .fromTo(
          ".hero-caption",
          { autoAlpha: 0 },
          { autoAlpha: 1, duration: 0.6 },
          "-=0.3"
        );
    },
    { scope: scopeRef }
  );

  return (
    <section
      ref={scopeRef}
      className="relative flex min-h-svh flex-col overflow-hidden bg-bosque-deep text-nube"
    >
      {/* Fondo: foto aérea generada — cae al bosque si falta el asset */}
      <div
        className="hero-bg absolute inset-0 bg-cover bg-center"
        style={{ backgroundImage: "url(/brand/hero-bg.jpg)" }}
      />
      {/* Veladuras para legibilidad editorial */}
      <div className="absolute inset-0 bg-gradient-to-t from-bosque-deep via-bosque/55 to-bosque/20" />
      <div className="absolute inset-0 bg-gradient-to-r from-bosque-deep/70 via-transparent to-transparent" />
      {/* Estratos de marca sobre la foto */}
      <div className="absolute inset-0 opacity-50 mix-blend-screen">
        <ContourLines tone="dark" lines={14} />
      </div>

      {/* Topbar del hero */}
      <div className="hero-topbar relative z-10 flex items-center justify-between px-6 pt-6 sm:px-10 sm:pt-8">
        <BrandMark tone="light" size={30} />
        <CoordinateTag tone="light" className="hidden sm:block">
          Tierra · Datos · Historia — AR
        </CoordinateTag>
      </div>

      {/* Contenido principal, abajo a la izquierda (composición editorial) */}
      <div className="relative z-10 mt-auto flex flex-col gap-6 px-6 pb-16 sm:px-10 sm:pb-20 max-w-3xl">
        <div className="hero-kicker">
          <CoordinateTag tone="light" className="text-tierra">
            Certificación de parcelas
          </CoordinateTag>
        </div>

        <h1 className="hero-title font-display text-5xl sm:text-6xl lg:text-7xl font-medium leading-[1.02] tracking-tight">
          El campo también
          <br />
          tiene memoria.
        </h1>

        <p className="hero-sub max-w-xl text-base sm:text-lg leading-relaxed text-nube/80">
          Convertimos cada parcela en un activo con memoria digital: qué pasó,
          qué se sembró, qué puede pasar. Historial verificable, permanente.
        </p>

        <div className="hero-meta flex flex-wrap items-center gap-x-5 gap-y-2 font-mono text-[11px] uppercase tracking-[0.2em] text-nube/60">
          <span>33.89° S — 60.57° W</span>
          <span className="text-nube/30">/</span>
          <span>Versión V04</span>
          <span className="text-nube/30">/</span>
          <Seal state="verified" />
        </div>

        <div className="hero-ctas flex flex-wrap items-center gap-3 pt-2">
          <a
            href="#explorador"
            className="rounded-full bg-nube px-6 py-3 text-xs font-mono font-bold uppercase tracking-[0.15em] text-bosque transition-all hover:bg-tierra hover:text-bosque-deep shadow-md"
          >
            Explorar parcelas
          </a>
        </div>
      </div>

      {/* Caption de evidencia, abajo a la derecha */}
      <div className="hero-caption pointer-events-none absolute bottom-6 right-6 z-10 hidden text-right sm:block sm:right-10">
        <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-nube/50">
          Parcela certificada N° TR-AR-2847-0013
        </p>
        <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-nube/50">
          Pergamino, Buenos Aires
        </p>
      </div>

      {/* Cue de scroll */}
      <div className="pointer-events-none absolute bottom-5 left-1/2 z-10 -translate-x-1/2 sm:bottom-6">
        <span className="block h-8 w-px bg-nube/40" />
      </div>
    </section>
  );
}
