import { TimelapseManifest, SolanaCertification, TimelapseFrame, WeatherDaily } from "@/types/terria";

export const DEMO_SOLANA_CERTIFICATION: SolanaCertification = {
  snapshotHash: "b87f9c2a1e05d4b8e73104f6c4a8996fb92427ae41e4649b934ca495991b7852",
  txSignature: "4uX8eP9wBZ3M4X9rQ7kV2aL9nM1cE6tY8hR5vT3jK2pW1mS0dF7gH5jK9lP4oN6q",
  cluster: "devnet",
  slot: 284910392,
  blockTime: 1739372400,
  verified: true,
  certifiedAt: "2025-02-12T18:30:00Z",
  campaign: "2024/2025",
  memoProgram: "MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr",
  explorerUrl: "https://explorer.solana.com/tx/4uX8eP9wBZ3M4X9rQ7kV2aL9nM1cE6tY8hR5vT3jK2pW1mS0dF7gH5jK9lP4oN6q?cluster=devnet",
};

// Generamos 60 días de serie meteorológica y 10 pasadas satelitales (Ene a Mar 2025)
const generateMockTimeline = (): { weather: WeatherDaily[]; frames: TimelapseFrame[] } => {
  const weather: WeatherDaily[] = [];
  const frames: TimelapseFrame[] = [];

  const startDate = new Date("2025-01-01T00:00:00Z");
  const totalDays = 60;

  // Curva biológica esperada para maíz tardío en Córdoba (emergencia a llenado)
  const getSimulatedNdvi = (dayIndex: number): number => {
    // Pico en día 42 (mediados de febrero) ~ 0.81
    const progress = dayIndex / totalDays;
    if (progress < 0.25) return 0.32 + progress * 1.2;
    if (progress < 0.70) return 0.62 + (progress - 0.25) * 0.45;
    return 0.82 - (progress - 0.70) * 0.6;
  };

  const dailyRainValues: number[] = [
    0, 0, 4.5, 18.2, 2.0, 0, 0, 0, 0, 32.0, 
    8.5, 0, 0, 0, 0, 0, 0, 14.0, 6.0, 0,
    0, 0, 0, 0, 42.0, 15.0, 0, 0, 0, 0,
    0, 0, 5.0, 0, 0, 0, 22.0, 4.0, 0, 0,
    0, 0, 0, 0, 0, 18.5, 0, 0, 0, 0,
    0, 28.0, 12.0, 0, 0, 0, 0, 3.0, 0, 0
  ];

  for (let i = 0; i < totalDays; i++) {
    const d = new Date(startDate.getTime() + i * 86400000);
    const dateStr = d.toISOString().split("T")[0];

    const rainDay = dailyRainValues[i] ?? 0;
    // Cálculo acumulado 7 días anteriores
    let rain7d = 0;
    for (let k = Math.max(0, i - 6); k <= i; k++) {
      rain7d += dailyRainValues[k] ?? 0;
    }

    const tMin = 16 + Math.sin(i * 0.3) * 4;
    const tMax = 28 + Math.cos(i * 0.2) * 5;

    weather.push({
      date: dateStr,
      precipitationDay: {
        value: Number(rainDay.toFixed(1)),
        unit: "mm",
        sourceId: "open-meteo-era5",
        kind: "reanalysis",
      },
      precipitation7d: {
        value: Number(rain7d.toFixed(1)),
        unit: "mm",
        sourceId: "open-meteo-era5",
        kind: "derived",
      },
      temperatureMin: {
        value: Number(tMin.toFixed(1)),
        unit: "°C",
        sourceId: "open-meteo-era5",
        kind: "reanalysis",
      },
      temperatureMax: {
        value: Number(tMax.toFixed(1)),
        unit: "°C",
        sourceId: "open-meteo-era5",
        kind: "reanalysis",
      },
    });

    // Pasadas satelitales cada ~5-6 días
    if (i % 6 === 3) {
      const meanNdvi = getSimulatedNdvi(i);
      const isCloudy = i === 27; // Frame de prueba con nubes (inutilizable)

      frames.push({
        id: `s2-frame-${i}`,
        observedAt: `${dateStr}T14:28:15Z`,
        localDate: dateStr,
        sourceItemIds: [`S2A_MSIL2A_20250${Math.floor(i/30)+1}${dateStr.replace(/-/g, "")}`],
        usable: !isCloudy,
        unusableReason: isCloudy ? "clouds" : undefined,
        quality: {
          validPixelFraction: isCloudy ? 0.38 : 0.88 + (i % 5) * 0.02,
          validPixelCount: isCloudy ? 1420 : 3820,
          cloudFraction: isCloudy ? 0.62 : 0.04,
        },
        ndvi: {
          mean: {
            value: isCloudy ? null : Number(meanNdvi.toFixed(2)),
            unit: "index",
            sourceId: "sentinel-2-l2a",
            kind: "derived",
            missingReason: isCloudy ? "clouds" : undefined,
          },
          p10: {
            value: isCloudy ? null : Number((meanNdvi * 0.88).toFixed(2)),
            unit: "index",
            sourceId: "sentinel-2-l2a",
            kind: "derived",
          },
          p90: {
            value: isCloudy ? null : Number((meanNdvi * 1.08).toFixed(2)),
            unit: "index",
            sourceId: "sentinel-2-l2a",
            kind: "derived",
          },
        },
        assets: [
          {
            layer: "rgb",
            url: `/textures/fields/field_1_rgb_${i}.png`,
            expiresAt: "2026-12-31T23:59:59Z",
            resolutionM: 10,
          },
          {
            layer: "ndvi",
            url: `/textures/fields/field_1_ndvi_${i}.png`,
            expiresAt: "2026-12-31T23:59:59Z",
            resolutionM: 10,
          },
        ],
      });
    }
  }

  return { weather, frames };
};

const { weather, frames } = generateMockTimeline();

export const DEMO_TIMELAPSE_MANIFEST: TimelapseManifest = {
  schemaVersion: "1",
  datasetVersion: "v1.4-sentinel-era5",
  fieldId: "field-1-la-providencia",
  geometryVersion: "geom-v2-geo-wgs84",
  from: "2025-01-01",
  to: "2025-03-01",
  generatedAt: "2025-03-02T10:00:00Z",
  status: "ready",
  frames,
  weatherDaily: weather,
  sources: [
    {
      id: "sentinel-2-l2a",
      provider: "Copernicus CDSE",
      dataset: "Sentinel-2 MSI Level-2A",
      resolution: "10m",
      attribution: "European Space Agency (ESA) Copernicus Sentinel data",
    },
    {
      id: "open-meteo-era5",
      provider: "Open-Meteo / ECMWF",
      dataset: "ERA5 Reanalysis",
      resolution: "0.25° (~25km)",
      attribution: "ECMWF Copernicus Climate Change Service",
    },
  ],
};
