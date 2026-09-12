"use client";

import React, { useState, useRef } from "react";
import gsap from "gsap";
import { useGSAP } from "@gsap/react";
import { SolanaCertification } from "@/types/terria";

gsap.registerPlugin(useGSAP);

export interface SolanaAuditCardProps {
  certification: SolanaCertification;
  className?: string;
}

export default function SolanaAuditCard({
  certification,
  className = "",
}: SolanaAuditCardProps) {
  const [copiedField, setCopiedField] = useState<string | null>(null);
  const cardRef = useRef<HTMLDivElement>(null);

  useGSAP(
    () => {
      gsap.fromTo(
        cardRef.current,
        { autoAlpha: 0, y: 15 },
        { autoAlpha: 1, y: 0, duration: 0.4, ease: "power3.out" }
      );
    },
    { scope: cardRef }
  );

  const handleCopy = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    setCopiedField(label);
    setTimeout(() => setCopiedField(null), 2000);
  };

  const shortHash = `${certification.snapshotHash.slice(0, 10)}...${certification.snapshotHash.slice(-8)}`;
  const shortTx = `${certification.txSignature.slice(0, 10)}...${certification.txSignature.slice(-8)}`;

  return (
    <div
      ref={cardRef}
      className={`group relative flex flex-col justify-between rounded-2xl border border-piedra-soft bg-papel p-4.5 shadow-xs transition-colors duration-200 hover:border-tierra-deep select-none ${className}`}
    >
      {/* Header */}
      <div className="flex items-center justify-between border-b border-piedra-soft pb-2.5">
        <span className="text-[10px] font-mono font-bold tracking-wider text-piedra uppercase">
          Certificación Inmutable
        </span>
        <span className="rounded-full bg-tierra/15 border border-tierra/50 px-2 py-0.5 text-[9px] font-mono font-bold text-tierra-deep tracking-wider uppercase">
          Solana Devnet
        </span>
      </div>

      {/* Audit Rows */}
      <div className="py-3 space-y-3">
        {/* Snapshot Hash */}
        <div className="rounded-xl bg-nube border border-piedra-soft p-2.5 transition-colors group-hover:bg-tierra/10">
          <div className="flex items-center justify-between">
            <span className="text-[9px] font-mono font-bold text-piedra uppercase tracking-wider">
              Snapshot Hash (SHA-256)
            </span>
            <button
              onClick={() => handleCopy(certification.snapshotHash, "hash")}
              className="text-[9px] font-mono font-bold text-bosque/60 hover:text-bosque transition-colors uppercase cursor-pointer"
            >
              {copiedField === "hash" ? "Copiado" : "Copiar"}
            </button>
          </div>
          <div className="mt-1 font-mono text-xs font-bold text-bosque break-all">
            {shortHash}
          </div>
        </div>

        {/* Solana Memo Transaction */}
        <div className="rounded-xl bg-nube border border-piedra-soft p-2.5 transition-colors group-hover:bg-tierra/10">
          <div className="flex items-center justify-between">
            <span className="text-[9px] font-mono font-bold text-piedra uppercase tracking-wider">
              Tx Signature (Memo Program)
            </span>
            <button
              onClick={() => handleCopy(certification.txSignature, "tx")}
              className="text-[9px] font-mono font-bold text-bosque/60 hover:text-bosque transition-colors uppercase cursor-pointer"
            >
              {copiedField === "tx" ? "Copiado" : "Copiar"}
            </button>
          </div>
          <div className="mt-1 font-mono text-xs font-bold text-tierra-deep break-all">
            {shortTx}
          </div>
        </div>

        {/* Slot & Campaign */}
        <div className="grid grid-cols-2 gap-2 text-[10px] font-mono">
          <div className="rounded-lg bg-nube p-2 border border-piedra-soft">
            <span className="text-piedra block text-[8px] uppercase">Slot On-Chain</span>
            <span className="font-bold text-bosque/80">{certification.slot}</span>
          </div>
          <div className="rounded-lg bg-nube p-2 border border-piedra-soft">
            <span className="text-piedra block text-[8px] uppercase">Campaña</span>
            <span className="font-bold text-bosque/80">{certification.campaign}</span>
          </div>
        </div>
      </div>

      {/* Explorer Link CTA */}
      <div className="border-t border-piedra-soft pt-3">
        <a
          href={certification.explorerUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="flex w-full items-center justify-center rounded-xl bg-bosque hover:bg-bosque-deep text-nube px-3 py-2 text-xs font-mono font-bold tracking-wider uppercase transition-all duration-150 cursor-pointer shadow-xs active:scale-[0.99]"
        >
          Ver en Solana Explorer
        </a>
      </div>
    </div>
  );
}
