import React from "react";
import SectionHeading from "@/components/brand/SectionHeading";
import ParcelCertificate from "@/components/landing/ParcelCertificate";
import VersionTimeline, { DEFAULT_VERSIONS } from "@/components/landing/VersionTimeline";
import { FieldItem, FIELDS_DATA } from "@/data/fieldsData";

export interface CertificateSectionProps {
  field?: FieldItem;
}

/**
 * Sección "Certificado" de la landing: el documento TERRIA + el sistema de
 * versiones históricas de la parcela.
 */
export default function CertificateSection({ field }: CertificateSectionProps) {
  const featured = field ?? FIELDS_DATA[1];

  return (
    <section id="certificado" className="relative bg-nube px-6 py-20 sm:px-10 sm:py-28">
      <div className="mx-auto max-w-6xl">
        <SectionHeading
          kicker="Certificación"
          title={
            <>
              Cada parcela,
              <br />
              un historial verificable.
            </>
          }
          description="El certificado TERRIA convierte el pasado productivo de un campo en evidencia: campañas, cultivos y eventos sellados como versiones permanentes."
          className="mb-12"
        />

        <div className="grid items-start gap-10 lg:grid-cols-[1.5fr_1fr]">
          <ParcelCertificate field={featured} />

          <div className="space-y-6 lg:pt-2">
            <div className="rounded-3xl border border-piedra-soft bg-papel p-6">
              <span className="mb-5 block font-mono text-[10px] font-bold uppercase tracking-[0.25em] text-piedra">
                Sistema de versiones
              </span>
              <VersionTimeline versions={DEFAULT_VERSIONS} />
            </div>

            <p className="px-1 font-mono text-[10px] leading-relaxed uppercase tracking-[0.15em] text-piedra">
              Cada campaña se sella como una versión. El territorio queda
              versionado — como el software, pero para la tierra.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
