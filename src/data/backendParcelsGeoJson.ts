import { FIELDS_DATA, FieldItem } from "./fieldsData";
import { FIELD_SECTORS_DATA, NEIGHBOR_CADASTRE_PARCELS, ParcelSector } from "./sectorsData";
import { ParcelGeoJsonFeature, ParcelsGeoJsonCollection } from "@/types/parcels";
import { TimelineState, TimelapseManifest } from "@/types/terria";

/**
 * Precision Agriculture 7-band NDVI Colormap
 * Matches Sentinel-2 / Landsat-8 precision agronomy standards (OneSoil / Climate FieldView)
 */
export function getNdviRampColor(ndvi: number): string {
  if (ndvi < 0.18) return "#c9b28a"; // Tierra / suelo desnudo / rastrojo seco
  if (ndvi < 0.30) return "#a9b183"; // Oliva claro / emergencia temprana
  if (ndvi < 0.45) return "#8a9a6b"; // Oliva / macollaje e inicio vegetativo
  if (ndvi < 0.60) return "#637e52"; // Verde transición / expansión foliar
  if (ndvi < 0.72) return "#4a6b46"; // Musgo / canopia cerrada
  if (ndvi < 0.85) return "#1c3a2e"; // Bosque / floración y pico de biomasa
  return "#12271e"; // Bosque profundo / máximo vigor fotosintético
}

/**
 * ERA5 Reanalysis Daily Temperature Color Ramp
 */
export function getTempRampColor(tempC: number): string {
  if (tempC < 18) return "#7ba7d9"; // Fresco (<18C) — cielo
  if (tempC < 24) return "#4a6b46"; // Óptimo agronómico (18-24C) — musgo
  if (tempC < 30) return "#c9b28a"; // Templado cálido (24-30C) — tierra
  return "#8f7550"; // Estrés térmico (>30C) — tierra profunda
}

/**
 * Biological growth curve simulation when direct observation is between scenes
 */
export function getSimulatedParcelNdvi(baseNdvi: number, crop: string, progress: number): number {
  const normProgress = Math.max(0, Math.min(1, progress));
  const cropLower = (crop || "").toLowerCase();

  if (cropLower.includes("maíz") || cropLower.includes("maiz")) {
    if (normProgress < 0.20) {
      return 0.28 + normProgress * 1.4;
    } else if (normProgress < 0.70) {
      return 0.56 + (normProgress - 0.20) * 0.60;
    } else {
      return 0.86 - (normProgress - 0.70) * 0.75;
    }
  } else if (cropLower.includes("soja")) {
    if (normProgress < 0.25) {
      return 0.26 + normProgress * 1.5;
    } else if (normProgress < 0.65) {
      return 0.63 + (normProgress - 0.25) * 0.52;
    } else {
      return 0.84 - (normProgress - 0.65) * 0.80;
    }
  } else if (cropLower.includes("trigo") || cropLower.includes("cebada")) {
    return Math.max(0.32, baseNdvi - normProgress * 0.35);
  } else {
    return Math.max(0.35, Math.min(0.85, baseNdvi + Math.sin(normProgress * Math.PI) * 0.12));
  }
}

/**
 * Helper to ensure a ring has strictly closed geometry with no consecutive duplicates
 */
function sanitizeRing(points: [number, number][]): number[][] {
  if (points.length < 3) return [];
  const clean: number[][] = [];

  for (let i = 0; i < points.length; i++) {
    const pt = points[i];
    const prev = clean[clean.length - 1];
    if (!prev || prev[0] !== pt[0] || prev[1] !== pt[1]) {
      clean.push([Number(pt[0].toFixed(6)), Number(pt[1].toFixed(6))]);
    }
  }

  // Ensure closed
  if (clean.length > 2) {
    const first = clean[0];
    const last = clean[clean.length - 1];
    if (first[0] !== last[0] || first[1] !== last[1]) {
      clean.push([first[0], first[1]]);
    }
  }

  return clean;
}

/**
 * Cleanly partitions a field bounding box into 3 agronomic crop strips
 * aligned with its geometric aspect ratio and real hectares.
 */
function computeFieldSectorRings(
  field: FieldItem,
  minLng: number,
  maxLng: number,
  minLat: number,
  maxLat: number
) {
  const dec = field.hectares && field.hectares < 10 ? 2 : 1;
  const latSpan = maxLat - minLat;
  const lngSpan = maxLng - minLng;

  if (latSpan >= lngSpan) {
    // Divided into 3 horizontal agronomic crop strips (Norte, Centro, Sur)
    const lat1 = Number((maxLat - latSpan * 0.42).toFixed(6));
    const lat2 = Number((minLat + latSpan * 0.28).toFixed(6));

    return [
      {
        id: `${field.id}-lote-1`,
        name: `Lote 1 (Norte) — ${field.primaryCrop || field.crop || "Maíz Tardío"}`,
        crop: field.primaryCrop || field.crop || "Maíz Tardío",
        hectares: Number(((field.hectares || 100) * 0.42).toFixed(dec)),
        baseNdvi: field.ndvi ?? 0.82,
        ring: sanitizeRing([
          [minLng, maxLat],
          [maxLng, maxLat],
          [maxLng, lat1],
          [minLng, lat1],
          [minLng, maxLat],
        ]),
      },
      {
        id: `${field.id}-lote-2`,
        name: "Lote 2 (Centro) — Soja de 1ra",
        crop: "Soja de 1ra",
        hectares: Number(((field.hectares || 100) * 0.30).toFixed(dec)),
        baseNdvi: Math.max(0.25, (field.ndvi ?? 0.82) - 0.05),
        ring: sanitizeRing([
          [minLng, lat1],
          [maxLng, lat1],
          [maxLng, lat2],
          [minLng, lat2],
          [minLng, lat1],
        ]),
      },
      {
        id: `${field.id}-lote-3`,
        name: "Lote 3 (Sur) — Trigo / Cobertura",
        crop: "Trigo / Cobertura",
        hectares: Number(((field.hectares || 100) * 0.28).toFixed(dec)),
        baseNdvi: Math.max(0.20, (field.ndvi ?? 0.82) - 0.12),
        ring: sanitizeRing([
          [minLng, lat2],
          [maxLng, lat2],
          [maxLng, minLat],
          [minLng, minLat],
          [minLng, lat2],
        ]),
      },
    ];
  } else {
    // Divided into 3 vertical agronomic crop strips (Oeste, Centro, Este)
    const lng1 = Number((minLng + lngSpan * 0.42).toFixed(6));
    const lng2 = Number((maxLng - lngSpan * 0.28).toFixed(6));

    return [
      {
        id: `${field.id}-lote-1`,
        name: `Lote 1 (Oeste) — ${field.primaryCrop || field.crop || "Maíz Tardío"}`,
        crop: field.primaryCrop || field.crop || "Maíz Tardío",
        hectares: Number(((field.hectares || 100) * 0.42).toFixed(dec)),
        baseNdvi: field.ndvi ?? 0.82,
        ring: sanitizeRing([
          [minLng, maxLat],
          [lng1, maxLat],
          [lng1, minLat],
          [minLng, minLat],
          [minLng, maxLat],
        ]),
      },
      {
        id: `${field.id}-lote-2`,
        name: "Lote 2 (Centro) — Soja de 1ra",
        crop: "Soja de 1ra",
        hectares: Number(((field.hectares || 100) * 0.30).toFixed(dec)),
        baseNdvi: Math.max(0.25, (field.ndvi ?? 0.82) - 0.05),
        ring: sanitizeRing([
          [lng1, maxLat],
          [lng2, maxLat],
          [lng2, minLat],
          [lng1, minLat],
          [lng1, maxLat],
        ]),
      },
      {
        id: `${field.id}-lote-3`,
        name: "Lote 3 (Este) — Trigo / Cobertura",
        crop: "Trigo / Cobertura",
        hectares: Number(((field.hectares || 100) * 0.28).toFixed(dec)),
        baseNdvi: Math.max(0.20, (field.ndvi ?? 0.82) - 0.12),
        ring: sanitizeRing([
          [lng2, maxLat],
          [maxLng, maxLat],
          [maxLng, minLat],
          [lng2, minLat],
          [lng2, maxLat],
        ]),
      },
    ];
  }
}

/**
 * Generate PostGIS-compliant GeoJSON FeatureCollection dynamically evaluated
 * for the current calendar date in the Sentinel-2 timelapse.
 */
export function generateParcelsGeoJson(
  selectedDate: string = "2024-01-01",
  activeLayer: "rgb" | "ndvi" | "weather" = "ndvi",
  targetFieldId?: string,
  fieldsList?: FieldItem[],
  timelineState?: TimelineState | null,
  manifest?: TimelapseManifest | null
): ParcelsGeoJsonCollection {
  const fields = fieldsList && fieldsList.length > 0 ? fieldsList : FIELDS_DATA;

  // 1. Resolve timeline progress
  let timelineProgress = 0.5;
  if (manifest?.weatherDaily && manifest.weatherDaily.length > 1) {
    const dates = manifest.weatherDaily.map((w) => w.date);
    const idx = dates.indexOf(selectedDate);
    if (idx !== -1) {
      timelineProgress = idx / (dates.length - 1);
    }
  }

  // 2. Resolve weather from timeline
  let activeTemp = 24.5;
  let activeRain = 0.0;
  if (timelineState?.weather) {
    const tMax = timelineState.weather.temperatureMax?.value;
    const tMin = timelineState.weather.temperatureMin?.value;
    if (tMax != null && tMin != null) activeTemp = Number(((tMax + tMin) / 2).toFixed(1));
    else if (tMax != null) activeTemp = Number(tMax.toFixed(1));
    const rain = timelineState.weather.precipitationDay?.value;
    if (rain != null) activeRain = Number(rain.toFixed(1));
  } else if (manifest?.weatherDaily) {
    const w = manifest.weatherDaily.find((entry) => entry.date === selectedDate);
    if (w) {
      const tMax = w.temperatureMax?.value;
      const tMin = w.temperatureMin?.value;
      if (tMax != null && tMin != null) activeTemp = Number(((tMax + tMin) / 2).toFixed(1));
      if (w.precipitationDay?.value != null) activeRain = Number(w.precipitationDay.value.toFixed(1));
    }
  }

  // 3. Resolve direct satellite NDVI from backend frame
  let backendObservedNdvi: number | null = null;
  let backendObservationDate: string | null = null;
  let isFreshSatellite = false;

  if (timelineState?.satellite && timelineState.satellite.usable) {
    const meanVal = timelineState.satellite.ndvi?.mean?.value;
    if (typeof meanVal === "number" && !isNaN(meanVal)) {
      backendObservedNdvi = meanVal;
      backendObservationDate = timelineState.satellite.localDate;
      isFreshSatellite = timelineState.isFresh;
    }
  }

  const features: ParcelGeoJsonFeature[] = [];

  // 4. Process Portfolio Fields (Both macro perimeter AND internal agricultural parcels)
  fields.forEach((field) => {
    const isTarget = targetFieldId ? field.id === targetFieldId : true;
    const staticSectors = FIELD_SECTORS_DATA[field.id];

    // A. Build Macro Field Boundary (Outer Perimeter)
    let outerBoundaryRing: number[][] = [];
    const radiusDeg = Math.max(0.003, Math.min(0.025, Math.sqrt((field.hectares || 100) * 0.0001) * 0.65));
    let minLng = field.lng - radiusDeg * 1.1;
    let maxLng = field.lng + radiusDeg * 1.1;
    let minLat = field.lat - radiusDeg * 0.9;
    let maxLat = field.lat + radiusDeg * 0.9;

    const boundaryRing = field.boundary?.coordinates?.[0];
    if (boundaryRing && boundaryRing.length >= 3) {
      const bCoords = boundaryRing;
      const pts: [number, number][] = bCoords.map((c: number[]) => [c[0], c[1]]);
      outerBoundaryRing = sanitizeRing(pts);

      // Compute bounding box
      const lngs = bCoords.map((c: number[]) => c[0]);
      const lats = bCoords.map((c: number[]) => c[1]);
      minLng = Math.min(...lngs);
      maxLng = Math.max(...lngs);
      minLat = Math.min(...lats);
      maxLat = Math.max(...lats);
    } else if (staticSectors && staticSectors.length > 0) {
      const allLats: number[] = [];
      const allLngs: number[] = [];
      staticSectors.forEach((s) => {
        s.offsets.forEach(([dLat, dLng]) => {
          allLats.push(field.lat + dLat);
          allLngs.push(field.lng + dLng);
        });
      });
      minLng = Math.min(...allLngs);
      maxLng = Math.max(...allLngs);
      minLat = Math.min(...allLats);
      maxLat = Math.max(...allLats);

      outerBoundaryRing = sanitizeRing([
        [minLng, maxLat],
        [maxLng, maxLat],
        [maxLng, minLat],
        [minLng, minLat],
        [minLng, maxLat],
      ]);
    } else {
      outerBoundaryRing = sanitizeRing([
        [minLng, maxLat],
        [maxLng, maxLat],
        [maxLng, minLat],
        [minLng, minLat],
        [minLng, maxLat],
      ]);
    }

    // Add perimeter feature (Used for field-perimeter-line and active glowing halo)
    if (outerBoundaryRing.length >= 4) {
      features.push({
        type: "Feature",
        id: `${field.id}-perimeter`,
        properties: {
          id: `${field.id}-perimeter`,
          fieldId: field.id,
          fieldName: field.name,
          name: `${field.name} — Perímetro Catastral`,
          crop: field.primaryCrop || field.crop || "Establecimiento",
          variety: "Límite perimetral",
          hectares: field.hectares,
          isPortfolio: true,
          isPerimeter: true,
          kind: "perimeter",
          baseColor: "#1c3a2e",
          color: "#1c3a2e",
          currentNdvi: parseFloat((field.ndvi ?? 0.72).toFixed(2)),
          currentTemp: activeTemp,
          currentRain: activeRain,
          statusLabel: "Límite catastral verificado",
          selectedDate,
          isFreshSatellite,
        },
        geometry: {
          type: "Polygon",
          coordinates: [outerBoundaryRing],
        },
      });
    }

    // B. Build Internal Agronomic Parcels (Hectares / Management Zones)
    const midLng = Number(((minLng + maxLng) / 2).toFixed(6));
    const midLat = Number(((minLat + maxLat) / 2).toFixed(6));

    let sectorRings: { id: string; name: string; crop: string; hectares: number; baseNdvi: number; ring: number[][] }[] = [];

    if (staticSectors && staticSectors.length > 0) {
      sectorRings = staticSectors.map((s) => ({
        id: s.id,
        name: s.name,
        crop: s.crop,
        hectares: s.hectares,
        baseNdvi: s.ndvi,
        ring: sanitizeRing(s.offsets.map(([dLat, dLng]) => [field.lng + dLng, field.lat + dLat])),
      }));
    } else {
      sectorRings = computeFieldSectorRings(field, minLng, maxLng, minLat, maxLat);
    }

    sectorRings.forEach((sec, sIdx) => {
      if (sec.ring.length < 4) return;

      // Calculate dynamic NDVI for this sector
      let parcelNdvi = sec.baseNdvi;
      let statusText = "En vegetación activa";

      if (backendObservedNdvi != null && isTarget) {
        const sectorVariance = sIdx === 0 ? 1.02 : sIdx === 1 ? 0.98 : 0.94;
        parcelNdvi = Math.max(0.12, Math.min(0.95, backendObservedNdvi * sectorVariance));

        if (parcelNdvi > 0.75) {
          statusText = `Pico de biomasa (Satélite ${backendObservationDate || selectedDate})`;
        } else if (parcelNdvi > 0.55) {
          statusText = `Desarrollo vegetativo vigoroso (Satélite ${backendObservationDate || selectedDate})`;
        } else if (parcelNdvi > 0.35) {
          statusText = `Crecimiento inicial / Macollaje (Satélite ${backendObservationDate || selectedDate})`;
        } else {
          statusText = `Emergencia / Rastrojo (Satélite ${backendObservationDate || selectedDate})`;
        }
      } else {
        parcelNdvi = getSimulatedParcelNdvi(sec.baseNdvi, sec.crop, timelineProgress);
        if (parcelNdvi > 0.75) statusText = "Pico vegetativo / Floración";
        else if (parcelNdvi > 0.55) statusText = "Desarrollo de biomasa foliar";
        else if (parcelNdvi > 0.35) statusText = "Emergencia y macollaje";
        else statusText = "Emergencia temprana / Rastrojo";
      }

      let activeColor = getNdviRampColor(parcelNdvi);
      if (activeLayer === "weather") {
        activeColor = getTempRampColor(activeTemp);
        statusText = activeRain > 5 ? `Lluvia acumulada ${activeRain} mm` : `Temperatura ${activeTemp}°C`;
      }

      features.push({
        type: "Feature",
        id: sec.id,
        properties: {
          id: sec.id,
          fieldId: field.id,
          fieldName: field.name,
          name: sec.name,
          crop: sec.crop,
          variety: "Híbrido Certificado",
          hectares: sec.hectares,
          soilHorizon: field.soilSeries || field.soilType || "Suelo Clase II",
          isPortfolio: true,
          isPerimeter: false,
          kind: "lot",
          baseColor: activeColor,
          color: activeColor,
          currentNdvi: parseFloat(parcelNdvi.toFixed(2)),
          currentTemp: activeTemp,
          currentRain: activeRain,
          statusLabel: statusText,
          selectedDate,
          isFreshSatellite,
        },
        geometry: {
          type: "Polygon",
          coordinates: [sec.ring],
        },
      });
    });
  });

  // 5. Process Surrounding Neighbor Cadastral Parcels (Context)
  NEIGHBOR_CADASTRE_PARCELS.forEach((cad) => {
    const field = fields.find((f) => f.id === cad.fieldId);
    if (!field) return;

    const ring = sanitizeRing(cad.offsets.map(([dLat, dLng]) => [field.lng + dLng, field.lat + dLat]));
    if (ring.length < 4) return;

    const neighborNdvi = getSimulatedParcelNdvi(0.55, cad.crop || "Soja", timelineProgress);
    let activeColor = cad.color;
    if (activeLayer === "ndvi") {
      activeColor = getNdviRampColor(neighborNdvi);
    } else if (activeLayer === "weather") {
      activeColor = getTempRampColor(activeTemp);
    }

    features.push({
      type: "Feature",
      id: cad.id,
      properties: {
        id: cad.id,
        fieldId: cad.fieldId,
        fieldName: field.name,
        name: cad.name,
        crop: cad.crop || "Cultivo lindero",
        variety: "Zona rural vecina",
        hectares: cad.hectares,
        isPortfolio: false,
        isPerimeter: false,
        kind: "neighbor",
        baseColor: cad.color,
        color: activeColor,
        currentNdvi: parseFloat(neighborNdvi.toFixed(2)),
        currentTemp: activeTemp,
        currentRain: activeRain,
        statusLabel: "Lote vecino lindero",
        selectedDate,
      },
      geometry: {
        type: "Polygon",
        coordinates: [ring],
      },
    });
  });

  return {
    type: "FeatureCollection",
    features,
  };
}

export interface CalculatedLotInfo {
  id: string;
  name: string;
  crop: string;
  hectares: number;
  percent: number;
  ndvi: number;
  color: string;
  statusLabel: string;
  centroid: [number, number]; // [lng, lat]
}

/**
 * Returns structured breakdown of lots/hectares for a field,
 * reactive to the current timeline satellite NDVI or seasonal curve.
 */
export function getFieldLotBreakdown(
  field: FieldItem | null | undefined,
  timelineState?: TimelineState,
  selectedDate?: string
): CalculatedLotInfo[] {
  if (!field) return [];

  const staticSectors = FIELD_SECTORS_DATA[field.id];
  let sectorRings: { id: string; name: string; crop: string; hectares: number; baseNdvi: number; ring: number[][] }[] = [];

  const radiusDeg = Math.max(0.003, Math.min(0.025, Math.sqrt((field.hectares || 100) * 0.0001) * 0.65));
  let minLng = field.lng - radiusDeg * 1.1;
  let maxLng = field.lng + radiusDeg * 1.1;
  let minLat = field.lat - radiusDeg * 0.9;
  let maxLat = field.lat + radiusDeg * 0.9;

  const boundaryRing = field.boundary?.coordinates?.[0];
  if (boundaryRing && boundaryRing.length >= 3) {
    const lngs = boundaryRing.map((c: number[]) => c[0]);
    const lats = boundaryRing.map((c: number[]) => c[1]);
    minLng = Math.min(...lngs);
    maxLng = Math.max(...lngs);
    minLat = Math.min(...lats);
    maxLat = Math.max(...lats);
  }

  const midLng = Number(((minLng + maxLng) / 2).toFixed(6));
  const midLat = Number(((minLat + maxLat) / 2).toFixed(6));

  if (staticSectors && staticSectors.length > 0) {
    sectorRings = staticSectors.map((s) => ({
      id: s.id,
      name: s.name,
      crop: s.crop,
      hectares: s.hectares,
      baseNdvi: s.ndvi,
      ring: sanitizeRing(s.offsets.map(([dLat, dLng]) => [field.lng + dLng, field.lat + dLat])),
    }));
  } else {
    sectorRings = computeFieldSectorRings(field, minLng, maxLng, minLat, maxLat);
  }

  const totalHectares = sectorRings.reduce((acc, s) => acc + s.hectares, 0) || field.hectares || 100;

  // Resolve satellite NDVI if available
  let backendObservedNdvi: number | null = null;
  if (timelineState?.satellite && timelineState.satellite.usable) {
    const meanVal = timelineState.satellite.ndvi?.mean?.value;
    if (typeof meanVal === "number" && !isNaN(meanVal)) {
      backendObservedNdvi = meanVal;
    }
  }

  return sectorRings.map((sec, sIdx) => {
    // Calculate centroid
    const cLng = sec.ring.reduce((acc, pt) => acc + pt[0], 0) / (sec.ring.length || 1);
    const cLat = sec.ring.reduce((acc, pt) => acc + pt[1], 0) / (sec.ring.length || 1);

    let parcelNdvi = sec.baseNdvi;
    let statusLabel = "Vegetación activa";

    if (backendObservedNdvi != null) {
      const sectorVariance = sIdx === 0 ? 1.02 : sIdx === 1 ? 0.98 : 0.94;
      parcelNdvi = Math.max(0.12, Math.min(0.95, backendObservedNdvi * sectorVariance));
      statusLabel = parcelNdvi > 0.75 ? "Pico fotosintético" : parcelNdvi > 0.50 ? "Desarrollo vegetativo" : "Emergencia";
    } else {
      parcelNdvi = getSimulatedParcelNdvi(sec.baseNdvi, sec.crop, 0.5);
      statusLabel = parcelNdvi > 0.75 ? "Floración óptima" : parcelNdvi > 0.50 ? "Crecimiento foliar" : "Emergencia";
    }

    return {
      id: sec.id,
      name: sec.name,
      crop: sec.crop,
      hectares: sec.hectares,
      percent: Math.round((sec.hectares / totalHectares) * 100),
      ndvi: parseFloat(parcelNdvi.toFixed(2)),
      color: getNdviRampColor(parcelNdvi),
      statusLabel,
      centroid: [Number(cLng.toFixed(6)), Number(cLat.toFixed(6))],
    };
  });
}
