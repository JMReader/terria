import React from "react";

export interface ParcelVersion {
  version: string; // "V01"
  period: string; // "2022/23"
  crop: string; // "Soja"
  state: "verified" | "pending";
}

export interface VersionTimelineProps {
  versions: ParcelVersion[];
  className?: string;
}

export const DEFAULT_VERSIONS: ParcelVersion[] = [
  { version: "V01", period: "2021/22", crop: "Soja", state: "verified" },
  { version: "V02", period: "2022/23", crop: "Maíz", state: "verified" },
  { version: "V03", period: "2023/24", crop: "Trigo / Soja", state: "verified" },
  { version: "V04", period: "2024/25", crop: "Soja", state: "verified" },
];

/**
 * El campo versionado: cada campaña es un snapshot certificado.
 * Metáfora central de marca hecha componente.
 */
export default function VersionTimeline({
  versions = DEFAULT_VERSIONS,
  className = "",
}: VersionTimelineProps) {
  return (
    <ol className={`relative ${className}`}>
      {versions.map((v, i) => {
        const isLast = i === versions.length - 1;
        return (
          <li key={v.version} className="relative flex gap-4 pb-6 last:pb-0">
            {/* Rail + nodo */}
            <div className="flex flex-col items-center">
              <span
                className={`mt-1 h-2.5 w-2.5 rounded-full border-2 ${
                  isLast
                    ? "border-tierra-deep bg-tierra"
                    : "border-musgo bg-nube"
                }`}
              />
              {!isLast && <span className="mt-1 w-px flex-1 bg-piedra-soft" />}
            </div>

            <div className="flex flex-1 items-baseline justify-between gap-3">
              <div>
                <span className="font-mono text-[11px] font-bold tracking-[0.18em] text-bosque">
                  {v.version}
                </span>
                <span className="ml-3 font-mono text-[11px] text-piedra">
                  {v.period}
                </span>
                <span className="ml-3 text-sm font-medium text-bosque/80">
                  {v.crop}
                </span>
              </div>
              <span
                className={`font-mono text-[9px] font-bold uppercase tracking-[0.18em] ${
                  v.state === "verified" ? "text-tierra-deep" : "text-piedra"
                }`}
              >
                {v.state === "verified" ? "Verified" : "Pendiente"}
              </span>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
