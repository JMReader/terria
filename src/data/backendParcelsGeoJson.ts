import { FIELDS_DATA, FieldItem } from "./fieldsData";
import { FIELD_SECTORS_DATA, NEIGHBOR_CADASTRE_PARCELS, ParcelSector } from "./sectorsData";
import { ParcelGeoJsonFeature, ParcelsGeoJsonCollection } from "@/types/parcels";
import { TimelineState, TimelapseManifest } from "@/types/terria";

/**
 * Precision Agriculture 7-band NDVI Colormap
 * Matches Sentinel-2 / Landsat-8 precision agronomy standards (OneSoil / Climate FieldView)
 */
export function getNdviRampColor(ndvi: number): string {
  if (ndvi < 0.18) return "#b45309"; // Ocre / suelo desnudo / rastrojo seco
  if (ndvi < 0.30) return "#eab308"; // Amarillo dorado / emergencia temprana
  if (ndvi < 0.45) return "#84cc16"; // Verde lima / macollaje e inicio vegetativo
  if (ndvi < 0.60) return "#22c55e"; // Verde esmeralda / expansión foliar
  if (ndvi < 0.72) return "#16a34a"; // Verde intenso / canopia cerrada
  if (ndvi < 0.85) return "#15803d"; // Verde bosque vivo / floración y pico de biomasa
  return "#14532d"; // Verde profundo / máximo vigor fotosintético
}

/**
 * ERA5 Reanalysis Daily Temperature Color Ramp
 */
export function getTempRampColor(tempC: number): string {
  if (tempC < 18) return "#38bdf8"; // Fresco (<18C)
  if (tempC < 24) return "#34d399"; // Óptimo agronómico (18-24C)
  if (tempC < 30) return "#fbbf24"; // Templado cálido (24-30C)
  return "#f97316"; // Estrés térmico (>30C)
}

/**
 * Biological growth curve simulation when direct observation is between scenes
 */
export function getSimulatedParcelNdvi(baseNdvi: number, crop: string, progress: number): number {
  const normProgress = Math.max(0, Math.min(1, progress));
  const cropLower = (crop || "").toLowerCase();

  if (cropLower.includes("maíz") || cropLower.includes("maiz")) {
    // Summer corn: emergence 0.28 -> rapid tillering -> peak 0.86 at day ~45 -> dry down
    if (normProgress < 0.20) {
      return 0.28 + normProgress * 1.4;
    } else if (normProgress < 0.70) {
      return 0.56 + (normProgress - 0.20) * 0.60;
    } else {
      return 0.86 - (normProgress - 0.70) * 0.75;
    }
  } else if (cropLower.includes("soja")) {
    // First crop soybean: emergence 0.26 -> rapid canopy closure -> peak 0.84 -> maturation
    if (normProgress < 0.25) {
      return 0.26 + normProgress * 1.5;
    } else if (normProgress < 0.65) {
      return 0.63 + (normProgress - 0.25) * 0.52;
    } else {
      return 0.84 - (normProgress - 0.65) * 0.80;
    }
  } else if (cropLower.includes("trigo") || cropLower.includes("cebada")) {
    // Winter small grains
    return Math.max(0.32, baseNdvi - normProgress * 0.35);
  } else {
    // General pasture or native cover
    return Math.max(0.35, Math.min(0.85, baseNdvi + Math.sin(normProgress * Math.PI) * 0.12));
  }
}

/**
 * Fallback sector generator for dynamic fields (e.g. from backend database)
 * Subdivides field center/bounds into 3 realistic cadastral parcels
 */
function generateDynamicSectorsForField(field: FieldItem): ParcelSector[] {
  const lat = field.lat;
  const lng = field.lng;
  const crop = field.primaryCrop || field.crop || "Maíz";

  return [
    {
      id: `${field.id}-lote-1`,
      name: `Lote 1 — ${crop}`,
      hectares: Math.round(field.hectares * 0.45 * 10) / 10,
      crop: crop,
      variety: "Híbrido Premium",
      ndvi: field.ndvi ?? 0.72,
      moisturePercent: 82,
      expectedYield: "95 qq/ha",
      soilHorizon: field.soilSeries || field.soilType || "Suelo Agrícola Clase II",
      color: "#16a34a",
      offsets: [
        [0.0055, -0.0065],
        [0.0055, 0.0045],
        [0.0005, 0.0045],
        [0.0005, -0.0065],
        [0.0055, -0.0065],
      ],
    },
    {
      id: `${field.id}-lote-2`,
      name: "Lote 2 — Soja 1ra",
      hectares: Math.round(field.hectares * 0.35 * 10) / 10,
      crop: "Soja 1ra",
      variety: "Enlist E3",
      ndvi: Math.max(0.35, (field.ndvi ?? 0.72) - 0.05),
      moisturePercent: 78,
      expectedYield: "42 qq/ha",
      soilHorizon: "Horizonte superficial profundo",
      color: "#eab308",
      offsets: [
        [0.0000, -0.0065],
        [0.0000, -0.0010],
        [-0.0060, -0.0010],
        [-0.0060, -0.0065],
        [0.0000, -0.0065],
      ],
    },
    {
      id: `${field.id}-lote-3`,
      name: "Lote 3 — Trigo / Rotación",
      hectares: Math.round(field.hectares * 0.20 * 10) / 10,
      crop: "Rotación",
      variety: "Ciclo Intermedio",
      ndvi: Math.max(0.30, (field.ndvi ?? 0.72) - 0.12),
      moisturePercent: 74,
      expectedYield: "38 qq/ha",
      soilHorizon: "Suelo fértil bien drenado",
      color: "#84cc16",
      offsets: [
        [0.0000, -0.0005],
        [0.0000, 0.0045],
        [-0.0060, 0.0045],
        [-0.0060, -0.0005],
        [0.0000, -0.0005],
      ],
    },
  ];
}

/**
 * Generate PostGIS-compliant GeoJSON FeatureCollection dynamically evaluated
 * for the current calendar date in the Sentinel-2 timelapse.
 * Directly integrates real backend frames and weather series!
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

  // Determine timeline date and progress (e.g. between manifest start and end)
  let timelineProgress = 0.5;
  if (manifest && manifest.weatherDaily && manifest.weatherDaily.length > 1) {
    const dates = manifest.weatherDaily.map((w) => w.date);
    const idx = dates.indexOf(selectedDate);
    if (idx !== -1) {
      timelineProgress = idx / (dates.length - 1);
    }
  } else {
    // Fallback: day of year in Jan-Mar window
    try {
      const d = new Date(selectedDate);
      const day = Math.min(90, Math.max(1, d.getDate() + (d.getMonth() * 30)));
      timelineProgress = day / 90;
    } catch {
      timelineProgress = 0.5;
    }
  }

  // 1. Resolve active weather from timelineState or manifest
  let activeTemp = 24.5;
  let activeRain = 0.0;
  if (timelineState?.weather) {
    const tMax = timelineState.weather.temperatureMax?.value;
    const tMin = timelineState.weather.temperatureMin?.value;
    if (tMax != null && tMin != null) {
      activeTemp = Number(((tMax + tMin) / 2).toFixed(1));
    } else if (tMax != null) {
      activeTemp = Number(tMax.toFixed(1));
    }
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

  // 2. Resolve direct satellite NDVI from backend frame
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

  // 3. Process Neighbor Cadastral Parcels (OneSoil Cadastre context)
  NEIGHBOR_CADASTRE_PARCELS.forEach((cad) => {
    const field = fields.find((f) => f.id === cad.fieldId) || FIELDS_DATA.find((f) => f.id === cad.fieldId);
    if (!field) return;

    const ring = cad.offsets.map(([dLat, dLng]) => [
      parseFloat((field.lng + dLng).toFixed(6)),
      parseFloat((field.lat + dLat).toFixed(6)),
    ]);
    if (ring.length > 0) {
      ring.push([ring[0][0], ring[0][1]]); // close polygon
    }

    const neighborNdvi = getSimulatedParcelNdvi(0.58, cad.crop || "Soja", timelineProgress);

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
        isPortfolio: false, // Not selectable
        baseColor: cad.color,
        color: activeColor,
        currentNdvi: parseFloat(neighborNdvi.toFixed(2)),
        currentTemp: activeTemp,
        currentRain: activeRain,
        statusLabel: "Lote vecino lindero",
      },
      geometry: {
        type: "Polygon",
        coordinates: [ring],
      },
    });
  });

  // 4. Process Active Portfolio Fields (Subdivided into agronomic parcels)
  fields.forEach((field) => {
    let sectors = FIELD_SECTORS_DATA[field.id];
    if (!sectors || sectors.length === 0) {
      sectors = generateDynamicSectorsForField(field);
    }

    sectors.forEach((sec, sIdx) => {
      const ring = sec.offsets.map(([dLat, dLng]) => [
        parseFloat((field.lng + dLng).toFixed(6)),
        parseFloat((field.lat + dLat).toFixed(6)),
      ]);
      if (ring.length > 0) {
        ring.push([ring[0][0], ring[0][1]]); // close polygon
      }

      // Calculate dynamic NDVI for this sector
      let parcelNdvi = sec.ndvi;
      let statusText = "En vegetación activa";

      if (backendObservedNdvi != null && (targetFieldId ? field.id === targetFieldId : true)) {
        // Apply backend satellite observation with slight intra-field sector variance
        const sectorVariance = sIdx === 0 ? 1.02 : sIdx === 1 ? 0.98 : 0.95;
        parcelNdvi = Math.max(0.12, Math.min(0.95, backendObservedNdvi * sectorVariance));

        if (parcelNdvi > 0.75) {
          statusText = `Pico de biomasa (Satélite ${backendObservationDate || selectedDate})`;
        } else if (parcelNdvi > 0.55) {
          statusText = `Desarrollo vegetativo vigoroso (Satélite ${backendObservationDate || selectedDate})`;
        } else if (parcelNdvi > 0.35) {
          statusText = `Crecimiento inicial / Macollaje (Satélite ${backendObservationDate || selectedDate})`;
        } else {
          statusText = `Emergencia / Suelo con rastrojo (Satélite ${backendObservationDate || selectedDate})`;
        }
      } else {
        // Biological simulation based on timeline date
        parcelNdvi = getSimulatedParcelNdvi(sec.ndvi, sec.crop, timelineProgress);
        if (parcelNdvi > 0.75) statusText = "Pico vegetativo / Floración";
        else if (parcelNdvi > 0.55) statusText = "Desarrollo de biomasa foliar";
        else if (parcelNdvi > 0.35) statusText = "Emergencia y macollaje";
        else statusText = "Emergencia temprana / Rastrojo";
      }

      let activeColor = sec.color;
      if (activeLayer === "ndvi") {
        activeColor = getNdviRampColor(parcelNdvi);
      } else if (activeLayer === "weather") {
        activeColor = getTempRampColor(activeTemp);
        statusText = activeRain > 10 ? `Lluvia acumulada ${activeRain} mm` : `Temperatura ${activeTemp}°C`;
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
          variety: sec.variety,
          hectares: sec.hectares,
          soilHorizon: sec.soilHorizon,
          isPortfolio: true, // Interactive and selectable!
          baseColor: sec.color,
          color: activeColor,
          currentNdvi: parseFloat(parcelNdvi.toFixed(2)),
          currentTemp: activeTemp,
          currentRain: activeRain,
          statusLabel: statusText,
          selectedDate: selectedDate,
          isFreshSatellite,
        },
        geometry: {
          type: "Polygon",
          coordinates: [ring],
        },
      });
    });
  });

  return {
    type: "FeatureCollection",
    features,
  };
}
