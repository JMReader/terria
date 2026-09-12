"use client";

import { useState, useEffect, useRef, useMemo, useCallback } from "react";
import { FieldItem } from "@/data/fieldsData";
import {
  WhatIfSimulation,
  WhatIfSource,
  detectFieldDefaultCrop,
  checkYearDataAvailability,
  YearDataAvailability,
} from "@/types/whatIf";
import { fetchFieldWhatIf, fetchStandaloneWhatIf } from "@/lib/terriaApi";
import { computeDemoWhatIf } from "@/data/whatIfMockData";

export interface UseFieldWhatIfOptions {
  initialYear?: number;
  initialRealCrop?: string;
  initialRealMargin?: number;
}

export function useFieldWhatIf(
  field: FieldItem,
  options: UseFieldWhatIfOptions = {}
) {
  // Detección automática desde datos del campo (Supabase / local store)
  const defaultCrop = useMemo(
    () => options.initialRealCrop ?? detectFieldDefaultCrop(field.primaryCrop || field.crop),
    [options.initialRealCrop, field.primaryCrop, field.crop]
  );

  const defaultMargin = useMemo(
    () => options.initialRealMargin ?? (field.rentUsdHa ?? 350.0),
    [options.initialRealMargin, field.rentUsdHa]
  );

  const [targetYear, setTargetYear] = useState<number>(options.initialYear ?? 2023);
  const [realCrop, setRealCrop] = useState<string>(defaultCrop);
  const [realMarginUsdHa, setRealMarginUsdHa] = useState<number>(defaultMargin);
  const [selectedCropId, setSelectedCropId] = useState<string | null>(null);

  // Sincronizar si cambia el campo seleccionado
  useEffect(() => {
    setRealCrop(defaultCrop);
    setRealMarginUsdHa(defaultMargin);
  }, [field.id, defaultCrop, defaultMargin]);

  // Chequeo de disponibilidad satelital para el año ingresado
  const availability: YearDataAvailability = useMemo(
    () => checkYearDataAvailability(targetYear),
    [targetYear]
  );

  const [simulation, setSimulation] = useState<WhatIfSimulation>(() =>
    computeDemoWhatIf(field, targetYear, realCrop, realMarginUsdHa)
  );
  const [source, setSource] = useState<WhatIfSource>("loading");

  const cacheRef = useRef<
    Map<string, { simulation: WhatIfSimulation; source: "live" | "demo" }>
  >(new Map());

  const resetToFieldDefaults = useCallback(() => {
    setRealCrop(defaultCrop);
    setRealMarginUsdHa(defaultMargin);
    setTargetYear(2023);
  }, [defaultCrop, defaultMargin]);

  useEffect(() => {
    let active = true;
    const safeYear = Math.max(2015, Math.min(2030, targetYear || 2023));
    const safeMargin = Math.max(0, realMarginUsdHa || 350);
    const cacheKey = `${field.id}-${safeYear}-${realCrop}-${safeMargin}`;

    const cached = cacheRef.current.get(cacheKey);
    if (cached) {
      setSimulation(cached.simulation);
      setSource(cached.source);
      return;
    }

    setSource("loading");

    async function load() {
      try {
        let res: WhatIfSimulation;
        const isUuid =
          /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(
            field.id
          );

        if (isUuid) {
          res = await fetchFieldWhatIf(field.id, {
            targetYear: safeYear,
            realCrop,
            realMarginUsdHa: safeMargin,
            includeAudit: true,
          });
        } else {
          res = await fetchStandaloneWhatIf({
            name: field.name,
            centroidLat: field.lat,
            centroidLon: field.lng,
            areaHectares: field.hectares,
            targetYear: safeYear,
            realCrop,
            realMarginUsdHa: safeMargin,
            includeAudit: true,
          });
        }

        if (!active) return;
        cacheRef.current.set(cacheKey, { simulation: res, source: "live" });
        setSimulation(res);
        setSource("live");
      } catch {
        if (!active) return;
        const fallback = computeDemoWhatIf(
          field,
          safeYear,
          realCrop,
          safeMargin
        );
        cacheRef.current.set(cacheKey, { simulation: fallback, source: "demo" });
        setSimulation(fallback);
        setSource("demo");
      }
    }

    // Debounce de 300ms para entrada numérica libre sin saturar la red
    const timer = setTimeout(load, 300);

    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [field.id, field.name, field.lat, field.lng, field.hectares, targetYear, realCrop, realMarginUsdHa]);

  const isFieldPreloaded = Boolean(field.primaryCrop || field.rentUsdHa);

  return {
    simulation,
    source,
    targetYear,
    setTargetYear,
    realCrop,
    setRealCrop,
    realMarginUsdHa,
    setRealMarginUsdHa,
    selectedCropId,
    setSelectedCropId,
    availability,
    isFieldPreloaded,
    resetToFieldDefaults,
  };
}
