"use client";

import React, { useState, useRef, useEffect } from "react";
import dynamic from "next/dynamic";
import { FIELDS_DATA, FieldItem } from "@/data/fieldsData";
import FloatingIslandHeader from "@/components/FloatingIslandHeader";
import FieldCardsList from "@/components/FieldCardsList";
import FieldDetailView from "@/components/FieldDetailView";
import WebGpuCosmicGrid from "@/components/WebGpuCosmicGrid";
import TimelapseController from "@/components/timelapse/TimelapseController";
import { useFieldTimelapse } from "@/hooks/useFieldTimelapse";
import { DEMO_TIMELAPSE_MANIFEST } from "@/data/timelapseMockData";
import { Satellite } from "lucide-react";
import gsap from "gsap";
import { useGSAP } from "@gsap/react";
import { TimelapseManifest } from "@/types/terria";

gsap.registerPlugin(useGSAP);

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

// Dynamic import for 3D Three.js canvas to avoid SSR issues
const Planet3D = dynamic(() => import("@/components/Planet3D"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full w-full items-center justify-center bg-white text-gray-600 text-xs font-sans">
      <div className="flex flex-col items-center gap-2">
        <Satellite className="h-6 w-6 animate-spin text-blue-600" />
        <span>Cargando mapa interactivo...</span>
      </div>
    </div>
  ),
});

const Field3DIsoViewer = dynamic(() => import("@/components/Field3DIsoViewer"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full w-full items-center justify-center bg-white text-gray-600 text-xs font-sans">
      <div className="flex flex-col items-center gap-2">
        <Satellite className="h-6 w-6 animate-spin text-blue-600" />
        <span>Cargando maqueta 3D aislada...</span>
      </div>
    </div>
  ),
});

export default function Home() {
  const [selectedField, setSelectedField] = useState<FieldItem>(FIELDS_DATA[0]);
  const [isFieldExpanded, setIsFieldExpanded] = useState(false);
  const [isFieldIsolated3D, setIsFieldIsolated3D] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [backendFields, setBackendFields] = useState<FieldItem[]>(FIELDS_DATA);
  const [timelapseManifest, setTimelapseManifest] = useState<TimelapseManifest>(DEMO_TIMELAPSE_MANIFEST);
  const [backendStatus, setBackendStatus] = useState<"loading" | "connected" | "offline">("loading");

  // Fetch fields and timelapse data from real backend on mount
  useEffect(() => {
    const fetchBackendData = async () => {
      try {
        // 1. Check health
        const health = await fetch(`${API_URL}/health`, { signal: AbortSignal.timeout(3000) });
        if (!health.ok) throw new Error("backend offline");

        setBackendStatus("connected");

        // 2. Fetch fields list
        const fieldsRes = await fetch(`${API_URL}/v1/fields`);
        if (fieldsRes.ok) {
          const fieldsData = await fieldsRes.json();
          // Map backend fields to FieldItem shape (fill optional visual props from mock fallback)
          if (Array.isArray(fieldsData) && fieldsData.length > 0) {
            const mapped: FieldItem[] = fieldsData.map((f: any, idx: number) => ({
              id: f.id,
              name: f.name,
              lat: f.centroid_lat ?? FIELDS_DATA[idx % FIELDS_DATA.length]?.lat ?? -33.12,
              lng: f.centroid_lng ?? FIELDS_DATA[idx % FIELDS_DATA.length]?.lng ?? -64.22,
              hectares: f.area_hectares ?? FIELDS_DATA[idx % FIELDS_DATA.length]?.hectares ?? 100,
              crop: f.primary_crop ?? FIELDS_DATA[idx % FIELDS_DATA.length]?.crop ?? "Maíz",
              ndvi: FIELDS_DATA[idx % FIELDS_DATA.length]?.ndvi ?? 0.55,
              aptitude: FIELDS_DATA[idx % FIELDS_DATA.length]?.aptitude ?? "Alta",
              soilType: FIELDS_DATA[idx % FIELDS_DATA.length]?.soilType ?? "Franco arcilloso",
              status: f.is_published ? "published" : "draft",
              publicSlug: f.public_slug,
            }));
            setBackendFields(mapped);
            setSelectedField(mapped[0]);

            // 3. Fetch timelapses for the first field
            const firstFieldId = mapped[0].id;
            const tlRes = await fetch(`${API_URL}/v1/fields/${firstFieldId}/timelapses`);
            if (tlRes.ok) {
              const datasets = await tlRes.json();
              // Pick first ready/partial dataset
              const readyDataset = datasets.find(
                (d: any) => d.status === "ready" || d.status === "partial"
              );
              if (readyDataset) {
                const manifestRes = await fetch(
                  `${API_URL}/v1/fields/${firstFieldId}/timelapses/${readyDataset.id}`
                );
                if (manifestRes.ok) {
                  const manifest = await manifestRes.json();
                  setTimelapseManifest(manifest);
                }
              }
            }
          }
        }
      } catch {
        // Backend offline — keep mock data, inform user
        setBackendStatus("offline");
        console.info("[TERRIA] Backend not reachable — using demo mock data");
      }
    };

    fetchBackendData();
  }, []);

  // Synchronized timelapse engine across 3D and detail views
  const timelapse = useFieldTimelapse({ manifest: timelapseManifest });

  const pageContainerRef = useRef<HTMLDivElement>(null);
  const mapViewportRef = useRef<HTMLDivElement>(null);
  const cardsPanelRef = useRef<HTMLDivElement>(null);

  // GSAP Smooth Entrance Animation
  useGSAP(
    () => {
      const tl = gsap.timeline({ defaults: { ease: "power3.out" } });

      tl.from(mapViewportRef.current, {
        scale: 0.97,
        autoAlpha: 0,
        duration: 0.6,
      }).from(
        cardsPanelRef.current,
        {
          x: 25,
          autoAlpha: 0,
          duration: 0.6,
        },
        "-=0.4"
      );
    },
    { scope: pageContainerRef }
  );

  const handleSelectField = (field: FieldItem) => {
    setSelectedField(field);
    setIsFieldExpanded(true); // Smoothly expands into the second view (detailed passport)

    if (mapViewportRef.current) {
      gsap.fromTo(
        mapViewportRef.current,
        { scale: 0.988 },
        { scale: 1, duration: 0.4, ease: "power2.out" }
      );
    }
  };

  const handleBackToCatalog = () => {
    setIsFieldExpanded(false);
    setIsFieldIsolated3D(false);

    if (mapViewportRef.current) {
      gsap.fromTo(
        mapViewportRef.current,
        { scale: 0.99 },
        { scale: 1, duration: 0.35, ease: "power2.out" }
      );
    }
  };

  return (
    <div
      ref={pageContainerRef}
      className="relative h-screen max-h-screen w-screen overflow-hidden bg-[#f8fafc] text-gray-900 flex flex-col select-none"
    >
      {/* Subtle WebGPU background canvas */}
      <WebGpuCosmicGrid />

      {/* Dynamic Floating Island Header with GSAP Auto-Hide & Reveal */}
      <FloatingIslandHeader
        onSearchChange={(query) => setSearchQuery(query)}
        selectedField={selectedField}
        totalFields={backendFields.length}
        backendStatus={backendStatus}
      />

      {/* Main Two-Column Layout: Left Map/Planet + Right Field Cards */}
      <main className="relative z-10 flex-1 min-h-0 w-full grid grid-cols-1 lg:grid-cols-12 gap-4 px-4 sm:px-6 pt-16 pb-3 overflow-hidden">
        {/* LEFT COLUMN (7 / 12 cols): Clean 3D Map / Planet or Isolated 3D Field Viewport */}
        <div
          ref={mapViewportRef}
          className="lg:col-span-7 xl:col-span-8 h-full min-h-0 flex flex-col relative rounded-3xl border border-gray-200 bg-white shadow-sm overflow-hidden"
        >
          <div className="relative flex-1 w-full h-full min-h-0">
            {isFieldIsolated3D ? (
              <Field3DIsoViewer
                field={selectedField}
                onBackToMap={() => setIsFieldIsolated3D(false)}
                className="h-full w-full"
              />
            ) : (
              <Planet3D
                embedded={true}
                selectedField={selectedField}
                isExpanded={isFieldExpanded}
                onSelectField={handleSelectField}
                onIsolateField={() => setIsFieldIsolated3D(true)}
                timelapse={timelapse}
                className="h-full w-full"
              />
            )}

            {/* Floating Timelapse Controller dock over the 3D viewport when field is active */}
            {isFieldExpanded && (
              <div className="absolute bottom-4 left-4 right-4 z-30 pointer-events-auto">
                <TimelapseController
                  dates={timelapse.dates}
                  dateIndex={timelapse.dateIndex}
                  onDateIndexChange={timelapse.setDateIndex}
                  timelineState={timelapse.timelineState}
                  isPlaying={timelapse.isPlaying}
                  onTogglePlay={() => timelapse.setIsPlaying(!timelapse.isPlaying)}
                  speed={timelapse.speed}
                  onSpeedChange={timelapse.setSpeed}
                  activeLayer={timelapse.activeLayer}
                  onLayerChange={timelapse.setActiveLayer}
                  onStepNext={timelapse.stepNext}
                  onStepPrev={timelapse.stepPrev}
                  onJumpObservation={timelapse.jumpToObservation}
                />
              </div>
            )}
          </div>
        </div>

        {/* RIGHT COLUMN (5 / 12 cols): Clean White Field Cards Feed or Expanded Detail View */}
        <div
          ref={cardsPanelRef}
          className="lg:col-span-5 xl:col-span-4 h-full min-h-0 flex flex-col overflow-hidden"
        >
          {isFieldExpanded ? (
            <FieldDetailView
              field={selectedField}
              onBack={handleBackToCatalog}
              onToggleIsolate3D={() => setIsFieldIsolated3D(!isFieldIsolated3D)}
              isIsolated3D={isFieldIsolated3D}
              sharedTimelapse={timelapse}
            />
          ) : (
            <FieldCardsList
              selectedField={selectedField}
              onSelectField={handleSelectField}
              filterQuery={searchQuery}
              fields={backendFields}
              className="h-full min-h-0"
            />
          )}
        </div>
      </main>
    </div>
  );
}
