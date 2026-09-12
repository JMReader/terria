import React from "react";

export interface SectionHeadingProps {
  /** kicker mono en mayúsculas (voz data) */
  kicker: string;
  /** titular serif (voz editorial) */
  title: React.ReactNode;
  description?: React.ReactNode;
  tone?: "dark" | "light";
  align?: "left" | "center";
  className?: string;
}

/** Cabecera editorial de sección: kicker mono + titular serif + bajada. */
export default function SectionHeading({
  kicker,
  title,
  description,
  tone = "dark",
  align = "left",
  className = "",
}: SectionHeadingProps) {
  const kickerColor = tone === "light" ? "text-tierra" : "text-musgo";
  const titleColor = tone === "light" ? "text-nube" : "text-bosque";
  const descColor = tone === "light" ? "text-nube/70" : "text-bosque/70";
  const alignCls = align === "center" ? "text-center items-center" : "text-left items-start";

  return (
    <div className={`flex flex-col gap-3 ${alignCls} ${className}`}>
      <span
        className={`font-mono text-[11px] font-bold uppercase tracking-[0.3em] ${kickerColor}`}
      >
        {kicker}
      </span>
      <h2
        className={`font-display text-3xl sm:text-4xl lg:text-5xl font-medium leading-[1.05] tracking-tight ${titleColor}`}
      >
        {title}
      </h2>
      {description && (
        <p className={`max-w-xl text-sm sm:text-base leading-relaxed ${descColor}`}>
          {description}
        </p>
      )}
    </div>
  );
}
