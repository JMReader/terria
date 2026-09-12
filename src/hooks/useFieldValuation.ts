"use client";

import { useEffect, useRef, useState } from "react";
import { FieldItem } from "@/data/fieldsData";
import { LandValuation, ValuationSource } from "@/types/valuation";
import { fetchFieldValuation } from "@/lib/terriaApi";
import { computeDemoValuation } from "@/data/valuationMockData";

/**
 * Resuelve la proyección de valor del campo: intenta el endpoint real
 * `POST /v1/valuations/5yr` (standalone con centroide + hectáreas del
 * FieldItem) y cae a `computeDemoValuation` (réplica determinística de la
 * fórmula documentada) cuando el backend no responde — mismo patrón que
 * `useLiveTimelapseManifest`.
 *
 * Cachea por `field.id + años` y descarta respuestas viejas si el usuario
 * cambia de campo o mueve el horizonte rápido (race guard por requestId).
 */
export function useFieldValuation(field: FieldItem) {
  const [projectionYears, setProjectionYears] = useState(5);
  const [valuation, setValuation] = useState<LandValuation>(() =>
    computeDemoValuation(field, 5)
  );
  const [source, setSource] = useState<ValuationSource>("loading");

  const cacheRef = useRef(
    new Map<string, { valuation: LandValuation; source: "live" | "demo" }>()
  );
  const requestRef = useRef(0);

  useEffect(() => {
    const key = `${field.id}:${projectionYears}`;
    const cached = cacheRef.current.get(key);
    if (cached) {
      setValuation(cached.valuation);
      setSource(cached.source);
      return;
    }

    // Optimista: demo determinístico inmediato mientras resuelve la API.
    setValuation(computeDemoValuation(field, projectionYears));
    setSource("loading");

    const requestId = ++requestRef.current;
    const timer = setTimeout(() => {
      fetchFieldValuation({
        name: field.name,
        centroidLat: field.lat,
        centroidLon: field.lng,
        areaHectares: field.hectares,
        projectionYears,
      })
        .then((v) => {
          if (requestId !== requestRef.current) return;
          cacheRef.current.set(key, { valuation: v, source: "live" });
          setValuation(v);
          setSource("live");
        })
        .catch(() => {
          if (requestId !== requestRef.current) return;
          const v = computeDemoValuation(field, projectionYears);
          cacheRef.current.set(key, { valuation: v, source: "demo" });
          setValuation(v);
          setSource("demo");
        });
    }, 300);

    return () => clearTimeout(timer);
  }, [field, projectionYears]);

  return { valuation, source, projectionYears, setProjectionYears };
}
