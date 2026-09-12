export type MetricKind = "derived" | "reanalysis" | "declared";

export interface MetricValue<T = number> {
  value: T | null;
  unit: string;
  sourceId: string;
  kind: MetricKind;
  missingReason?: "clouds" | "no_scene" | "insufficient_coverage" | "provider_error" | "window_incomplete" | string;
}

export type TimelapseLayer = "rgb" | "ndvi" | "weather";

export interface TimelapseAsset {
  layer: "rgb" | "ndvi";
  url: string;
  expiresAt: string;
  resolutionM: number;
  nodata?: string;
  checksum?: string;
}

export interface TimelapseFrameQuality {
  validPixelFraction: number; // e.g. 0.94 (94%)
  validPixelCount: number;
  cloudFraction: number;
}

export interface TimelapseFrame {
  id: string;
  observedAt: string; // ISO UTC: "2025-02-12T14:32:00Z"
  localDate: string;  // "2025-02-12"
  sourceItemIds: string[];
  usable: boolean;
  unusableReason?: string;
  quality: TimelapseFrameQuality;
  ndvi: {
    mean: MetricValue<number>;
    p10: MetricValue<number>;
    p90: MetricValue<number>;
  };
  assets: TimelapseAsset[];
}

export interface WeatherDaily {
  date: string; // "2025-02-12"
  precipitationDay: MetricValue<number>;
  precipitation7d: MetricValue<number>;
  temperatureMin: MetricValue<number>;
  temperatureMax: MetricValue<number>;
}

export interface TimelapseSource {
  id: string;
  provider: string;
  dataset: string;
  documentationUrl?: string;
  resolution?: string;
  attribution: string;
}

export interface TimelapseManifest {
  schemaVersion: "1";
  datasetVersion: string;
  fieldId: string;
  geometryVersion: string;
  from: string;
  to: string;
  generatedAt: string;
  status: "ready" | "partial";
  frames: TimelapseFrame[];
  weatherDaily: WeatherDaily[];
  sources: TimelapseSource[];
}

export interface TimelineState {
  selectedDate: string;
  weather: WeatherDaily | null;
  satellite: TimelapseFrame | null;
  isFresh: boolean;
  ageDays: number | null;
  missingReason?: string;
}

export interface SolanaCertification {
  snapshotHash: string; // SHA-256 canonical hash
  txSignature: string;  // Solana devnet tx signature
  cluster: "devnet" | "mainnet-beta";
  slot: number;
  blockTime: number;
  verified: boolean;
  certifiedAt: string;
  campaign: string;
  memoProgram: string;
  explorerUrl: string;
}
