import React from "react";
import BrandMark from "@/components/brand/BrandMark";
import Seal from "@/components/brand/Seal";
import CoordinateTag from "@/components/brand/CoordinateTag";
import { FieldItem } from "@/data/fieldsData";

export interface ParcelCertificateProps {
  field?: FieldItem;
  certificateId?: string;
  version?: string;
  hash?: string;
  className?: string;
}

/** Glifo abstracto de parcela: polígono territorial + estratos interiores. */
function ParcelGlyph() {
  return (
    <svg viewBox="0 0 200 160" className="h-full w-full" aria-hidden="true">
      {/* parcela */}
      <polygon
        points="38,22 162,14 178,64 150,138 60,146 26,96"
        fill="#f4f6f2"
        stroke="#1c3a2e"
        strokeWidth="2"
      />
      {/* estratos interiores recortados a la parcela */}
      <clipPath id="parcelClip">
        <polygon points="38,22 162,14 178,64 150,138 60,146 26,96" />
      </clipPath>
      <g clipPath="url(#parcelClip)" stroke="#8a9a6b" strokeWidth="1" fill="none" opacity="0.8">
        <path d="M10 50 C60 42 120 60 200 46" />
        <path d="M10 66 C60 58 120 76 200 62" />
        <path d="M10 82 C60 74 120 92 200 78" />
        <path d="M10 98 C60 90 120 108 200 94" />
        <path d="M10 114 C60 106 120 124 200 110" />
      </g>
      {/* marcador */}
      <circle cx="104" cy="78" r="4" fill="#c9b28a" stroke="#1c3a2e" strokeWidth="1.5" />
      <line x1="104" y1="70" x2="104" y2="62" stroke="#1c3a2e" strokeWidth="1.5" />
      {/* norte */}
      <text x="172" y="30" fontFamily="monospace" fontSize="9" fill="#a7a7a0">N ↑</text>
    </svg>
  );
}

/** QR ficticio determinista — elemento gráfico, no verificación real. */
function PseudoQr({ seed = 2847 }: { seed?: number }) {
  const n = 15;
  const cells: React.ReactNode[] = [];
  const finder = (cx: number, cy: number) => (
    <g key={`f${cx}${cy}`}>
      <rect x={cx * 8} y={cy * 8} width={56} height={56} fill="#1c3a2e" />
      <rect x={cx * 8 + 8} y={cy * 8 + 8} width={40} height={40} fill="#fafaf6" />
      <rect x={cx * 8 + 16} y={cy * 8 + 16} width={24} height={24} fill="#1c3a2e" />
    </g>
  );
  const isFinder = (x: number, y: number) =>
    (x < 7 && y < 7) || (x > n - 8 && y < 7) || (x < 7 && y > n - 8);

  for (let y = 0; y < n; y++) {
    for (let x = 0; x < n; x++) {
      if (isFinder(x, y)) continue;
      const bit = (x * 31 + y * 17 + seed) % 7;
      if (bit < 3) {
        cells.push(
          <rect key={`${x}-${y}`} x={x * 8} y={y * 8} width={8} height={8} fill="#1c3a2e" />
        );
      }
    }
  }
  return (
    <svg viewBox={`0 0 ${n * 8} ${n * 8}`} className="h-20 w-20" aria-hidden="true">
      {cells}
      {finder(0, 0)}
      {finder(n - 7, 0)}
      {finder(0, n - 7)}
    </svg>
  );
}

/**
 * TERRIA Parcel Certificate — documento institucional premium.
 * El historial verificable de una parcela, presentado como pieza editorial.
 */
export default function ParcelCertificate({
  field,
  certificateId = "TR-AR-2847-0013",
  version = "V04",
  hash = "sha256:8f2a4c…9d1e77c4",
  className = "",
}: ParcelCertificateProps) {
  const name = field?.name ?? "Estancia La Felicidad";
  const location = field
    ? `${field.locality}, ${field.province}`
    : "Pergamino, Buenos Aires";
  const coords = field?.coordinates ?? "33°53′ S — 60°34′ W";
  const hectares = field ? `${field.hectares} ha` : "327,4 ha";

  return (
    <article
      className={`relative overflow-hidden rounded-3xl border border-piedra-soft bg-papel shadow-[0_24px_60px_-24px_rgba(18,39,30,0.25)] ${className}`}
    >
      {/* Header del documento */}
      <header className="flex items-center justify-between gap-4 border-b border-piedra-soft px-6 py-4 sm:px-8">
        <BrandMark tone="dark" size={22} />
        <div className="flex items-center gap-3">
          <CoordinateTag>Parcel Certificate</CoordinateTag>
          <Seal state="verified" />
        </div>
      </header>

      {/* Cuerpo */}
      <div className="grid gap-6 px-6 py-6 sm:grid-cols-[1fr_220px] sm:px-8">
        <div className="space-y-5">
          <div>
            <CoordinateTag className="mb-1 block">
              Parcela certificada · N° {certificateId}
            </CoordinateTag>
            <h3 className="font-display text-2xl font-medium tracking-tight text-bosque sm:text-3xl">
              {name}
            </h3>
            <p className="mt-1 font-mono text-[11px] uppercase tracking-[0.2em] text-piedra">
              {location} · {coords}
            </p>
          </div>

          <dl className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
            <div className="border-l-2 border-piedra-soft pl-3">
              <dt className="font-mono text-[9px] uppercase tracking-[0.2em] text-piedra">
                Superficie
              </dt>
              <dd className="font-bold text-bosque">{hectares}</dd>
            </div>
            <div className="border-l-2 border-piedra-soft pl-3">
              <dt className="font-mono text-[9px] uppercase tracking-[0.2em] text-piedra">
                Historial verificado
              </dt>
              <dd className="font-bold text-bosque">2021 — 2025</dd>
            </div>
            <div className="border-l-2 border-piedra-soft pl-3">
              <dt className="font-mono text-[9px] uppercase tracking-[0.2em] text-piedra">
                Cultivos detectados
              </dt>
              <dd className="font-bold text-bosque">Soja · Maíz · Trigo</dd>
            </div>
            <div className="border-l-2 border-piedra-soft pl-3">
              <dt className="font-mono text-[9px] uppercase tracking-[0.2em] text-piedra">
                Versión actual
              </dt>
              <dd className="font-bold text-bosque">{version} · Verified</dd>
            </div>
          </dl>

          <div className="rounded-2xl bg-nube p-3.5 font-mono text-[10px] leading-relaxed text-bosque/70">
            <span className="text-piedra">REGISTRO —</span> Cuatro campañas
            selladas. La integridad del historial se ancla por hash de estado;
            cualquier modificación retroactiva invalida la cadena de evidencia.
          </div>
        </div>

        {/* Mapa abstracto + QR */}
        <div className="flex flex-col items-center gap-4">
          <div className="w-full max-w-[220px] rounded-2xl border border-piedra-soft bg-nube p-3">
            <ParcelGlyph />
            <p className="mt-1 text-center font-mono text-[9px] uppercase tracking-[0.18em] text-piedra">
              Huella territorial · EPSG:4326
            </p>
          </div>
          <PseudoQr />
        </div>
      </div>

      {/* Footer de evidencia */}
      <footer className="flex flex-wrap items-center justify-between gap-3 border-t border-piedra-soft bg-bosque px-6 py-3.5 sm:px-8">
        <span className="font-mono text-[10px] tracking-[0.14em] text-nube/80">
          {hash}
        </span>
        <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-tierra">
          Historia real · Valor a futuro
        </span>
      </footer>
    </article>
  );
}
