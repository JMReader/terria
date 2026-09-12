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
      className={`group relative flex flex-col justify-between rounded-2xl border border-gray-200 bg-white p-4.5 shadow-xs transition-colors duration-200 hover:border-emerald-600 select-none ${className}`}
    >
      {/* Header */}
      <div className="flex items-center justify-between border-b border-gray-100 pb-2.5">
        <span className="text-[10px] font-mono font-bold tracking-wider text-gray-400 uppercase">
          Certificación Inmutable
        </span>
        <span className="rounded-full bg-emerald-50 border border-emerald-200 px-2 py-0.5 text-[9px] font-mono font-bold text-emerald-700 tracking-wider uppercase">
          Solana Devnet
        </span>
      </div>

      {/* Audit Rows */}
      <div className="py-3 space-y-3">
        {/* Snapshot Hash */}
        <div className="rounded-xl bg-gray-50/70 border border-gray-100 p-2.5 transition-colors group-hover:bg-emerald-50/30">
          <div className="flex items-center justify-between">
            <span className="text-[9px] font-mono font-bold text-gray-400 uppercase tracking-wider">
              Snapshot Hash (SHA-256)
            </span>
            <button
              onClick={() => handleCopy(certification.snapshotHash, "hash")}
              className="text-[9px] font-mono font-bold text-gray-500 hover:text-gray-900 transition-colors uppercase cursor-pointer"
            >
              {copiedField === "hash" ? "Copiado" : "Copiar"}
            </button>
          </div>
          <div className="mt-1 font-mono text-xs font-bold text-gray-800 break-all">
            {shortHash}
          </div>
        </div>

        {/* Solana Memo Transaction */}
        <div className="rounded-xl bg-gray-50/70 border border-gray-100 p-2.5 transition-colors group-hover:bg-emerald-50/30">
          <div className="flex items-center justify-between">
            <span className="text-[9px] font-mono font-bold text-gray-400 uppercase tracking-wider">
              Tx Signature (Memo Program)
            </span>
            <button
              onClick={() => handleCopy(certification.txSignature, "tx")}
              className="text-[9px] font-mono font-bold text-gray-500 hover:text-gray-900 transition-colors uppercase cursor-pointer"
            >
              {copiedField === "tx" ? "Copiado" : "Copiar"}
            </button>
          </div>
          <div className="mt-1 font-mono text-xs font-bold text-emerald-800 break-all">
            {shortTx}
          </div>
        </div>

        {/* Slot & Campaign */}
        <div className="grid grid-cols-2 gap-2 text-[10px] font-mono">
          <div className="rounded-lg bg-gray-50/50 p-2 border border-gray-100">
            <span className="text-gray-400 block text-[8px] uppercase">Slot On-Chain</span>
            <span className="font-bold text-gray-700">{certification.slot}</span>
          </div>
          <div className="rounded-lg bg-gray-50/50 p-2 border border-gray-100">
            <span className="text-gray-400 block text-[8px] uppercase">Campaña</span>
            <span className="font-bold text-gray-700">{certification.campaign}</span>
          </div>
        </div>
      </div>

      {/* Explorer Link CTA */}
      <div className="border-t border-gray-100 pt-3">
        <a
          href={certification.explorerUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="flex w-full items-center justify-center rounded-xl bg-gray-900 hover:bg-black text-white px-3 py-2 text-xs font-mono font-bold tracking-wider uppercase transition-all duration-150 cursor-pointer shadow-xs active:scale-[0.99]"
        >
          Ver en Solana Explorer
        </a>
      </div>
    </div>
  );
}
