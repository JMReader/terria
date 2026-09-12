import { FIELDS_DATA } from "./fieldsData";
import { FIELD_SECTORS_DATA, NEIGHBOR_CADASTRE_PARCELS } from "./sectorsData";
import { ParcelGeoJsonFeature, ParcelsGeoJsonCollection } from "@/types/parcels";

// Helper to interpolate colors along an NDVI ramp
export function getNdviRampColor(ndvi: number): string {
  if (ndvi < 0.35) return "#fef08a"; // Soft straw / early emergence
  if (ndvi < 0.50) return "#bef264"; // Pale lime / early tillering
  if (ndvi < 0.65) return "#84cc16"; // Bright green / vegetative expansion
  if (ndvi < 0.78) return "#22c55e"; // Rich vibrant green / canopy closure
  return "#15803d"; // Deep forest emerald / peak vigor (silking/flowering)
}

// Helper to interpolate temperature colors (ERA5 reanalysis)
export function getTempRampColor(tempC: number): string {
  if (tempC < 22) return "#38bdf8"; // Cool cyan (<22C)
  if (tempC < 27) return "#34d399"; // Moderate emerald (22-27C)
  if (tempC < 32) return "#fbbf24"; // Warm amber (27-32C)
  return "#f97316"; // High heat stress orange (>32C)
}

// Simulate biological growth curve for date progress (Jan 1 to Mar 1 = 60 days)
export function getSimulatedParcelNdvi(baseNdvi: number, crop: string, dayIndex: number): number {
  const progress = Math.max(0, Math.min(1, dayIndex / 59)); // 0 to 1
  const cropLower = crop.toLowerCase();

  if (cropLower.includes("maíz") || cropLower.includes("maiz")) {
    // Summer corn: emergence 0.30 -> peak 0.88 at day 44 -> 0.82
    if (progress < 0.25) {
      return 0.32 + progress * 1.3;
    } else if (progress < 0.75) {
      return 0.64 + (progress - 0.25) * 0.48;
    } else {
      return 0.88 - (progress - 0.75) * 0.25;
    }
  } else if (cropLower.includes("soja")) {
    // First crop soybean: emergence 0.28 -> rapid vegetative -> peak 0.86 at day 40
    if (progress < 0.30) {
      return 0.28 + progress * 1.4;
    } else if (progress < 0.70) {
      return 0.70 + (progress - 0.30) * 0.40;
    } else {
      return 0.86 - (progress - 0.70) * 0.35;
    }
  } else if (cropLower.includes("trigo") || cropLower.includes("cebada") || cropLower.includes("papa")) {
    // Mature winter grain or tuber
    return Math.max(0.38, baseNdvi - progress * 0.25);
  } else {
    // Pasture or native vegetation: steady with slight rain-driven pulse
    return baseNdvi + Math.sin(progress * Math.PI) * 0.08;
  }
}

/**
 * Generate PostGIS-compliant GeoJSON FeatureCollection dynamically evaluated
 * for the current calendar date in the Sentinel-2 timelapse.
 */
export function generateParcelsGeoJson(
  selectedDate: string = "2025-01-01",
  activeLayer: "rgb" | "ndvi" | "weather" = "ndvi",
  targetFieldId?: string
): ParcelsGeoJsonCollection {
  const startDate = new Date("2025-01-01T00:00:00Z").getTime();
  const curDate = new Date(selectedDate + "T00:00:00Z").getTime();
  const dayIndex = Math.max(0, Math.min(59, Math.round((curDate - startDate) / 86400000)));

  // Simulated daily weather based on dayIndex
  const simulatedTemp = 24 + Math.sin(dayIndex * 0.25) * 6; // 18C to 30C
  const simulatedRain = [
    0, 0, 4.5, 18.2, 2.0, 0, 0, 0, 0, 32.0, 
    8.5, 0, 0, 0, 0, 0, 0, 14.0, 6.0, 0,
    0, 0, 0, 0, 42.0, 15.0, 0, 0, 0, 0,
    0, 0, 5.0, 0, 0, 0, 22.0, 4.0, 0, 0,
    0, 0, 0, 0, 0, 18.5, 0, 0, 0, 0,
    0, 28.0, 12.0, 0, 0, 0, 0, 3.0, 0, 0
  ][dayIndex] ?? 0;

  const features: ParcelGeoJsonFeature[] = [];

  // 1. Process Neighbor Cadastral Parcels (OneSoil Cadastre context)
  NEIGHBOR_CADASTRE_PARCELS.forEach((cad) => {
    const field = FIELDS_DATA.find((f) => f.id === cad.fieldId);
    if (!field) return;

    const ring = cad.offsets.map(([dLat, dLng]) => [
      parseFloat((field.lng + dLng).toFixed(6)),
      parseFloat((field.lat + dLat).toFixed(6)),
    ]);
    if (ring.length > 0) {
      ring.push([ring[0][0], ring[0][1]]); // close polygon
    }

    const neighborNdvi = getSimulatedParcelNdvi(0.65, cad.crop || "Soja", dayIndex);
    
    // Choose active color according to layer
    let activeColor = cad.color;
    if (activeLayer === "ndvi") {
      activeColor = getNdviRampColor(neighborNdvi);
    } else if (activeLayer === "weather") {
      activeColor = getTempRampColor(simulatedTemp);
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
        currentTemp: parseFloat(simulatedTemp.toFixed(1)),
        currentRain: simulatedRain,
        statusLabel: "Lote vecino lindero",
      },
      geometry: {
        type: "Polygon",
        coordinates: [ring],
      },
    });
  });

  // 2. Process Loaded Portfolio Fields (Subdivided into agronomic parcels)
  FIELDS_DATA.forEach((field) => {
    const sectors = FIELD_SECTORS_DATA[field.id] || [];
    sectors.forEach((sec) => {
      const ring = sec.offsets.map(([dLat, dLng]) => [
        parseFloat((field.lng + dLng).toFixed(6)),
        parseFloat((field.lat + dLat).toFixed(6)),
      ]);
      if (ring.length > 0) {
        ring.push([ring[0][0], ring[0][1]]); // close polygon
      }

      const parcelNdvi = getSimulatedParcelNdvi(sec.ndvi, sec.crop, dayIndex);

      let activeColor = sec.color;
      let statusText = "En vegetación activa";

      if (activeLayer === "ndvi") {
        activeColor = getNdviRampColor(parcelNdvi);
        if (parcelNdvi > 0.80) statusText = "Pico vegetativo / Floración";
        else if (parcelNdvi > 0.60) statusText = "Desarrollo de biomasa";
        else statusText = "Emergencia / Crecimiento temprano";
      } else if (activeLayer === "weather") {
        activeColor = getTempRampColor(simulatedTemp);
        statusText = simulatedRain > 10 ? "Alerta precipitación acumulada" : "Régimen térmico normal";
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
          currentTemp: parseFloat(simulatedTemp.toFixed(1)),
          currentRain: simulatedRain,
          statusLabel: statusText,
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
