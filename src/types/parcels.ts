// Type definitions for Backend PostGIS GeoJSON Parcels & Multi-temporal Sentinel-2 Layers

export interface ParcelProperties {
  id: string;
  fieldId: string;
  fieldName?: string;
  name: string;
  crop: string;
  variety: string;
  hectares: number;
  soilHorizon?: string;
  isPortfolio: boolean;
  baseColor: string; // OneSoil default crop color
  color: string;     // Active color evaluated for current date & layer
  currentNdvi: number;
  currentTemp?: number;
  currentRain?: number;
  statusLabel?: string;
}

export interface ParcelGeoJsonFeature {
  type: "Feature";
  id?: string | number;
  properties: ParcelProperties;
  geometry: {
    type: "Polygon";
    coordinates: number[][][]; // [ [ [lng, lat], [lng, lat], ... ] ]
  };
}

export interface ParcelsGeoJsonCollection {
  type: "FeatureCollection";
  features: ParcelGeoJsonFeature[];
}
