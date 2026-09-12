import React from "react";
import BrandMark from "@/components/brand/BrandMark";
import ContourLines from "@/components/brand/ContourLines";
import CoordinateTag from "@/components/brand/CoordinateTag";

/** Footer editorial — Verde Bosque, estratos, voz mono. */
export default function SiteFooter() {
  return (
    <footer className="relative overflow-hidden bg-bosque-deep text-nube">
      <div className="absolute inset-0 opacity-40">
        <ContourLines tone="dark" lines={10} />
      </div>

      <div className="relative z-10 mx-auto flex max-w-6xl flex-col gap-10 px-6 py-14 sm:px-10">
        <div className="flex flex-col justify-between gap-8 sm:flex-row sm:items-end">
          <div className="space-y-4">
            <BrandMark tone="light" size={30} />
            <p className="max-w-sm font-display text-xl leading-snug text-nube/85">
              La tierra tiene memoria.
              <br />
              Nosotros la hacemos verificable.
            </p>
          </div>

          <nav className="flex gap-10 font-mono text-[11px] uppercase tracking-[0.2em]">
            <div className="flex flex-col gap-2.5">
              <span className="text-tierra">Producto</span>
              <a href="#explorador" className="text-nube/70 transition-colors hover:text-nube">
                Explorador
              </a>
            </div>
            <div className="flex flex-col gap-2.5">
              <span className="text-tierra">Datos</span>
              <span className="text-nube/70">Sentinel-2 L2A</span>
              <span className="text-nube/70">ERA5 · Open-Meteo</span>
              <span className="text-nube/70">INTA Suelos</span>
            </div>
          </nav>
        </div>

        <div className="flex flex-col items-start justify-between gap-3 border-t border-nube/15 pt-5 sm:flex-row sm:items-center">
          <CoordinateTag tone="light">
            Terria · Certificación de parcelas · Argentina
          </CoordinateTag>
          <CoordinateTag tone="light" className="text-nube/40">
            Land first · Data second · Technology invisible
          </CoordinateTag>
        </div>
      </div>
    </footer>
  );
}
