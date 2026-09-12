"use client";

import React, { useEffect, useRef, useState, useCallback } from "react";
// Use MapLibre GL — 100% open source, no API token required, full Mapbox GL JS compatibility
import * as maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { FIELDS_DATA, FieldItem } from "@/data/fieldsData";
import { FIELD_SECTORS_DATA, NEIGHBOR_CADASTRE_PARCELS } from "@/data/sectorsData";
import { useFieldTimelapse } from "@/hooks/useFieldTimelapse";
import { generateParcelsGeoJson, getFieldLotBreakdown } from "@/data/backendParcelsGeoJson";
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

export interface Planet3DProps {
  embedded?: boolean;
  selectedField?: FieldItem;
  isExpanded?: boolean;
  className?: string;
  onSelectField?: (field: FieldItem) => void;
  onIsolateField?: (field: FieldItem) => void;
  timelapse?: ReturnType<typeof useFieldTimelapse>;
  fields?: FieldItem[];
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
  fields,
}: Planet3DProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const markersRef = useRef<maplibregl.Marker[]>([]);

  const [currentStyleKey, setCurrentStyleKey] = useState<FreeMapStyleKey>("satellite");
  const [zoomLevelName, setZoomLevelName] = useState<"global" | "regional" | "parcel">("global");
  const [currentZoom, setCurrentZoom] = useState<number>(2.0);
  const [showStyleMenu, setShowStyleMenu] = useState(false);

  const fieldsList = fields && fields.length > 0 ? fields : FIELDS_DATA;

  // Construct GeoJSON FeatureCollection for field cadastral parcels & crop sectors
  const buildParcelsGeoJson = useCallback(() => {
    const selectedDate = timelapse?.timelineState?.selectedDate || "2024-01-01";
    const activeLayer = (timelapse?.activeLayer as "rgb" | "ndvi" | "weather") || "ndvi";
    return generateParcelsGeoJson(
      selectedDate,
      activeLayer,
      selectedField?.id,
      fieldsList,
      timelapse?.timelineState,
      timelapse?.manifest
    );
  }, [timelapse?.timelineState, timelapse?.activeLayer, timelapse?.manifest, selectedField?.id, fieldsList]);

  // Add parcels layers on map style load
  const addParcelLayers = useCallback(
    (map: maplibregl.Map) => {
      if (!map || !map.isStyleLoaded || !map.isStyleLoaded()) return;
      try {
        const data = buildParcelsGeoJson();
        if (map.getSource("field-parcels")) {
          const src = map.getSource("field-parcels") as maplibregl.GeoJSONSource;
          src.setData(data as any);
          return;
        }

        map.addSource("field-parcels", {
          type: "geojson",
          data: data as any,
        });

        // Layer 1: Surrounding neighbor cadastral lots (authentic OneSoil multi-crop mosaic, non-selectable)
        map.addLayer({
          id: "cadastre-neighbors-fill",
          type: "fill",
          source: "field-parcels",
          filter: ["==", ["get", "kind"], "neighbor"],
          paint: {
            "fill-color": ["get", "color"],
            "fill-opacity": 0.45,
          },
        });

        // Layer 2: Surrounding neighbor cadastral boundaries (crisp parcel fence/road separation)
        map.addLayer({
          id: "cadastre-neighbors-line",
          type: "line",
          source: "field-parcels",
          filter: ["==", ["get", "kind"], "neighbor"],
          paint: {
            "line-color": "#a7a7a0",
            "line-width": 1.2,
            "line-opacity": 0.6,
          },
        });

        // Layer 3: Field Cadastral Perimeter Fill (subtle baseline footprint)
        map.addLayer({
          id: "field-perimeter-fill",
          type: "fill",
          source: "field-parcels",
          filter: ["==", ["get", "kind"], "perimeter"],
          paint: {
            "fill-color": "#1c3a2e",
            "fill-opacity": 0.05,
          },
        });

        // Layer 4: Internal Agronomic Parcels Fill (vibrant NDVI & crop colors, interactive)
        map.addLayer({
          id: "field-parcels-fill",
          type: "fill",
          source: "field-parcels",
          filter: ["==", ["get", "kind"], "lot"],
          paint: {
            "fill-color": ["get", "color"],
            "fill-opacity": 0.58,
          },
        });

        // Layer 5: Crisp cadastral interior division lines between internal lots
        map.addLayer({
          id: "field-parcels-line",
          type: "line",
          source: "field-parcels",
          filter: ["==", ["get", "kind"], "lot"],
          paint: {
            "line-color": "#1c3a2e",
            "line-width": 2.0,
            "line-opacity": 0.9,
          },
        });

        // Layer 6: Whole Field Outer Perimeter boundary line (3.2px dark brand border)
        map.addLayer({
          id: "field-perimeter-line",
          type: "line",
          source: "field-parcels",
          filter: ["==", ["get", "kind"], "perimeter"],
          paint: {
            "line-color": "#12271e",
            "line-width": 3.2,
            "line-opacity": 1.0,
          },
        });

        // Layer 7: Active field outer glow / halo (halo musgo de marca)
        map.addLayer({
          id: "field-active-halo",
          type: "line",
          source: "field-parcels",
          filter: [
            "all",
            ["==", ["get", "kind"], "perimeter"],
            ["==", ["get", "fieldId"], selectedField?.id || ""],
          ],
          paint: {
            "line-color": "#4a6b46",
            "line-width": 7.0,
            "line-opacity": 0.55,
          },
        });

        // Layer 8: Active field crisp chalk border (boundary nube de marca)
        map.addLayer({
          id: "field-active-highlight",
          type: "line",
          source: "field-parcels",
          filter: [
            "all",
            ["==", ["get", "kind"], "perimeter"],
            ["==", ["get", "fieldId"], selectedField?.id || ""],
          ],
          paint: {
            "line-color": "#f4f6f2",
            "line-width": 3.5,
            "line-opacity": 1.0,
          },
        });

        // Layer 9: Native cartographic lot labels with hectares directly on the terrain
        map.addLayer({
          id: "field-parcels-labels",
          type: "symbol",
          source: "field-parcels",
          filter: ["==", ["get", "kind"], "lot"],
          layout: {
            "text-field": [
              "concat",
              ["get", "name"],
              "\n",
              ["to-string", ["get", "hectares"]],
              " ha • NDVI ",
              ["to-string", ["get", "currentNdvi"]]
            ],
            "text-size": 11,
            "text-justify": "center",
            "text-anchor": "center",
            "text-allow-overlap": false,
          },
          paint: {
            "text-color": "#0f172a",
            "text-halo-color": "#ffffff",
            "text-halo-width": 2.5,
          },
        });
      } catch (err) {
        console.warn("Failed to add parcel layers:", err);
      }
    },
    [buildParcelsGeoJson, selectedField]
  );

  // Synchronize GeoJSON source whenever timelapse date or layer changes
  useEffect(() => {
    if (!mapRef.current) return;
    const map = mapRef.current;
    if (!map.isStyleLoaded || !map.isStyleLoaded()) return;
    try {
      const source = map.getSource("field-parcels") as maplibregl.GeoJSONSource | undefined;
      if (source) {
        const data = buildParcelsGeoJson();
        source.setData(data as any);
      } else {
        addParcelLayers(map);
      }
    } catch {
      // Map style or source not ready yet
    }
  }, [buildParcelsGeoJson, addParcelLayers]);

  const isTransitioningRef = useRef(false);

  const triggerZoomAnd3D = useCallback(
    (field: FieldItem) => {
      if (!mapRef.current || isTransitioningRef.current) return;
      isTransitioningRef.current = true;

      if (onSelectField) {
        onSelectField(field);
      }

      const map = mapRef.current;

      // Smooth cinematic camera swoop down to parcel level
      map.flyTo({
        center: [field.lng, field.lat],
        zoom: 15.6,
        pitch: 54,
        bearing: -12,
        duration: 1600,
        essential: true,
      });

      // Right as camera reaches ground level, transition to 3D isolated representation
      const timer = setTimeout(() => {
        if (onIsolateField) {
          onIsolateField(field);
        }
        isTransitioningRef.current = false;
      }, 1500);

      return () => clearTimeout(timer);
    },
    [onSelectField, onIsolateField]
  );

  const triggerZoomAnd3DRef = useRef(triggerZoomAnd3D);
  useEffect(() => {
    triggerZoomAnd3DRef.current = triggerZoomAnd3D;
  }, [triggerZoomAnd3D]);

  // Initialize MapLibre GL (no token needed — 100% free!)
  useEffect(() => {
    if (!mapContainerRef.current) return;

    const initialCenter: [number, number] = selectedField
      ? [selectedField.lng, selectedField.lat]
      : [-64.215, -33.115];

    const initialZoom = 14.6;
    const initialPitch = 42;

    const styleToUse = OPEN_MAP_STYLES[currentStyleKey] as any;

    const map = new maplibregl.Map({
      container: mapContainerRef.current,
      style: styleToUse,
      center: initialCenter,
      zoom: initialZoom,
      pitch: initialPitch,
      maxZoom: 16.8,
      minZoom: 1.5,
      attributionControl: false,
    } as maplibregl.MapOptions);

    mapRef.current = map;

    // Ensure map resizes properly as flex/grid layout computes
    const resizeTimeout = setTimeout(() => {
      map.resize();
    }, 150);

    const ro = new ResizeObserver(() => {
      map.resize();
    });
    ro.observe(mapContainerRef.current);

    // Apply sky atmosphere + globe projection (MapLibre native)
    const applySkyAndAtmosphere = () => {
      if (!map.isStyleLoaded || !map.isStyleLoaded()) return;
      try {
        // Set vertical-perspective projection — pseudo-globe visual effect
        (map as any).setProjection({ type: "vertical-perspective" });
      } catch { /* noop — projection API not ready yet */ }
      try {
        // setSky gives white/blue atmosphere halo around the globe
        map.setSky({
          "sky-color": "#fafaf6",
          "sky-horizon-blend": 0.5,
          "horizon-color": "#f4f6f2",
          "horizon-fog-blend": 0.05,
          "atmosphere-blend": 0.6,
        } as any);
      } catch {
        // setSky not supported on this style — CSS fallback handles background color
      }
      addParcelLayers(map);
    };

    map.on("style.load", applySkyAndAtmosphere);
    if (map.isStyleLoaded && map.isStyleLoaded()) {
      applySkyAndAtmosphere();
    }

    // Interactive click: ONLY trigger selection on our loaded portfolio fields
    map.on("click", (e: maplibregl.MapMouseEvent) => {
      if (!map.isStyleLoaded || !map.isStyleLoaded()) return;
      try {
        const queryLayers: string[] = [];
        if (map.getLayer("field-parcels-fill")) queryLayers.push("field-parcels-fill");
        if (map.getLayer("field-perimeter-fill")) queryLayers.push("field-perimeter-fill");
        if (map.getLayer("field-parcels-labels")) queryLayers.push("field-parcels-labels");
        if (queryLayers.length === 0) return;
        const features = map.queryRenderedFeatures(e.point, { layers: queryLayers });
        if (features && features[0]) {
          const isPortfolio = features[0].properties?.isPortfolio;
          if (isPortfolio) {
            const fieldId = features[0].properties?.fieldId;
            const match = fieldsList.find((f) => f.id === fieldId);
            if (match) {
              triggerZoomAnd3DRef.current(match);
            }
          }
        }
      } catch {
        // Safe ignore
      }
    });

    // Mousemove: stable pointer cursor on portfolio fields without moving popups (no jitter!)
    map.on("mousemove", (e: maplibregl.MapMouseEvent) => {
      if (!map.isStyleLoaded || !map.isStyleLoaded()) return;
      try {
        const activeLayer = map.getLayer("field-parcels-fill");
        const cadastreLayer = map.getLayer("cadastre-neighbors-fill");
        if (!activeLayer && !cadastreLayer) return;

        const layersToQuery: string[] = [];
        if (activeLayer) layersToQuery.push("field-parcels-fill");
        if (map.getLayer("field-perimeter-fill")) layersToQuery.push("field-perimeter-fill");
        if (map.getLayer("field-parcels-labels")) layersToQuery.push("field-parcels-labels");
        if (cadastreLayer) layersToQuery.push("cadastre-neighbors-fill");

        const features = map.queryRenderedFeatures(e.point, { layers: layersToQuery });

        if (features && features[0]) {
          const f = features[0];
          const props = f.properties || {};
          const isPortfolio = props.isPortfolio === true || props.isPortfolio === "true";
          map.getCanvas().style.cursor = isPortfolio ? "pointer" : "default";
        } else {
          map.getCanvas().style.cursor = "";
        }
      } catch {
        // Safe ignore
      }
    });

    map.on("mouseout", () => {
      map.getCanvas().style.cursor = "";
    });

  // Track Zoom level dynamically + switch projection for globe/map feel
  map.on("zoom", () => {
    const z = map.getZoom();
    setCurrentZoom(z);
    if (z < 5.0) {
      setZoomLevelName("global");
      // Globe-like perspective in world view
      try { map.setProjection({ type: "vertical-perspective" } as any); } catch { /* noop */ }
    } else if (z < 11.5) {
      setZoomLevelName("regional");
      // Flat Mercator for regional accuracy
      try { map.setProjection({ type: "mercator" } as any); } catch { /* noop */ }
    } else {
      setZoomLevelName("parcel");
      // Mercator for precise parcel geometry at field level
      try { map.setProjection({ type: "mercator" } as any); } catch { /* noop */ }
    }
  });

    return () => {
      clearTimeout(resizeTimeout);
      ro.disconnect();
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // Synchronize interactive field markers with dynamic fieldsList
  useEffect(() => {
    if (!mapRef.current) return;
    const map = mapRef.current;

    markersRef.current.forEach((m) => m.remove());
    markersRef.current = [];

    fieldsList.forEach((field) => {
      // If we are at parcel zoom (>= 13.5) and this is selectedField,
      // hide the general field badge so it doesn't overlap the individual lot badges!
      if (currentZoom >= 13.5 && selectedField?.id === field.id) {
        return;
      }

      const el = document.createElement("div");
      el.className =
        "terria-field-marker group cursor-pointer select-none flex items-center gap-2 rounded-full bg-papel border-2 border-musgo/50 hover:border-musgo hover:bg-nube px-3.5 py-1.5 text-xs font-bold text-bosque shadow-md hover:shadow-lg transition-colors";

      el.style.pointerEvents = "auto";
      el.style.cursor = "pointer";
      el.style.transform = "none";
      el.title = `Clic para hacer zoom en ${field.name} y abrir maqueta 3D`;

      el.innerHTML = `
        <span class="flex h-2.5 w-2.5 rounded-full bg-musgo animate-pulse shrink-0 pointer-events-none"></span>
        <div class="flex flex-col text-left leading-tight pointer-events-none">
          <span class="truncate max-w-[130px] font-bold text-bosque tracking-tight">${field.name}</span>
          <span class="text-[10px] font-mono text-musgo font-semibold">${field.hectares} ha</span>
        </div>
        <span class="terria-3d-tag flex items-center gap-1 rounded-full bg-bosque text-nube font-mono font-bold px-2 py-0.5 text-[10px] shadow-xs group-hover:bg-musgo transition-colors pointer-events-none">
          <svg class="w-3 h-3 text-nube" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"/></svg>
          <span>3D</span>
        </span>
      `;

      el.addEventListener("click", (e) => {
        e.stopPropagation();
        const tag = el.querySelector(".terria-3d-tag");
        if (tag) {
          tag.textContent = "3D...";
        }
        triggerZoomAnd3D(field);
      });

      const marker = new maplibregl.Marker({ element: el, anchor: "bottom" })
        .setLngLat([field.lng, field.lat])
        .addTo(map);

      markersRef.current.push(marker);
    });

    return () => {
      markersRef.current.forEach((m) => m.remove());
      markersRef.current = [];
    };
  }, [fieldsList, currentZoom, selectedField, triggerZoomAnd3D]);

  // Camera focus handlers for lots and fields
  const handleFocusLot = useCallback((lng: number, lat: number) => {
    if (!mapRef.current) return;
    mapRef.current.flyTo({
      center: [lng, lat],
      zoom: 15.2,
      pitch: 45,
      bearing: -10,
      duration: 1000,
      essential: true,
    });
  }, []);

  const handleFocusField = useCallback(() => {
    if (!mapRef.current || !selectedField) return;
    mapRef.current.flyTo({
      center: [selectedField.lng, selectedField.lat],
      zoom: 14.6,
      pitch: 42,
      bearing: -10,
      duration: 1200,
      essential: true,
    });
  }, [selectedField]);

  // Parcel Lot Hectare Floating Badges (Visible on map over active field ONLY at parcel scale >= 13.0)
  const lotMarkersRef = useRef<maplibregl.Marker[]>([]);

  useEffect(() => {
    if (!mapRef.current || !selectedField) return;
    const map = mapRef.current;

    // Clean previous lot markers
    lotMarkersRef.current.forEach((m) => m.remove());
    lotMarkersRef.current = [];

    // ONLY show lot breakdown markers at parcel zoom level (>= 13.0)
    // At regional zoom (< 13.0), only the main field marker is shown to prevent collisions!
    if (currentZoom < 13.0) {
      return;
    }

    const lots = getFieldLotBreakdown(
      selectedField,
      timelapse?.timelineState,
      timelapse?.timelineState?.selectedDate
    );

    lots.forEach((lot) => {
      const el = document.createElement("div");
      el.className = "terria-lot-badge cursor-pointer select-none";
      el.style.pointerEvents = "auto";
      el.style.cursor = "pointer";
      el.title = `Clic para hacer zoom en ${lot.name} y abrir maqueta 3D`;
      el.innerHTML = `
        <div style="
          display: flex;
          align-items: center;
          gap: 6px;
          background: rgba(255, 255, 255, 0.98);
          border: 1.5px solid ${lot.color};
          padding: 3px 8px;
          border-radius: 9999px;
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
          font-family: system-ui, sans-serif;
          white-space: nowrap;
          pointer-events: none;
        ">
          <span style="
            display: inline-block;
            width: 7px;
            height: 7px;
            border-radius: 9999px;
            background: ${lot.color};
          "></span>
          <span style="font-size: 11px; font-weight: 800; color: #1c3a2e;">${lot.name}</span>
          <span style="
            background: #f4f6f2;
            color: #1c3a2e;
            font-size: 10px;
            font-weight: 800;
            padding: 1px 5px;
            border-radius: 6px;
          ">${lot.hectares} ha</span>
          <span style="
            background: ${lot.color};
            color: #ffffff;
            font-size: 9px;
            font-weight: 800;
            padding: 1px 5px;
            border-radius: 6px;
          ">${lot.ndvi.toFixed(2)}</span>
          <span style="
            display: flex;
            align-items: center;
            gap: 3px;
            background: #1c3a2e;
            color: #f4f6f2;
            font-size: 9px;
            font-weight: 800;
            padding: 1px 5px;
            border-radius: 6px;
          ">
            <svg style="width: 10px; height: 10px;" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"/></svg>
            3D
          </span>
        </div>
      `;

      el.addEventListener("click", (e) => {
        e.stopPropagation();
        triggerZoomAnd3D(selectedField);
      });

      const marker = new maplibregl.Marker({ element: el, anchor: "center" })
        .setLngLat([lot.centroid[0], lot.centroid[1]])
        .addTo(map);

      lotMarkersRef.current.push(marker);
    });

    return () => {
      lotMarkersRef.current.forEach((m) => m.remove());
      lotMarkersRef.current = [];
    };
  }, [selectedField, currentZoom, timelapse?.timelineState, triggerZoomAnd3D]);

  // React to field selection: Smoothly fly camera to field with parcel zoom & update active highlight
  useEffect(() => {
    if (!mapRef.current || !selectedField) return;
    const map = mapRef.current;

    // Fly camera directly to parcel level zoom so lots and hectares are clearly visible
    const targetZoom = isExpanded ? 15.0 : 14.6;
    const targetPitch = 42;

    map.flyTo({
      center: [selectedField.lng, selectedField.lat],
      zoom: targetZoom,
      pitch: targetPitch,
      bearing: isExpanded ? -15 : -10,
      essential: true,
      duration: 2200,
    });

    // Update active highlight & halo glow filters safely
    if (map.isStyleLoaded && map.isStyleLoaded()) {
      try {
        if (map.getLayer("field-active-highlight")) {
          map.setFilter("field-active-highlight", [
            "all",
            ["==", ["get", "kind"], "perimeter"],
            ["==", ["get", "fieldId"], selectedField.id],
          ]);
        }
        if (map.getLayer("field-active-halo")) {
          map.setFilter("field-active-halo", [
            "all",
            ["==", ["get", "kind"], "perimeter"],
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
    <div className={`relative w-full h-full overflow-hidden select-none bg-nube ${className}`}>
      {/* MapLibre GL WebGL Map Container */}
      <div ref={mapContainerRef} className="absolute inset-0 w-full h-full" />

      {/* Top Left: 3D Button, Scale/Altitude, and NDVI Colors */}
      <div className="absolute top-3 left-3 z-20 pointer-events-auto flex flex-col gap-1.5 items-start">
        {/* Botón para ver en 3D */}
        {onIsolateField && selectedField && (
          <button
            onClick={() => onIsolateField(selectedField)}
            title="Ver maqueta 3D aislada"
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-xs font-bold bg-papel/95 text-bosque hover:bg-musgo/10 transition-all cursor-pointer border border-musgo/40 shadow-sm backdrop-blur-md"
          >
            <Box className="h-3.5 w-3.5 text-musgo" />
            <span>Ver en 3D</span>
          </button>
        )}

        {/* Current Scale & Altitude Pill */}
        <div className="flex items-center gap-2 rounded-full bg-papel/90 border border-piedra-soft/80 px-3 py-1 shadow-xs backdrop-blur-sm text-[11px] text-piedra font-sans w-fit">
          <span
            className={`h-1.5 w-1.5 rounded-full shrink-0 ${
              zoomLevelName === "parcel"
                ? "bg-musgo animate-pulse"
                : zoomLevelName === "regional"
                ? "bg-cielo-deep"
                : "bg-piedra"
            }`}
          />
          <span className="font-medium text-bosque/80">
            {zoomLevelName === "parcel"
              ? `Nivel Parcela (Zoom ${currentZoom.toFixed(1)} • Calles y Catastro)`
              : zoomLevelName === "regional"
              ? `Nivel Regional (Zoom ${currentZoom.toFixed(1)} • Rutas y Ciudades)`
              : `Órbita Global (Zoom ${currentZoom.toFixed(1)} • Planeta 3D)`}
          </span>
        </div>

        {/* Leyenda NDVI: únicamente NDVI y los colores, englobado en un rectángulo con bordes super redondeados */}
        {currentZoom >= 4.0 && (
          <div className="flex items-center gap-2.5 rounded-full bg-papel/95 border border-piedra-soft px-3.5 py-1.5 shadow-sm backdrop-blur-md text-[11px] text-bosque/70 w-fit animate-in fade-in duration-300">
            <span className="font-bold text-bosque">NDVI:</span>
            <div className="flex items-center gap-1 font-medium">
              <span className="inline-block h-2.5 w-2.5 rounded-full bg-[#c9b28a] border border-black/10 shadow-xs" />
              <span>&lt;0.35</span>
            </div>
            <div className="flex items-center gap-1 font-medium">
              <span className="inline-block h-2.5 w-2.5 rounded-full bg-[#a9b183] border border-black/10 shadow-xs" />
              <span>0.50</span>
            </div>
            <div className="flex items-center gap-1 font-medium">
              <span className="inline-block h-2.5 w-2.5 rounded-full bg-[#8a9a6b] border border-black/10 shadow-xs" />
              <span>0.65</span>
            </div>
            <div className="flex items-center gap-1 font-medium">
              <span className="inline-block h-2.5 w-2.5 rounded-full bg-[#637e52] border border-black/10 shadow-xs" />
              <span>0.78</span>
            </div>
            <div className="flex items-center gap-1 font-medium">
              <span className="inline-block h-2.5 w-2.5 rounded-full bg-[#1c3a2e] border border-black/10 shadow-xs" />
              <span>&gt;0.85</span>
            </div>
          </div>
        )}
      </div>

      {/* Top Right: Map Style Selector (Calles / Satélite / Positron) & Token */}
      <div className="absolute top-3 right-3 z-20 pointer-events-auto flex items-center gap-1.5">
        <div className="relative">
          <button
            onClick={() => setShowStyleMenu(!showStyleMenu)}
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-full bg-papel/95 border border-piedra-soft text-xs font-semibold text-bosque/80 shadow-sm backdrop-blur-md hover:bg-nube transition-colors cursor-pointer"
          >
            <Layers className="h-3.5 w-3.5 text-musgo" />
            <span>{OPEN_MAP_STYLES[currentStyleKey].name}</span>
          </button>

          {showStyleMenu && (
            <div className="absolute right-0 top-10 w-52 rounded-2xl bg-papel border border-piedra-soft p-2 shadow-xl backdrop-blur-md space-y-1 text-xs z-30">
              <div className="px-2 py-1 text-[10px] font-bold text-piedra uppercase tracking-wider">
                Capas Gratuitas (Sin API Key)
              </div>
              <button
                onClick={() => handleStyleChange("canvas")}
                className={`w-full flex items-center justify-between p-2 rounded-xl text-left cursor-pointer transition-colors ${
                  currentStyleKey === "canvas"
                    ? "bg-musgo/10 text-musgo font-bold"
                    : "text-bosque/70 hover:bg-nube"
                }`}
              >
                <div>
                  <div className="font-semibold">Minimalista Blanco</div>
                  <div className="text-[10px] text-piedra">Ideal para NDVI y lotes</div>
                </div>
                {currentStyleKey === "canvas" && <span className="text-musgo font-bold">✓</span>}
              </button>

              <button
                onClick={() => handleStyleChange("satellite")}
                className={`w-full flex items-center justify-between p-2 rounded-xl text-left cursor-pointer transition-colors ${
                  currentStyleKey === "satellite"
                    ? "bg-musgo/10 text-musgo font-bold"
                    : "text-bosque/70 hover:bg-nube"
                }`}
              >
                <div>
                  <div className="font-semibold">Satélite Real HD</div>
                  <div className="text-[10px] text-piedra">Fotografía satelital + rutas</div>
                </div>
                {currentStyleKey === "satellite" && <span className="text-musgo font-bold">✓</span>}
              </button>

              <button
                onClick={() => handleStyleChange("streets")}
                className={`w-full flex items-center justify-between p-2 rounded-xl text-left cursor-pointer transition-colors ${
                  currentStyleKey === "streets"
                    ? "bg-musgo/10 text-musgo font-bold"
                    : "text-bosque/70 hover:bg-nube"
                }`}
              >
                <div>
                  <div className="font-semibold">Calles & Catastro</div>
                  <div className="text-[10px] text-piedra">Red vial y poblados</div>
                </div>
                {currentStyleKey === "streets" && <span className="text-musgo font-bold">✓</span>}
              </button>

              <button
                onClick={() => handleStyleChange("osm")}
                className={`w-full flex items-center justify-between p-2 rounded-xl text-left cursor-pointer transition-colors ${
                  currentStyleKey === "osm"
                    ? "bg-musgo/10 text-musgo font-bold"
                    : "text-bosque/70 hover:bg-nube"
                }`}
              >
                <div>
                  <div className="font-semibold">OpenStreetMap</div>
                  <div className="text-[10px] text-piedra">Mapa abierto global</div>
                </div>
                {currentStyleKey === "osm" && <span className="text-musgo font-bold">✓</span>}
              </button>

              <button
                onClick={() => handleStyleChange("topo")}
                className={`w-full flex items-center justify-between p-2 rounded-xl text-left cursor-pointer transition-colors ${
                  currentStyleKey === "topo"
                    ? "bg-musgo/10 text-musgo font-bold"
                    : "text-bosque/70 hover:bg-nube"
                }`}
              >
                <div>
                  <div className="font-semibold">Relieve & Terreno</div>
                  <div className="text-[10px] text-piedra">Elevación y topografía</div>
                </div>
                {currentStyleKey === "topo" && <span className="text-musgo font-bold">✓</span>}
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
          className="flex h-8 w-8 items-center justify-center rounded-xl bg-papel/95 border border-piedra-soft text-bosque/70 shadow-sm hover:bg-nube hover:text-bosque transition-all cursor-pointer backdrop-blur-md active:scale-95"
        >
          <ZoomIn className="h-4 w-4" />
        </button>

        <button
          onClick={handleZoomOut}
          title="Alejar mapa"
          className="flex h-8 w-8 items-center justify-center rounded-xl bg-papel/95 border border-piedra-soft text-bosque/70 shadow-sm hover:bg-nube hover:text-bosque transition-all cursor-pointer backdrop-blur-md active:scale-95"
        >
          <ZoomOut className="h-4 w-4" />
        </button>

        <button
          onClick={zoomToGlobal}
          title="Restablecer a Globo 3D"
          className="flex h-8 w-8 items-center justify-center rounded-xl bg-papel/95 border border-piedra-soft text-bosque/70 shadow-sm hover:bg-nube hover:text-bosque transition-all cursor-pointer backdrop-blur-md active:scale-95 mt-1"
        >
          <RotateCcw className="h-4 w-4" />
        </button>
      </div>



      {/* Attribution & Navigation Hint */}
      <div className="absolute bottom-1 right-14 z-10 pointer-events-none text-[10px] text-piedra font-sans hidden sm:block">
        Arrastra para navegar • Scroll para hacer zoom
      </div>
    </div>
  );
}
