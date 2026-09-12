"use client";

import React, { useEffect, useRef, useState, useCallback } from "react";
import mapboxgl from "mapbox-gl";
import "mapbox-gl/dist/mapbox-gl.css";
import { FIELDS_DATA, FieldItem } from "@/data/fieldsData";
import { FIELD_SECTORS_DATA, NEIGHBOR_CADASTRE_PARCELS } from "@/data/sectorsData";
import { useFieldTimelapse } from "@/hooks/useFieldTimelapse";
import { generateParcelsGeoJson } from "@/data/backendParcelsGeoJson";
import {
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Layers,
  Sparkles,
  Globe2,
  Map as MapIcon,
  Box,
  Satellite,
  Compass,
} from "lucide-react";

// Configure Mapbox CSP Web Worker locally from /public to eliminate all worker errors
if (typeof window !== "undefined") {
  // @ts-ignore
  mapboxgl.workerUrl = "/mapbox-gl-csp-worker.js";
}

export interface Planet3DProps {
  embedded?: boolean;
  selectedField?: FieldItem;
  isExpanded?: boolean;
  className?: string;
  onSelectField?: (field: FieldItem) => void;
  onIsolateField?: (field: FieldItem) => void;
  timelapse?: ReturnType<typeof useFieldTimelapse>;
}

// 100% Free & Open Basemap Styles without Watermarks or API Key Requirements
const OPEN_MAP_STYLES: Record<string, any> = {
  canvas: {
    version: 8,
    name: "Minimalista Blanco",
    sources: {
      "esri-canvas-base": {
        type: "raster",
        tiles: [
          "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}",
        ],
        tileSize: 256,
        maxzoom: 16,
        attribution: "© Esri, HERE, Garmin, OpenStreetMap",
      },
      "esri-canvas-ref": {
        type: "raster",
        tiles: [
          "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Reference/MapServer/tile/{z}/{y}/{x}",
        ],
        tileSize: 256,
        maxzoom: 16,
      },
    },
    layers: [
      {
        id: "esri-canvas-base-layer",
        type: "raster",
        source: "esri-canvas-base",
        minzoom: 0,
        maxzoom: 20,
      },
      {
        id: "esri-canvas-ref-layer",
        type: "raster",
        source: "esri-canvas-ref",
        minzoom: 0,
        maxzoom: 20,
      },
    ],
  },
  satellite: {
    version: 8,
    name: "Satélite Real HD",
    sources: {
      "esri-satellite": {
        type: "raster",
        tiles: [
          "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        ],
        tileSize: 256,
        maxzoom: 19,
        attribution: "© Esri, Maxar, Earthstar Geographics",
      },
      "esri-roads-ref": {
        type: "raster",
        tiles: [
          "https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Transportation/MapServer/tile/{z}/{y}/{x}",
        ],
        tileSize: 256,
        maxzoom: 19,
      },
      "esri-places-ref": {
        type: "raster",
        tiles: [
          "https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}",
        ],
        tileSize: 256,
        maxzoom: 19,
      },
    },
    layers: [
      {
        id: "esri-satellite-layer",
        type: "raster",
        source: "esri-satellite",
        minzoom: 0,
        maxzoom: 20,
      },
      {
        id: "esri-roads-layer",
        type: "raster",
        source: "esri-roads-ref",
        minzoom: 6,
        maxzoom: 20,
      },
      {
        id: "esri-places-layer",
        type: "raster",
        source: "esri-places-ref",
        minzoom: 0,
        maxzoom: 20,
      },
    ],
  },
  streets: {
    version: 8,
    name: "Calles & Catastro",
    sources: {
      "esri-streets": {
        type: "raster",
        tiles: [
          "https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}",
        ],
        tileSize: 256,
        maxzoom: 17,
        attribution: "© Esri, HERE, Garmin, USGS",
      },
    },
    layers: [
      {
        id: "esri-streets-layer",
        type: "raster",
        source: "esri-streets",
        minzoom: 0,
        maxzoom: 20,
      },
    ],
  },
  osm: {
    version: 8,
    name: "OpenStreetMap",
    sources: {
      "osm-standard": {
        type: "raster",
        tiles: [
          "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
        ],
        tileSize: 256,
        maxzoom: 19,
        attribution: "© OpenStreetMap contributors",
      },
    },
    layers: [
      {
        id: "osm-standard-layer",
        type: "raster",
        source: "osm-standard",
        minzoom: 0,
        maxzoom: 19,
      },
    ],
  },
  topo: {
    version: 8,
    name: "Relieve & Terreno",
    sources: {
      "esri-topo": {
        type: "raster",
        tiles: [
          "https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}",
        ],
        tileSize: 256,
        maxzoom: 17,
        attribution: "© Esri, USGS, FAO",
      },
    },
    layers: [
      {
        id: "esri-topo-layer",
        type: "raster",
        source: "esri-topo",
        minzoom: 0,
        maxzoom: 20,
      },
    ],
  },
};

export type FreeMapStyleKey = "canvas" | "satellite" | "streets" | "osm" | "topo";

export default function Planet3D({
  embedded = false,
  selectedField,
  isExpanded = false,
  className = "",
  onSelectField,
  onIsolateField,
  timelapse,
}: Planet3DProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<mapboxgl.Map | null>(null);
  const markersRef = useRef<mapboxgl.Marker[]>([]);

  const [currentStyleKey, setCurrentStyleKey] = useState<FreeMapStyleKey>("canvas");
  const [zoomLevelName, setZoomLevelName] = useState<"global" | "regional" | "parcel">("global");
  const [currentZoom, setCurrentZoom] = useState<number>(2.0);
  const [showStyleMenu, setShowStyleMenu] = useState(false);

  // Construct GeoJSON FeatureCollection for field cadastral parcels & crop sectors
  const buildParcelsGeoJson = useCallback(() => {
    const selectedDate = timelapse?.timelineState?.selectedDate || "2025-01-01";
    const activeLayer = (timelapse?.activeLayer as "rgb" | "ndvi" | "weather") || "ndvi";
    return generateParcelsGeoJson(selectedDate, activeLayer, selectedField?.id);
  }, [timelapse?.timelineState?.selectedDate, timelapse?.activeLayer, selectedField?.id]);

  // Synchronize GeoJSON source whenever timelapse date or layer changes
  useEffect(() => {
    if (!mapRef.current) return;
    const map = mapRef.current;
    if (!map.isStyleLoaded || !map.isStyleLoaded()) return;
    try {
      const source = map.getSource("field-parcels") as mapboxgl.GeoJSONSource | undefined;
      if (source) {
        const data = buildParcelsGeoJson();
        source.setData(data as any);
      }
    } catch {
      // Map style or source not ready yet
    }
  }, [buildParcelsGeoJson]);

  // Add parcels layers on map style load
  const addParcelLayers = useCallback(
    (map: mapboxgl.Map) => {
      if (!map || !map.isStyleLoaded || !map.isStyleLoaded()) return;
      try {
        if (map.getSource("field-parcels")) return;

        const data = buildParcelsGeoJson();
        map.addSource("field-parcels", {
          type: "geojson",
          data: data as any,
        });

      // Find top reference layer (labels/cities/routes) so parcel fill stays beneath text for readability
      const beforeLayer = map.getLayer("esri-canvas-ref-layer")
        ? "esri-canvas-ref-layer"
        : map.getLayer("esri-places-layer")
        ? "esri-places-layer"
        : undefined;

      // Layer 1: Surrounding neighbor cadastral lots (authentic OneSoil multi-crop mosaic, non-selectable)
      map.addLayer(
        {
          id: "cadastre-neighbors-fill",
          type: "fill",
          source: "field-parcels",
          filter: ["==", ["get", "isPortfolio"], false],
          paint: {
            "fill-color": ["get", "color"],
            "fill-opacity": 0.62,
          },
        },
        beforeLayer
      );

      // Layer 2: Surrounding neighbor cadastral boundaries (crisp parcel fence/road separation)
      map.addLayer(
        {
          id: "cadastre-neighbors-line",
          type: "line",
          source: "field-parcels",
          filter: ["==", ["get", "isPortfolio"], false],
          paint: {
            "line-color": "#1e293b",
            "line-width": 1.6,
            "line-opacity": 0.75,
          },
        },
        beforeLayer
      );

      // Layer 3: Our loaded agricultural portfolio fields (vibrant NDVI & crop colors, interactive)
      map.addLayer(
        {
          id: "field-parcels-fill",
          type: "fill",
          source: "field-parcels",
          filter: ["==", ["get", "isPortfolio"], true],
          paint: {
            "fill-color": ["get", "color"],
            "fill-opacity": 0.78,
          },
        },
        beforeLayer
      );

      // Layer 4: Crisp cadastral perimeter lines for our loaded portfolio fields
      map.addLayer(
        {
          id: "field-parcels-line",
          type: "line",
          source: "field-parcels",
          filter: ["==", ["get", "isPortfolio"], true],
          paint: {
            "line-color": "#0f172a",
            "line-width": 2.5,
            "line-opacity": 0.95,
          },
        },
        beforeLayer
      );

      // Layer 5: Active field outer glow / halo (OneSoil neon blue halo)
      map.addLayer(
        {
          id: "field-active-halo",
          type: "line",
          source: "field-parcels",
          filter: [
            "all",
            ["==", ["get", "isPortfolio"], true],
            ["==", ["get", "fieldId"], selectedField?.id || ""],
          ],
          paint: {
            "line-color": "#2563eb",
            "line-width": 7.0,
            "line-opacity": 0.5,
          },
        },
        beforeLayer
      );

      // Layer 6: Active field crisp white neon border (OneSoil-style neon white boundary)
      map.addLayer(
        {
          id: "field-active-highlight",
          type: "line",
          source: "field-parcels",
          filter: [
            "all",
            ["==", ["get", "isPortfolio"], true],
            ["==", ["get", "fieldId"], selectedField?.id || ""],
          ],
          paint: {
            "line-color": "#ffffff",
            "line-width": 4.0,
            "line-opacity": 1.0,
          },
        },
        beforeLayer
      );
    } catch (err) {
      console.warn("Failed to add parcel layers:", err);
    }
  },
    [buildParcelsGeoJson, selectedField]
  );

  // Initialize Mapbox GL JS with Globe Projection
  useEffect(() => {
    if (!mapContainerRef.current) return;

    mapboxgl.accessToken =
      process.env.NEXT_PUBLIC_MAPBOX_TOKEN || "";

    const initialCenter: [number, number] = selectedField
      ? [selectedField.lng, selectedField.lat]
      : [-64.215, -33.115];

    const initialZoom = isExpanded ? 14.8 : 2.2;
    const initialPitch = isExpanded ? 45 : 0;

    const styleToUse = OPEN_MAP_STYLES[currentStyleKey] as any;

    const map = new mapboxgl.Map({
      container: mapContainerRef.current,
      style: styleToUse,
      projection: "globe", // 3D Globe View!
      center: initialCenter,
      zoom: initialZoom,
      pitch: initialPitch,
      maxZoom: 16.8, // Clamps zoom to guarantee no 'Map data not yet available' errors
      minZoom: 1.5,
      attributionControl: false,
    });

    mapRef.current = map;

    // Ensure map resizes properly as flex/grid layout computes
    const resizeTimeout = setTimeout(() => {
      map.resize();
    }, 150);

    const ro = new ResizeObserver(() => {
      map.resize();
    });
    ro.observe(mapContainerRef.current);

    // Apply clean white atmosphere & fog on load
    const applyFogAndAtmosphere = () => {
      if (!map.isStyleLoaded || !map.isStyleLoaded()) return;
      try {
        map.setFog({
          color: "rgb(255, 255, 255)", // Atmosphere bottom
          "high-color": "rgb(240, 246, 255)", // Atmosphere upper
          "horizon-blend": 0.02, // Atmosphere thickness
          "space-color": "rgb(255, 255, 255)", // Pure white background!
          "star-intensity": 0.0,
        });
      } catch {
        // Fog not supported or error
      }
      addParcelLayers(map);
    };

    map.on("style.load", applyFogAndAtmosphere);
    if (map.isStyleLoaded && map.isStyleLoaded()) {
      applyFogAndAtmosphere();
    }

    // Floating tooltip for OneSoil parcel inspector
    const hoverPopup = new mapboxgl.Popup({
      closeButton: false,
      closeOnClick: false,
      offset: 12,
    });

    // Interactive click: ONLY trigger selection on our loaded portfolio fields
    map.on("click", (e) => {
      if (!map.isStyleLoaded || !map.isStyleLoaded()) return;
      try {
        if (!map.getLayer("field-parcels-fill")) return;
        const features = map.queryRenderedFeatures(e.point, { layers: ["field-parcels-fill"] });
        if (features && features[0]) {
          const isPortfolio = features[0].properties?.isPortfolio;
          if (isPortfolio) {
            const fieldId = features[0].properties?.fieldId;
            const match = FIELDS_DATA.find((f) => f.id === fieldId);
            if (match && onSelectField) {
              onSelectField(match);
            }
          }
        }
      } catch {
        // Safe ignore
      }
    });

    // Mousemove: OneSoil tooltip & pointer cursor ONLY on portfolio fields
    map.on("mousemove", (e) => {
      if (!map.isStyleLoaded || !map.isStyleLoaded()) return;
      try {
        const activeLayer = map.getLayer("field-parcels-fill");
        const cadastreLayer = map.getLayer("cadastre-neighbors-fill");
        if (!activeLayer && !cadastreLayer) return;

      const layersToQuery: string[] = [];
      if (activeLayer) layersToQuery.push("field-parcels-fill");
      if (cadastreLayer) layersToQuery.push("cadastre-neighbors-fill");

      const features = map.queryRenderedFeatures(e.point, { layers: layersToQuery });

      if (features && features[0]) {
        const f = features[0];
        const props = f.properties || {};
        const isPortfolio = props.isPortfolio === true || props.isPortfolio === "true";

        map.getCanvas().style.cursor = isPortfolio ? "pointer" : "default";

        const html = isPortfolio
          ? `
            <div style="padding: 7px 11px; font-family: system-ui, sans-serif; font-size: 11px; line-height: 1.35; max-width: 215px;">
              <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px;">
                <div style="display: flex; align-items: center; gap: 5px;">
                  <span style="display: inline-block; width: 7px; height: 7px; border-radius: 9999px; background: #10b981;"></span>
                  <span style="font-size: 9px; font-weight: 800; text-transform: uppercase; color: #047857; letter-spacing: 0.05em;">Lote en Cartera</span>
                </div>
                ${props.currentNdvi ? `<span style="font-size: 10px; font-weight: 700; color: #15803d; background: #dcfce7; padding: 1px 5px; border-radius: 4px;">NDVI ${props.currentNdvi}</span>` : ''}
              </div>
              <div style="font-weight: 700; color: #0f172a; font-size: 12px;">${props.name || props.fieldName || "Lote Productivo"}</div>
              <div style="color: #475569; font-size: 11px; margin-top: 2px;">${props.crop} • <b>${props.hectares || 0} ha</b></div>
              <div style="font-size: 10px; color: #047857; margin-top: 4px; background: #f0fdf4; padding: 3px 6px; border-radius: 4px; border: 1px solid #bbf7d0;">
                🌱 ${props.statusLabel || "Desarrollo vegetal activo"}
              </div>
              ${props.currentTemp ? `<div style="font-size: 10px; color: #64748b; margin-top: 3px;">ERA5 Clima: ${props.currentTemp}°C • Lluvia: ${props.currentRain || 0} mm</div>` : ''}
              <div style="color: #2563eb; font-weight: 600; font-size: 10px; margin-top: 5px;">Clic para abrir pasaporte ➔</div>
            </div>
          `
          : `
            <div style="padding: 7px 11px; font-family: system-ui, sans-serif; font-size: 11px; line-height: 1.35; max-width: 215px;">
              <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px;">
                <div style="display: flex; align-items: center; gap: 5px;">
                  <span style="display: inline-block; width: 7px; height: 7px; border-radius: 9999px; background: #94a3b8;"></span>
                  <span style="font-size: 9px; font-weight: 800; text-transform: uppercase; color: #64748b; letter-spacing: 0.05em;">Catastro Lindero</span>
                </div>
                ${props.currentNdvi ? `<span style="font-size: 10px; font-weight: 700; color: #475569; background: #f1f5f9; padding: 1px 5px; border-radius: 4px;">NDVI ${props.currentNdvi}</span>` : ''}
              </div>
              <div style="font-weight: 700; color: #1e293b; font-size: 12px;">${props.name || "Chacra Vecina"}</div>
              <div style="color: #64748b; font-size: 11px; margin-top: 2px;">${props.crop || "Cultivo lindero"} • <b>${props.hectares || 0} ha</b></div>
              <div style="color: #94a3b8; font-style: italic; font-size: 10px; margin-top: 4px;">Lote vecino (no seleccionable)</div>
            </div>
          `;

        hoverPopup.setLngLat(e.lngLat).setHTML(html).addTo(map);
      } else {
        map.getCanvas().style.cursor = "";
        hoverPopup.remove();
      }
    } catch {
      // Safe ignore
    }
  });

  map.on("mouseout", () => {
    map.getCanvas().style.cursor = "";
    hoverPopup.remove();
  });

  // Track Zoom level dynamically
  map.on("zoom", () => {
    const z = map.getZoom();
    setCurrentZoom(z);
    if (z < 5.0) {
      setZoomLevelName("global");
    } else if (z < 11.5) {
      setZoomLevelName("regional");
    } else {
      setZoomLevelName("parcel");
    }
  });

  // Add interactive field markers
  markersRef.current.forEach((m) => m.remove());
  markersRef.current = [];

  FIELDS_DATA.forEach((field) => {
    const el = document.createElement("div");
    el.className =
      "group cursor-pointer flex items-center gap-1.5 rounded-full bg-white/95 border border-gray-200 px-3 py-1.5 text-xs font-bold text-gray-800 shadow-md backdrop-blur-md transition-all hover:scale-110 hover:border-blue-500 hover:shadow-lg active:scale-95";

    el.innerHTML = `
      <span class="flex h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></span>
      <span class="truncate max-w-[120px] font-bold text-gray-900">${field.name}</span>
      <span class="rounded-full bg-blue-50 text-blue-700 font-semibold px-2 py-0.5 text-[10px]">
        ${field.hectares} ha
      </span>
    `;

    el.addEventListener("click", (e) => {
      e.stopPropagation();
      if (onSelectField) onSelectField(field);
      map.flyTo({
        center: [field.lng, field.lat],
        zoom: 14.8,
        pitch: 45,
        bearing: -15,
        duration: 2200,
      });
    });

    const marker = new mapboxgl.Marker({ element: el, anchor: "bottom" })
      .setLngLat([field.lng, field.lat])
      .addTo(map);

    markersRef.current.push(marker);
  });

  return () => {
    clearTimeout(resizeTimeout);
    ro.disconnect();
    markersRef.current.forEach((m) => m.remove());
    map.remove();
    mapRef.current = null;
  };
}, []);

// React to field selection: Smoothly fly camera to field with parcel zoom & update active highlight
useEffect(() => {
  if (!mapRef.current || !selectedField) return;
  const map = mapRef.current;

  const targetZoom = isExpanded ? 14.8 : 6.8;
  const targetPitch = isExpanded ? 45 : 20;

  map.flyTo({
    center: [selectedField.lng, selectedField.lat],
    zoom: targetZoom,
    pitch: targetPitch,
    bearing: isExpanded ? -15 : 0,
    essential: true,
    duration: 2200,
  });

  // Update active highlight & halo glow filters safely
  if (map.isStyleLoaded && map.isStyleLoaded()) {
    try {
      if (map.getLayer("field-active-highlight")) {
        map.setFilter("field-active-highlight", [
          "all",
          ["==", ["get", "isPortfolio"], true],
          ["==", ["get", "fieldId"], selectedField.id],
        ]);
      }
      if (map.getLayer("field-active-halo")) {
        map.setFilter("field-active-halo", [
          "all",
          ["==", ["get", "isPortfolio"], true],
          ["==", ["get", "fieldId"], selectedField.id],
        ]);
      }
    } catch {
      // Style not fully ready yet
    }
  }
}, [selectedField, isExpanded]);

  // Switch Map Style
  const handleStyleChange = (styleKey: FreeMapStyleKey) => {
    if (!mapRef.current) return;
    setCurrentStyleKey(styleKey);
    mapRef.current.setStyle(OPEN_MAP_STYLES[styleKey] as any);
    setShowStyleMenu(false);
  };

  // Stepper: Zoom to Global Orbit
  const zoomToGlobal = () => {
    if (!mapRef.current) return;
    mapRef.current.flyTo({
      center: [-64.215, -33.115],
      zoom: 1.8,
      pitch: 0,
      bearing: 0,
      essential: true,
      duration: 1800,
    });
  };

  // Stepper: Zoom to Regional Argentine Agricultural Core
  const zoomToRegional = () => {
    if (!mapRef.current) return;
    mapRef.current.flyTo({
      center: [-62.5, -33.5],
      zoom: 6.8,
      pitch: 25,
      bearing: 0,
      essential: true,
      duration: 1800,
    });
  };

  // Stepper: Zoom to Parcel Detail View (OneSoil parcel zoom)
  const zoomToParcel = () => {
    if (!mapRef.current || !selectedField) return;
    mapRef.current.flyTo({
      center: [selectedField.lng, selectedField.lat],
      zoom: 14.8,
      pitch: 45,
      bearing: -15,
      essential: true,
      duration: 1800,
    });
  };

  const handleZoomIn = () => {
    if (!mapRef.current) return;
    mapRef.current.zoomIn({ duration: 350 });
  };

  const handleZoomOut = () => {
    if (!mapRef.current) return;
    mapRef.current.zoomOut({ duration: 350 });
  };

  return (
    <div className={`relative w-full h-full overflow-hidden select-none bg-white ${className}`}>
      {/* Real Mapbox GL WebGL Map Container */}
      <div ref={mapContainerRef} className="absolute inset-0 w-full h-full" />

      {/* Top Left: Mapbox-Style Level-of-Detail (LOD) Stepper */}
      <div className="absolute top-3 left-3 z-20 pointer-events-auto flex flex-col gap-1.5">
        <div className="flex items-center gap-1 rounded-full bg-white/95 border border-gray-200 p-1 shadow-sm backdrop-blur-md">
          <button
            onClick={zoomToGlobal}
            title="Vista Global (Planeta 3D completo)"
            className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium transition-colors cursor-pointer ${
              zoomLevelName === "global"
                ? "bg-blue-600 text-white shadow-xs font-semibold"
                : "text-gray-600 hover:text-gray-900 hover:bg-gray-100"
            }`}
          >
            <Globe2 className="h-3 w-3" />
            <span>Global</span>
          </button>

          <button
            onClick={zoomToRegional}
            title="Vista Regional (Provincias y Rutas)"
            className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium transition-colors cursor-pointer ${
              zoomLevelName === "regional"
                ? "bg-blue-600 text-white shadow-xs font-semibold"
                : "text-gray-600 hover:text-gray-900 hover:bg-gray-100"
            }`}
          >
            <MapIcon className="h-3 w-3" />
            <span>Regional</span>
          </button>

          <button
            onClick={zoomToParcel}
            title="Vista Parcela (Calles, lotes y NDVI)"
            className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium transition-colors cursor-pointer ${
              zoomLevelName === "parcel"
                ? "bg-emerald-600 text-white shadow-xs font-semibold"
                : "text-gray-600 hover:text-gray-900 hover:bg-gray-100"
            }`}
          >
            <Sparkles className="h-3 w-3" />
            <span>Parcela</span>
          </button>

          {selectedField && onIsolateField && (
            <button
              onClick={() => onIsolateField(selectedField)}
              title="Separar este campo del mapa como maqueta 3D aislada"
              className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-blue-50 text-blue-700 hover:bg-blue-100 transition-all cursor-pointer border border-blue-200/60 shadow-xs"
            >
              <Box className="h-3 w-3 text-blue-600" />
              <span>Aislar en 3D</span>
            </button>
          )}
        </div>

        {/* Current Scale & Altitude Pill */}
        <div className="flex items-center gap-2 rounded-full bg-white/90 border border-gray-200/80 px-3 py-1 shadow-xs backdrop-blur-sm text-[11px] text-gray-500 font-sans w-fit">
          <span
            className={`h-1.5 w-1.5 rounded-full shrink-0 ${
              zoomLevelName === "parcel"
                ? "bg-emerald-500 animate-pulse"
                : zoomLevelName === "regional"
                ? "bg-blue-500"
                : "bg-gray-400"
            }`}
          />
          <span className="font-medium text-gray-700">
            {zoomLevelName === "parcel"
              ? `Nivel Parcela (Zoom ${currentZoom.toFixed(1)} • Calles y Catastro)`
              : zoomLevelName === "regional"
              ? `Nivel Regional (Zoom ${currentZoom.toFixed(1)} • Rutas y Ciudades)`
              : `Órbita Global (Zoom ${currentZoom.toFixed(1)} • Planeta 3D)`}
          </span>
        </div>

              {/* OneSoil Dynamic Metric Legend (NDVI / Clima / Cultivos) */}
        {currentZoom >= 5.0 && (
          <div className="flex flex-wrap items-center gap-2 rounded-2xl bg-white/95 border border-gray-200/90 px-3 py-1.5 shadow-sm backdrop-blur-md text-[11px] text-gray-700 max-w-fit animate-in fade-in duration-300">
            {timelapse?.activeLayer === "ndvi" ? (
              <>
                <span className="font-bold text-gray-900 flex items-center gap-1">
                  <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></span>
                  NDVI Sentinel-2:
                </span>
                <div className="flex items-center gap-1 font-medium">
                  <span className="inline-block h-2.5 w-2.5 rounded-xs bg-[#fef08a] border border-black/10 shadow-xs" />
                  <span>&lt;0.35 Suelo</span>
                </div>
                <div className="flex items-center gap-1 font-medium">
                  <span className="inline-block h-2.5 w-2.5 rounded-xs bg-[#bef264] border border-black/10 shadow-xs" />
                  <span>0.50</span>
                </div>
                <div className="flex items-center gap-1 font-medium">
                  <span className="inline-block h-2.5 w-2.5 rounded-xs bg-[#84cc16] border border-black/10 shadow-xs" />
                  <span>0.65</span>
                </div>
                <div className="flex items-center gap-1 font-medium">
                  <span className="inline-block h-2.5 w-2.5 rounded-xs bg-[#22c55e] border border-black/10 shadow-xs" />
                  <span>0.78</span>
                </div>
                <div className="flex items-center gap-1 font-medium">
                  <span className="inline-block h-2.5 w-2.5 rounded-xs bg-[#15803d] border border-black/10 shadow-xs" />
                  <span>&gt;0.85 Pico</span>
                </div>
              </>
            ) : timelapse?.activeLayer === "weather" ? (
              <>
                <span className="font-bold text-gray-900 flex items-center gap-1">
                  <span className="h-2 w-2 rounded-full bg-blue-500 animate-pulse"></span>
                  Clima ERA5:
                </span>
                <div className="flex items-center gap-1 font-medium">
                  <span className="inline-block h-2.5 w-2.5 rounded-xs bg-[#38bdf8] border border-black/10 shadow-xs" />
                  <span>&lt;22°C</span>
                </div>
                <div className="flex items-center gap-1 font-medium">
                  <span className="inline-block h-2.5 w-2.5 rounded-xs bg-[#34d399] border border-black/10 shadow-xs" />
                  <span>25°C</span>
                </div>
                <div className="flex items-center gap-1 font-medium">
                  <span className="inline-block h-2.5 w-2.5 rounded-xs bg-[#fbbf24] border border-black/10 shadow-xs" />
                  <span>30°C</span>
                </div>
                <div className="flex items-center gap-1 font-medium">
                  <span className="inline-block h-2.5 w-2.5 rounded-xs bg-[#f97316] border border-black/10 shadow-xs" />
                  <span>&gt;32°C Estrés</span>
                </div>
              </>
            ) : (
              <>
                <span className="font-bold text-gray-900 flex items-center gap-1">
                  <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></span>
                  Cultivos:
                </span>
                <div className="flex items-center gap-1 font-medium">
                  <span className="inline-block h-2.5 w-2.5 rounded-xs bg-[#eab308] border border-black/10 shadow-xs" />
                  <span>Maíz</span>
                </div>
                <div className="flex items-center gap-1 font-medium">
                  <span className="inline-block h-2.5 w-2.5 rounded-xs bg-[#dc2626] border border-black/10 shadow-xs" />
                  <span>Soja</span>
                </div>
                <div className="flex items-center gap-1 font-medium">
                  <span className="inline-block h-2.5 w-2.5 rounded-xs bg-[#ca8a04] border border-black/10 shadow-xs" />
                  <span>Cebada</span>
                </div>
                <div className="flex items-center gap-1 font-medium">
                  <span className="inline-block h-2.5 w-2.5 rounded-xs bg-[#16a34a] border border-black/10 shadow-xs" />
                  <span>Pastura</span>
                </div>
                <div className="flex items-center gap-1 font-medium text-gray-500 border-l border-gray-200 pl-2">
                  <span className="inline-block h-2.5 w-2.5 rounded-xs bg-[#475569] border border-black/10 shadow-xs" />
                  <span>Linderos</span>
                </div>
              </>
            )}
          </div>
        )}
      </div>

            {/* Top Center: Sentinel-2 Live Observation & Date HUD */}
      {timelapse && isExpanded && (
        <div className="absolute top-3 left-1/2 -translate-x-1/2 z-20 pointer-events-none hidden sm:flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-white/95 border border-emerald-200/90 shadow-md backdrop-blur-md text-xs text-gray-800 animate-in fade-in duration-300">
          <span className="flex h-2 w-2 rounded-full bg-emerald-500 animate-ping" />
          <span className="font-bold text-gray-900">
            Sentinel-2 L2A • {timelapse.timelineState?.selectedDate || "2025-02-12"}
          </span>
          <span className="text-[10px] uppercase tracking-wider font-bold text-emerald-800 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full">
            {timelapse.activeLayer === "ndvi" ? "Índice NDVI" : timelapse.activeLayer === "weather" ? "Clima ERA5" : "RGB Real"}
          </span>
          {timelapse.timelineState?.satellite?.quality && (
            <span className="text-[10px] text-gray-500 font-medium border-l border-gray-200 pl-2">
              {Math.round(timelapse.timelineState.satellite.quality.validPixelFraction * 100)}% sin nubes
            </span>
          )}
        </div>
      )}

      {/* Top Right: Map Style Selector (Calles / Satélite / Positron) & Token */}
      <div className="absolute top-3 right-3 z-20 pointer-events-auto flex items-center gap-1.5">
        <div className="relative">
          <button
            onClick={() => setShowStyleMenu(!showStyleMenu)}
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-full bg-white/95 border border-gray-200 text-xs font-semibold text-gray-700 shadow-sm backdrop-blur-md hover:bg-gray-50 transition-colors cursor-pointer"
          >
            <Layers className="h-3.5 w-3.5 text-blue-600" />
            <span>{OPEN_MAP_STYLES[currentStyleKey].name}</span>
          </button>

          {showStyleMenu && (
            <div className="absolute right-0 top-10 w-52 rounded-2xl bg-white border border-gray-200 p-2 shadow-xl backdrop-blur-md space-y-1 text-xs z-30">
              <div className="px-2 py-1 text-[10px] font-bold text-gray-400 uppercase tracking-wider">
                Capas Gratuitas (Sin API Key)
              </div>
              <button
                onClick={() => handleStyleChange("canvas")}
                className={`w-full flex items-center justify-between p-2 rounded-xl text-left cursor-pointer transition-colors ${
                  currentStyleKey === "canvas"
                    ? "bg-blue-50 text-blue-700 font-bold"
                    : "text-gray-700 hover:bg-gray-50"
                }`}
              >
                <div>
                  <div className="font-semibold">Minimalista Blanco</div>
                  <div className="text-[10px] text-gray-400">Ideal para NDVI y lotes</div>
                </div>
                {currentStyleKey === "canvas" && <span className="text-blue-600 font-bold">✓</span>}
              </button>

              <button
                onClick={() => handleStyleChange("satellite")}
                className={`w-full flex items-center justify-between p-2 rounded-xl text-left cursor-pointer transition-colors ${
                  currentStyleKey === "satellite"
                    ? "bg-blue-50 text-blue-700 font-bold"
                    : "text-gray-700 hover:bg-gray-50"
                }`}
              >
                <div>
                  <div className="font-semibold">Satélite Real HD</div>
                  <div className="text-[10px] text-gray-400">Fotografía satelital + rutas</div>
                </div>
                {currentStyleKey === "satellite" && <span className="text-blue-600 font-bold">✓</span>}
              </button>

              <button
                onClick={() => handleStyleChange("streets")}
                className={`w-full flex items-center justify-between p-2 rounded-xl text-left cursor-pointer transition-colors ${
                  currentStyleKey === "streets"
                    ? "bg-blue-50 text-blue-700 font-bold"
                    : "text-gray-700 hover:bg-gray-50"
                }`}
              >
                <div>
                  <div className="font-semibold">Calles & Catastro</div>
                  <div className="text-[10px] text-gray-400">Red vial y poblados</div>
                </div>
                {currentStyleKey === "streets" && <span className="text-blue-600 font-bold">✓</span>}
              </button>

              <button
                onClick={() => handleStyleChange("osm")}
                className={`w-full flex items-center justify-between p-2 rounded-xl text-left cursor-pointer transition-colors ${
                  currentStyleKey === "osm"
                    ? "bg-blue-50 text-blue-700 font-bold"
                    : "text-gray-700 hover:bg-gray-50"
                }`}
              >
                <div>
                  <div className="font-semibold">OpenStreetMap</div>
                  <div className="text-[10px] text-gray-400">Mapa abierto global</div>
                </div>
                {currentStyleKey === "osm" && <span className="text-blue-600 font-bold">✓</span>}
              </button>

              <button
                onClick={() => handleStyleChange("topo")}
                className={`w-full flex items-center justify-between p-2 rounded-xl text-left cursor-pointer transition-colors ${
                  currentStyleKey === "topo"
                    ? "bg-blue-50 text-blue-700 font-bold"
                    : "text-gray-700 hover:bg-gray-50"
                }`}
              >
                <div>
                  <div className="font-semibold">Relieve & Terreno</div>
                  <div className="text-[10px] text-gray-400">Elevación y topografía</div>
                </div>
                {currentStyleKey === "topo" && <span className="text-blue-600 font-bold">✓</span>}
              </button>
            </div>
          )}
        </div>

      </div>

      {/* Bottom Right: Mapbox Zoom Controls (+ / - / Reset) */}
      <div className="absolute bottom-4 right-4 z-20 flex flex-col items-center gap-1.5 pointer-events-auto">
        <button
          onClick={handleZoomIn}
          title="Acercar mapa"
          className="flex h-8 w-8 items-center justify-center rounded-xl bg-white/95 border border-gray-200 text-gray-700 shadow-sm hover:bg-gray-100 hover:text-gray-900 transition-all cursor-pointer backdrop-blur-md active:scale-95"
        >
          <ZoomIn className="h-4 w-4" />
        </button>

        <button
          onClick={handleZoomOut}
          title="Alejar mapa"
          className="flex h-8 w-8 items-center justify-center rounded-xl bg-white/95 border border-gray-200 text-gray-700 shadow-sm hover:bg-gray-100 hover:text-gray-900 transition-all cursor-pointer backdrop-blur-md active:scale-95"
        >
          <ZoomOut className="h-4 w-4" />
        </button>

        <button
          onClick={zoomToGlobal}
          title="Restablecer a Globo 3D"
          className="flex h-8 w-8 items-center justify-center rounded-xl bg-white/95 border border-gray-200 text-gray-700 shadow-sm hover:bg-gray-100 hover:text-gray-900 transition-all cursor-pointer backdrop-blur-md active:scale-95 mt-1"
        >
          <RotateCcw className="h-4 w-4" />
        </button>
      </div>



      {/* Attribution & Navigation Hint */}
      <div className="absolute bottom-1 right-14 z-10 pointer-events-none text-[10px] text-gray-400 font-sans hidden sm:block">
        Arrastra para navegar • Scroll para hacer zoom
      </div>
    </div>
  );
}
