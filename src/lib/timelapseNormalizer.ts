import { TimelapseManifest, TimelapseFrame, WeatherDaily } from "@/types/terria";

/**
 * Normalizes backend FastAPI snake_case timelapse manifest response
 * into the frontend camelCase `TimelapseManifest` shape with nested MetricValue objects.
 */
export function normalizeTimelapseManifest(raw: any): TimelapseManifest {
  if (!raw) return raw;

  // If already normalized
  if (raw.weatherDaily && raw.frames && raw.schemaVersion === "1" && raw.weatherDaily[0]?.precipitationDay) {
    return raw as TimelapseManifest;
  }

  const rawWeather = raw.weather_daily || raw.weatherDaily || [];
  const rawFrames = raw.frames || [];

  const weatherDaily: WeatherDaily[] = rawWeather.map((w: any) => ({
    date: String(w.date || ""),
    precipitationDay: {
      value: w.precipitation_mm != null ? Number(w.precipitation_mm) : (w.precipitationDay?.value ?? 0),
      unit: "mm",
      sourceId: w.source_id || "open-meteo-era5",
      kind: "reanalysis",
    },
    precipitation7d: {
      value: w.precipitation_7d_mm != null ? Number(w.precipitation_7d_mm) : (w.precipitation7d?.value ?? 0),
      unit: "mm",
      sourceId: w.source_id || "open-meteo-era5",
      kind: "reanalysis",
    },
    temperatureMin: {
      value: w.temperature_min_c != null ? Number(w.temperature_min_c) : (w.temperatureMin?.value ?? 16),
      unit: "°C",
      sourceId: w.source_id || "open-meteo-era5",
      kind: "reanalysis",
    },
    temperatureMax: {
      value: w.temperature_max_c != null ? Number(w.temperature_max_c) : (w.temperatureMax?.value ?? 28),
      unit: "°C",
      sourceId: w.source_id || "open-meteo-era5",
      kind: "reanalysis",
    },
  }));

  const frames: TimelapseFrame[] = rawFrames.map((f: any) => {
    const rawNdvi = f.ndvi || {};
    const meanVal = typeof rawNdvi.mean === "number" ? rawNdvi.mean : rawNdvi.mean?.value;
    const p10Val = typeof rawNdvi.p10 === "number" ? rawNdvi.p10 : rawNdvi.p10?.value;
    const p90Val = typeof rawNdvi.p90 === "number" ? rawNdvi.p90 : rawNdvi.p90?.value;

    return {
      id: String(f.id || ""),
      observedAt: f.observed_at || f.observedAt || `${f.local_date || f.localDate}T14:30:00Z`,
      localDate: String(f.local_date || f.localDate || ""),
      sourceItemIds: f.source_item_ids || f.sourceItemIds || [],
      usable: Boolean(f.usable),
      unusableReason: f.missing_reason || f.unusableReason,
      quality: {
        validPixelFraction: f.valid_area_fraction != null ? Number(f.valid_area_fraction) : (f.quality?.validPixelFraction ?? 1),
        validPixelCount: f.valid_pixel_count != null ? Number(f.valid_pixel_count) : (f.quality?.validPixelCount ?? 0),
        cloudFraction: 1 - (f.valid_area_fraction != null ? Number(f.valid_area_fraction) : 1),
      },
      ndvi: {
        mean: {
          value: meanVal != null ? Number(meanVal) : null,
          unit: "",
          sourceId: "copernicus-s2-msi",
          kind: "derived",
        },
        p10: {
          value: p10Val != null ? Number(p10Val) : null,
          unit: "",
          sourceId: "copernicus-s2-msi",
          kind: "derived",
        },
        p90: {
          value: p90Val != null ? Number(p90Val) : null,
          unit: "",
          sourceId: "copernicus-s2-msi",
          kind: "derived",
        },
      },
      assets: (f.assets || []).map((a: any) => ({
        layer: a.layer,
        url: a.url,
        expiresAt: a.expires_at || a.expiresAt || "",
        resolutionM: 10,
        nodata: a.nodata,
        checksum: a.sha256 || a.checksum,
      })),
    };
  });

  return {
    schemaVersion: "1",
    datasetVersion: String(raw.dataset_id || raw.datasetVersion || "v1"),
    fieldId: String(raw.field_id || raw.fieldId || ""),
    geometryVersion: String(raw.geometry_version_id || raw.geometryVersion || "v1"),
    from: String(raw.start_date || raw.from || (weatherDaily[0]?.date ?? "2024-01-01")),
    to: String(raw.end_date || raw.to || (weatherDaily[weatherDaily.length - 1]?.date ?? "2024-03-31")),
    generatedAt: raw.generated_at || raw.generatedAt || new Date().toISOString(),
    status: raw.status === "failed" ? "partial" : (raw.status || "ready"),
    frames,
    weatherDaily,
    sources: (raw.sources || []).map((s: any) => ({
      id: s.id,
      provider: s.provider,
      dataset: s.dataset,
      documentationUrl: s.documentation_url || s.documentationUrl,
      resolution: s.resolution,
      attribution: s.attribution,
    })),
  };
}
