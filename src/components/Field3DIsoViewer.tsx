"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import gsap from "gsap";
import { FieldItem } from "@/data/fieldsData";
import { FIELD_SECTORS_DATA, ParcelSector } from "@/data/sectorsData";
import {
  getNdviRampColor,
  getTempRampColor,
  getSimulatedParcelNdvi,
} from "@/data/backendParcelsGeoJson";
import {
  ArrowLeft,
  Layers,
  Sparkles,
  Droplets,
  TrendingUp,
  MapPin,
  Maximize2,
  RotateCcw,
  CheckCircle2,
  Compass,
  Box,
  Eye,
} from "lucide-react";

export interface Field3DIsoViewerProps {
  field: FieldItem;
  onBackToMap: () => void;
  timelapse?: any;
  className?: string;
}

export default function Field3DIsoViewer({
  field,
  onBackToMap,
  timelapse,
  className = "",
}: Field3DIsoViewerProps) {
  const mountRef = useRef<HTMLDivElement>(null);
  const controlsRef = useRef<OrbitControls | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const sceneRef = useRef<THREE.Group | null>(null);

  // Sector meshes ref for dynamic color updates without scene rebuild
  const sectorMeshesRef = useRef<
    {
      id: string;
      mesh: THREE.Mesh;
      beacon: THREE.Mesh;
      pole: THREE.Mesh;
      sector: ParcelSector;
    }[]
  >([]);

  const rawSectors = FIELD_SECTORS_DATA[field.id];

  // Dynamic sector computation evaluated for current timelapse date / state
  const sectors: ParcelSector[] = useMemo(() => {
    // 1. Determine progress across timeline
    let timelineProgress = 0.5;
    if (timelapse?.dates && timelapse.dates.length > 1) {
      timelineProgress = Math.max(
        0,
        Math.min(1, (timelapse.dateIndex ?? 0) / (timelapse.dates.length - 1))
      );
    }

    // 2. Backend observed NDVI from Sentinel-2
    let backendObservedNdvi: number | null = null;
    if (timelapse?.timelineState?.satellite?.usable) {
      const meanVal = timelapse.timelineState.satellite.ndvi?.mean?.value;
      if (typeof meanVal === "number" && !isNaN(meanVal)) {
        backendObservedNdvi = meanVal;
      }
    }

    // 3. Weather variables
    let activeTemp = 24.0;
    let activeRain = 0.0;
    if (timelapse?.timelineState?.weather) {
      const w = timelapse.timelineState.weather;
      if (w.temperatureMax?.value != null) activeTemp = w.temperatureMax.value;
      if (w.precipitationDay?.value != null) activeRain = w.precipitationDay.value;
    }

    const activeLayer: string = timelapse?.activeLayer || "ndvi";

    const baseList: ParcelSector[] =
      rawSectors && rawSectors.length > 0
        ? rawSectors
        : [
            {
              id: `${field.id}-sec-1`,
              name: `Lote 1 — ${field.primaryCrop || field.crop || "Maíz Tardío"}`,
              hectares: Number((field.hectares * 0.48).toFixed(1)),
              crop: field.primaryCrop || field.crop || "Maíz Tardío",
              variety: "Híbrido Alto Rinde",
              ndvi: field.ndvi ?? 0.76,
              moisturePercent: 82,
              expectedYield: "112 qq/ha",
              soilHorizon: "Hapludol Típico Profundo",
              color: "#637e52",
              offsets: [
                [0.012, -0.012],
                [0.012, 0.012],
                [0.001, 0.012],
                [0.001, -0.012],
                [0.012, -0.012],
              ],
            },
            {
              id: `${field.id}-sec-2`,
              name: "Lote 2 — Soja de 1ra",
              hectares: Number((field.hectares * 0.32).toFixed(1)),
              crop: "Soja de 1ra",
              variety: "Grupo IV Corto",
              ndvi: Math.max(0.25, parseFloat(((field.ndvi ?? 0.76) - 0.06).toFixed(2))),
              moisturePercent: 78,
              expectedYield: "44 qq/ha",
              soilHorizon: "Horizonte Árgico a 40cm",
              color: "#8a9a6b",
              offsets: [
                [0.001, -0.012],
                [0.001, 0.0],
                [-0.012, 0.0],
                [-0.012, -0.012],
                [0.001, -0.012],
              ],
            },
            {
              id: `${field.id}-sec-3`,
              name: "Lote 3 — Trigo / Cobertura",
              hectares: Number((field.hectares * 0.20).toFixed(1)),
              crop: "Trigo / Cobertura",
              variety: "Ciclo Intermedio",
              ndvi: Math.max(0.20, parseFloat(((field.ndvi ?? 0.76) - 0.14).toFixed(2))),
              moisturePercent: 72,
              expectedYield: "38 qq/ha",
              soilHorizon: "Textura Franco-Limosa",
              color: "#a9b183",
              offsets: [
                [0.001, 0.0],
                [0.001, 0.012],
                [-0.012, 0.012],
                [-0.012, 0.0],
                [0.001, 0.0],
              ],
            },
          ];

    return baseList.map((sec, idx) => {
      let parcelNdvi = sec.ndvi;

      if (backendObservedNdvi != null) {
        // Real Sentinel-2 satellite observation on this date
        const variance = idx === 0 ? 1.03 : idx === 1 ? 0.98 : 0.93;
        parcelNdvi = Math.max(0.12, Math.min(0.95, backendObservedNdvi * variance));
      } else if (timelapse) {
        // Interpolated phenological growth curve
        const curveVal = getSimulatedParcelNdvi(sec.ndvi, sec.crop, timelineProgress);
        const variance = idx === 0 ? 0.03 : idx === 1 ? -0.02 : -0.05;
        parcelNdvi = Math.max(0.15, Math.min(0.92, curveVal + variance));
      }

      // Compute dynamic color depending on active layer
      let sectorColor = getNdviRampColor(parcelNdvi);

      if (activeLayer === "weather") {
        sectorColor = getTempRampColor(activeTemp + (idx - 1) * 0.8);
      } else if (activeLayer === "rgb") {
        if (parcelNdvi > 0.7) {
          sectorColor = idx === 0 ? "#244a2c" : "#2d5435";
        } else if (parcelNdvi > 0.45) {
          sectorColor = idx === 0 ? "#506d39" : "#5d7a42";
        } else if (parcelNdvi > 0.3) {
          sectorColor = "#8c874f";
        } else {
          sectorColor = "#9c8157";
        }
      }

      // Dynamic moisture based on rain events & phenology
      const baseMoisture = sec.moisturePercent || 76;
      const computedMoisture = Math.min(
        98,
        Math.max(
          35,
          Math.round(
            baseMoisture +
              (activeRain > 0 ? activeRain * 2.2 : -4 + Math.sin(timelineProgress * Math.PI) * 8) +
              (idx === 0 ? 3 : idx === 2 ? -3 : 0)
          )
        )
      );

      // Dynamic estimated yield based on current NDVI
      let computedYield = sec.expectedYield;
      if (parcelNdvi > 0.8) {
        computedYield = `+14% sobre histórico (${sec.expectedYield})`;
      } else if (parcelNdvi < 0.4) {
        computedYield = "Madurez / Cosecha";
      }

      return {
        ...sec,
        ndvi: parseFloat(parcelNdvi.toFixed(2)),
        color: sectorColor,
        moisturePercent: computedMoisture,
        expectedYield: computedYield,
      };
    });
  }, [
    field,
    rawSectors,
    timelapse?.dateIndex,
    timelapse?.dates,
    timelapse?.timelineState,
    timelapse?.activeLayer,
  ]);

  const sectorsRef = useRef<ParcelSector[]>(sectors);

  const [activeSector, setActiveSector] = useState<ParcelSector>(sectors[0] || null);

  // Switch active sector when field changes
  useEffect(() => {
    if (sectors.length > 0) {
      setActiveSector(sectors[0]);
    }
  }, [field.id]);

  // Smooth color tweening on timelapse change without recreating 3D scene
  useEffect(() => {
    sectorsRef.current = sectors;

    if (!sectorMeshesRef.current || sectorMeshesRef.current.length === 0) return;

    sectors.forEach((sec) => {
      const item = sectorMeshesRef.current.find((m) => m.id === sec.id);
      if (item) {
        const targetColor = new THREE.Color(sec.color);

        // Smoothly interpolate mesh surface color
        gsap.to((item.mesh.material as THREE.MeshStandardMaterial).color, {
          r: targetColor.r,
          g: targetColor.g,
          b: targetColor.b,
          duration: 0.35,
          ease: "power2.out",
        });

        // Smoothly interpolate beacon sphere color
        gsap.to((item.beacon.material as THREE.MeshBasicMaterial).color, {
          r: targetColor.r,
          g: targetColor.g,
          b: targetColor.b,
          duration: 0.35,
          ease: "power2.out",
        });

        item.sector = sec;
        item.mesh.userData = { sector: sec };
      }
    });

    // Keep activeSector synchronized with latest sector metrics
    setActiveSector((prev) => {
      if (!prev) return sectors[0] || null;
      const found = sectors.find((s) => s.id === prev.id);
      return found || sectors[0] || null;
    });
  }, [sectors]);

  const [showLayers, setShowLayers] = useState({
    ndvi: true,
    soilStrata: true,
    contours: true,
    furrows: true,
  });

  // Track projected screen positions for floating 3D pins
  const [projectedPins, setProjectedPins] = useState<
    { sector: ParcelSector; x: number; y: number; visible: boolean }[]
  >([]);

  const pinWorldPositions = useRef<{ sector: ParcelSector; pos: THREE.Vector3 }[]>([]);

  useEffect(() => {
    if (!mountRef.current) return;
    const container = mountRef.current;
    const width = container.clientWidth || 800;
    const height = container.clientHeight || 600;

    // 1. Scene
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xf4f6f2);

    // 2. Camera: Isometric-like high angle
    const camera = new THREE.PerspectiveCamera(40, width / height, 0.1, 1000);
    camera.position.set(11, 10, 15);
    cameraRef.current = camera;

    // 3. Renderer
    const renderer = new THREE.WebGLRenderer({
      antialias: true,
      powerPreference: "high-performance",
    });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFShadowMap;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.15;
    container.appendChild(renderer.domElement);

    // 4. OrbitControls
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.maxPolarAngle = Math.PI / 2.05; // don't go below horizon
    controls.minDistance = 6;
    controls.maxDistance = 35;
    controls.target.set(0, 0.5, 0);
    controlsRef.current = controls;

    // 5. Lighting (Crisp architectural diorama lighting)
    const ambientLight = new THREE.AmbientLight(0xffffff, 2.0);
    scene.add(ambientLight);

    const sunLight = new THREE.DirectionalLight(0xffffff, 1.2);
    sunLight.position.set(12, 22, 14);
    sunLight.castShadow = true;
    sunLight.shadow.mapSize.width = 2048;
    sunLight.shadow.mapSize.height = 2048;
    sunLight.shadow.camera.near = 0.5;
    sunLight.shadow.camera.far = 60;
    sunLight.shadow.camera.left = -12;
    sunLight.shadow.camera.right = 12;
    sunLight.shadow.camera.top = 12;
    sunLight.shadow.camera.bottom = -12;
    sunLight.shadow.bias = -0.0005;
    scene.add(sunLight);

    const fillLight = new THREE.DirectionalLight(0xf4f6f2, 0.5);
    fillLight.position.set(-15, 8, -12);
    scene.add(fillLight);

    // 6. Master Model Group
    const modelGroup = new THREE.Group();
    scene.add(modelGroup);
    sceneRef.current = modelGroup;

    // Smooth Entrance animation (Lifting from map)
    modelGroup.position.y = -3.5;
    modelGroup.scale.set(0.7, 0.7, 0.7);
    gsap.to(modelGroup.position, {
      y: 0,
      duration: 1.0,
      ease: "power3.out",
    });
    gsap.to(modelGroup.scale, {
      x: 1,
      y: 1,
      z: 1,
      duration: 1.0,
      ease: "power3.out",
    });

    // 7. Base pedestal shadow receiver
    const floorGeo = new THREE.PlaneGeometry(60, 60);
    const floorMat = new THREE.ShadowMaterial({ opacity: 0.12 });
    const floor = new THREE.Mesh(floorGeo, floorMat);
    floor.rotation.x = -Math.PI / 2;
    floor.position.y = -2.85;
    floor.receiveShadow = true;
    scene.add(floor);

    // 8. Construct 3D Soil Strata & Crop Sectors
    const worldPins: { sector: ParcelSector; pos: THREE.Vector3 }[] = [];

    // Base dimensions for the field slab
    const slabWidth = 11.0;
    const slabLength = 11.0;
    const slabDepth = 2.8;

    // Subsurface Soil Strata (Corte Transversal)
    const strataGroup = new THREE.Group();
    modelGroup.add(strataGroup);

    // Horizon A: Top arable layer (0 to -0.6) - Dark organic loam
    const hAGeo = new THREE.BoxGeometry(slabWidth, 0.6, slabLength);
    const hAMat = new THREE.MeshStandardMaterial({
      color: 0x3d2817,
      roughness: 0.9,
    });
    const hAMesh = new THREE.Mesh(hAGeo, hAMat);
    hAMesh.position.y = -0.3;
    hAMesh.castShadow = true;
    hAMesh.receiveShadow = true;
    strataGroup.add(hAMesh);

    // Horizon B: Clay-loam subsoil (-0.6 to -1.8) - Warm brown clay
    const hBGeo = new THREE.BoxGeometry(slabWidth, 1.2, slabLength);
    const hBMat = new THREE.MeshStandardMaterial({
      color: 0x6b4423,
      roughness: 0.85,
    });
    const hBMesh = new THREE.Mesh(hBGeo, hBMat);
    hBMesh.position.y = -1.2;
    hBMesh.castShadow = true;
    hBMesh.receiveShadow = true;
    strataGroup.add(hBMesh);

    // Horizon C: Mineral/sandy substratum (-1.8 to -2.8) - Ochre limestone
    const hCGeo = new THREE.BoxGeometry(slabWidth, 1.0, slabLength);
    const hCMat = new THREE.MeshStandardMaterial({
      color: 0x9a7b56,
      roughness: 0.95,
    });
    const hCMesh = new THREE.Mesh(hCGeo, hCMat);
    hCMesh.position.y = -2.3;
    hCMesh.castShadow = true;
    hCMesh.receiveShadow = true;
    strataGroup.add(hCMesh);

    // Water Table (Napa Freática Subterránea) - Luminous translucent cyan slab
    const waterGeo = new THREE.BoxGeometry(slabWidth * 1.02, 0.12, slabLength * 1.02);
    const waterMat = new THREE.MeshStandardMaterial({
      color: 0x7ba7d9,
      transparent: true,
      opacity: 0.68,
      roughness: 0.1,
      metalness: 0.2,
    });
    const waterMesh = new THREE.Mesh(waterGeo, waterMat);
    waterMesh.position.y = -1.8; // Depth corresponding to ~1.8m
    strataGroup.add(waterMesh);

    // Pedestal edge wireframe
    const boxWireGeo = new THREE.BoxGeometry(slabWidth, slabDepth, slabLength);
    const boxWireMat = new THREE.LineBasicMaterial({
      color: 0xdcdcd2,
      transparent: true,
      opacity: 0.8,
    });
    const boxWire = new THREE.LineSegments(
      new THREE.EdgesGeometry(boxWireGeo),
      boxWireMat
    );
    boxWire.position.y = -slabDepth / 2;
    modelGroup.add(boxWire);

    // Top Crop Sectors Layer
    const sectorsGroup = new THREE.Group();
    modelGroup.add(sectorsGroup);

    const sectorMeshes: {
      id: string;
      mesh: THREE.Mesh;
      beacon: THREE.Mesh;
      pole: THREE.Mesh;
      sector: ParcelSector;
    }[] = [];

    const currentSectors =
      sectorsRef.current.length > 0 ? sectorsRef.current : sectors;

    currentSectors.forEach((sec) => {
      // Calculate bounding box and centroid from offsets
      let minLat = 999,
        maxLat = -999,
        minLng = 999,
        maxLng = -999;
      sec.offsets.forEach(([dLat, dLng]) => {
        if (dLat < minLat) minLat = dLat;
        if (dLat > maxLat) maxLat = dLat;
        if (dLng < minLng) minLng = dLng;
        if (dLng > maxLng) maxLng = dLng;
      });

      // Normalize offsets to slab local coordinates [-5, 5]
      const scaleFactor = 220;
      const shape = new THREE.Shape();
      sec.offsets.forEach(([dLat, dLng], i) => {
        const x = dLng * scaleFactor;
        const z = dLat * scaleFactor;
        if (i === 0) shape.moveTo(x, z);
        else shape.lineTo(x, z);
      });
      shape.closePath();

      // Extrude 3D terrain sector slab slightly above the base
      const extrudeSettings = {
        depth: 0.2,
        bevelEnabled: true,
        bevelSegments: 2,
        steps: 1,
        bevelSize: 0.04,
        bevelThickness: 0.04,
      };

      const secGeo = new THREE.ExtrudeGeometry(shape, extrudeSettings);
      secGeo.rotateX(-Math.PI / 2); // Lay flat on XZ plane

      const secMat = new THREE.MeshStandardMaterial({
        color: new THREE.Color(sec.color),
        roughness: 0.65,
        metalness: 0.05,
      });

      const secMesh = new THREE.Mesh(secGeo, secMat);
      secMesh.position.y = 0.02;
      secMesh.castShadow = true;
      secMesh.receiveShadow = true;
      secMesh.userData = { sector: sec };
      sectorsGroup.add(secMesh);

      // Sector perimeter line
      const edges = new THREE.EdgesGeometry(secGeo);
      const edgeLine = new THREE.LineSegments(
        edges,
        new THREE.LineBasicMaterial({ color: 0xf4f6f2, linewidth: 2 })
      );
      secMesh.add(edgeLine);

      // Topographic Furrows / Surcos de Siembra
      const furrowLines = new THREE.Group();
      secMesh.add(furrowLines);
      for (let fz = -4.5; fz <= 4.5; fz += 0.35) {
        const linePts = [
          new THREE.Vector3(-4.8, 0.22, fz),
          new THREE.Vector3(4.8, 0.22, fz),
        ];
        const fGeo = new THREE.BufferGeometry().setFromPoints(linePts);
        const fMat = new THREE.LineBasicMaterial({
          color: 0xffffff,
          transparent: true,
          opacity: 0.2,
        });
        furrowLines.add(new THREE.Line(fGeo, fMat));
      }

      // Calculate centroid for 3D Data Pin
      const avgLat = (minLat + maxLat) / 2;
      const avgLng = (minLng + maxLng) / 2;
      const pinWorld = new THREE.Vector3(
        avgLng * scaleFactor,
        0.85,
        -avgLat * scaleFactor
      );
      worldPins.push({ sector: sec, pos: pinWorld });

      // Visual vertical pin pole on 3D mesh
      const poleGeo = new THREE.CylinderGeometry(0.02, 0.02, 0.6, 8);
      const poleMat = new THREE.MeshBasicMaterial({ color: 0x4e7faf });
      const pole = new THREE.Mesh(poleGeo, poleMat);
      pole.position.set(pinWorld.x, 0.45, pinWorld.z);
      secMesh.add(pole);

      const beaconGeo = new THREE.SphereGeometry(0.12, 16, 16);
      const beaconMat = new THREE.MeshBasicMaterial({
        color: new THREE.Color(sec.color),
      });
      const beacon = new THREE.Mesh(beaconGeo, beaconMat);
      beacon.position.set(pinWorld.x, 0.8, pinWorld.z);
      secMesh.add(beacon);

      sectorMeshes.push({
        id: sec.id,
        mesh: secMesh,
        beacon,
        pole,
        sector: sec,
      });
    });

    sectorMeshesRef.current = sectorMeshes;
    pinWorldPositions.current = worldPins;

    // If field has irrigation (e.g. San Jerónimo), render a 3D Center Pivot Boom!
    if (field.irrigation) {
      const pivotGroup = new THREE.Group();
      modelGroup.add(pivotGroup);
      pivotGroup.position.set(-1.5, 0.25, 0);

      // Central tower
      const towerGeo = new THREE.CylinderGeometry(0.1, 0.3, 0.8, 8);
      const towerMat = new THREE.MeshStandardMaterial({ color: 0xa7a7a0 });
      const tower = new THREE.Mesh(towerGeo, towerMat);
      tower.position.y = 0.4;
      pivotGroup.add(tower);

      // Truss arm
      const armGeo = new THREE.CylinderGeometry(0.04, 0.04, 3.8, 8);
      const armMat = new THREE.MeshStandardMaterial({ color: 0x84847c });
      const arm = new THREE.Mesh(armGeo, armMat);
      arm.rotation.z = Math.PI / 2;
      arm.position.set(1.9, 0.7, 0);
      pivotGroup.add(arm);

      // Wheels
      [-0.1, 1.8, 3.7].forEach((wx) => {
        const wheelGeo = new THREE.CylinderGeometry(0.15, 0.15, 0.06, 12);
        const wheelMat = new THREE.MeshStandardMaterial({ color: 0x12271e });
        const wheel = new THREE.Mesh(wheelGeo, wheelMat);
        wheel.rotation.x = Math.PI / 2;
        wheel.position.set(wx, 0.15, 0);
        pivotGroup.add(wheel);
      });
    }

    // 9. Interactive Raycasting on Sector Click
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();

    const handleClick = (e: MouseEvent) => {
      const rect = renderer.domElement.getBoundingClientRect();
      mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      raycaster.setFromCamera(mouse, camera);
      const candidates = sectorMeshesRef.current.map((s) => s.mesh);
      const intersects = raycaster.intersectObjects(candidates, false);

      if (intersects.length > 0) {
        const hit = intersects[0].object as THREE.Mesh;
        const match = sectorMeshesRef.current.find((s) => s.mesh === hit);
        if (match) {
          const currentSector =
            sectorsRef.current.find((s) => s.id === match.id) || match.sector;
          setActiveSector(currentSector);
          // Subtle pulse animation on clicked sector
          gsap.fromTo(
            hit.position,
            { y: 0.15 },
            { y: 0.02, duration: 0.35, ease: "bounce.out" }
          );
        }
      }
    };

    renderer.domElement.addEventListener("click", handleClick);

    // 10. Animation Loop & Screen Projection for Data Badges
    let animId: number;
    const tempVec = new THREE.Vector3();

    const animate = () => {
      animId = requestAnimationFrame(animate);
      controls.update();

      // Project 3D Pin coordinates to 2D Screen
      const w = container.clientWidth;
      const h = container.clientHeight;
      const currentPins: {
        sector: ParcelSector;
        x: number;
        y: number;
        visible: boolean;
      }[] = [];

      pinWorldPositions.current.forEach(({ sector, pos }) => {
        tempVec.copy(pos);
        tempVec.applyMatrix4(modelGroup.matrixWorld);

        // Check if point is in front of camera
        tempVec.project(camera);
        const visible = tempVec.z < 1.0;
        const screenX = (tempVec.x * 0.5 + 0.5) * w;
        const screenY = (-tempVec.y * 0.5 + 0.5) * h;

        const currentSec =
          sectorsRef.current.find((s) => s.id === sector.id) || sector;

        currentPins.push({
          sector: currentSec,
          x: screenX,
          y: screenY,
          visible,
        });
      });

      setProjectedPins(currentPins);
      renderer.render(scene, camera);
    };

    animate();

    // 11. Handle Resize
    const handleResize = () => {
      if (!container) return;
      const w = container.clientWidth;
      const h = container.clientHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };
    window.addEventListener("resize", handleResize);

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener("resize", handleResize);
      renderer.domElement.removeEventListener("click", handleClick);
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
      renderer.dispose();
      sectorMeshesRef.current = [];
    };
  }, [field.id, field.irrigation]);

  // Camera Presets
  const setCameraPreset = (type: "iso" | "top" | "soil") => {
    if (!cameraRef.current || !controlsRef.current) return;
    const camera = cameraRef.current;
    const controls = controlsRef.current;

    controls.enabled = false;
    let targetPos = { x: 11, y: 10, z: 15 };
    if (type === "top") targetPos = { x: 0, y: 18, z: 0.1 };
    if (type === "soil") targetPos = { x: 14, y: 1.5, z: 10 };

    gsap.to(camera.position, {
      ...targetPos,
      duration: 0.9,
      ease: "power2.inOut",
      onUpdate: () => camera.lookAt(0, 0, 0),
      onComplete: () => {
        controls.enabled = true;
      },
    });
  };

  return (
    <div className={`relative w-full h-full overflow-hidden select-none bg-nube ${className}`}>
      {/* 3D WebGL Canvas */}
      <div
        ref={mountRef}
        className="absolute inset-0 z-0 cursor-grab active:cursor-grabbing bg-nube"
      />

      {/* Top Left Navigation Bar: Reintegrar al Mapa & Breadcrumbs */}
      <div className="absolute top-4 left-4 z-20 pointer-events-auto flex items-center gap-2">
        <button
          onClick={onBackToMap}
          className="flex items-center gap-2 rounded-full bg-papel/95 border border-piedra-soft px-4 py-2 shadow-md backdrop-blur-md text-xs font-bold text-bosque/80 hover:bg-nube hover:text-musgo transition-all cursor-pointer group active:scale-95"
        >
          <ArrowLeft className="h-4 w-4 group-hover:-translate-x-0.5 transition-transform text-piedra" />
          <span>Reintegrar al Mapa</span>
        </button>

        <div className="hidden sm:flex items-center gap-1.5 rounded-full bg-papel/90 border border-piedra-soft px-3 py-1.5 shadow-xs backdrop-blur-md text-[11px] text-piedra font-sans">
          <span className="text-piedra">Terria</span>
          <span>/</span>
          <span className="font-semibold text-bosque/80">{field.name}</span>
          <span>/</span>
          <span className="font-bold text-musgo flex items-center gap-1">
            <Box className="h-3 w-3" /> Maqueta 3D Aislada
          </span>
        </div>
      </div>

      {/* Top Right Controls: Camera Presets & Layer Badges */}
      <div className="absolute top-4 right-4 z-20 pointer-events-auto flex items-center gap-2">
        {/* Camera Preset Buttons */}
        <div className="flex items-center gap-1 rounded-full bg-papel/95 border border-piedra-soft p-1 shadow-sm backdrop-blur-md text-xs">
          <button
            onClick={() => setCameraPreset("iso")}
            title="Perspectiva Isométrica 45°"
            className="px-2.5 py-1 rounded-full font-medium text-bosque/70 hover:bg-nube transition-colors cursor-pointer"
          >
            Iso 45°
          </button>
          <button
            onClick={() => setCameraPreset("top")}
            title="Vista Cenital Superior"
            className="px-2.5 py-1 rounded-full font-medium text-bosque/70 hover:bg-nube transition-colors cursor-pointer"
          >
            Cenital
          </button>
          <button
            onClick={() => setCameraPreset("soil")}
            title="Corte Estratigráfico Subterráneo"
            className="px-2.5 py-1 rounded-full font-medium text-bosque/70 hover:bg-nube transition-colors cursor-pointer"
          >
            Perfil Suelo
          </button>
        </div>
      </div>

      {/* Floating 3D Data Pins on Screen (Projected from 3D coords) */}
      <div className="pointer-events-none absolute inset-0 z-10 overflow-hidden">
        {projectedPins.map((p, idx) => {
          if (!p.visible) return null;
          const isSelected = activeSector?.id === p.sector.id;
          return (
            <div
              key={idx}
              className="absolute pointer-events-auto transition-transform duration-100 cursor-pointer"
              style={{
                left: `${p.x}px`,
                top: `${p.y}px`,
                transform: `translate(-50%, -100%) scale(${isSelected ? 1.08 : 0.95})`,
              }}
              onClick={() => setActiveSector(p.sector)}
            >
              <div
                className={`flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-bold shadow-md backdrop-blur-md transition-all border ${
                  isSelected
                    ? "bg-papel text-bosque border-musgo ring-2 ring-musgo/30 shadow-lg"
                    : "bg-papel/95 text-bosque/70 border-piedra-soft hover:border-piedra"
                }`}
              >
                <span
                  className="h-2 w-2 rounded-full shrink-0 transition-colors duration-300"
                  style={{ backgroundColor: p.sector.color }}
                />
                <span className="truncate max-w-[130px]">{p.sector.name}</span>
                <span className="rounded-full bg-musgo/10 text-musgo px-1.5 py-0.2 text-[10px]">
                  NDVI {p.sector.ndvi.toFixed(2)}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Stratigraphic Cutaway Annotations on the Side */}
      <div className="absolute left-4 top-20 z-10 pointer-events-none hidden md:flex flex-col gap-2 text-[10px] font-sans">
        <div className="rounded-xl bg-papel/90 border border-piedra-soft px-3 py-1.5 shadow-xs backdrop-blur-sm text-bosque/70 space-y-1 max-w-[200px]">
          <div className="font-bold text-bosque text-[11px] flex items-center gap-1">
            <Layers className="h-3 w-3 text-tierra-deep" />
            <span>Perfil Geológico</span>
          </div>
          <div className="flex items-center justify-between text-piedra">
            <span>Horizonte A (Capa fértil)</span>
            <span className="font-mono font-bold text-bosque/80">0 - 30 cm</span>
          </div>
          <div className="flex items-center justify-between text-piedra">
            <span>Horizonte B (Argílico)</span>
            <span className="font-mono font-bold text-bosque/80">30 - 100 cm</span>
          </div>
          <div className="flex items-center justify-between text-cielo-deep font-semibold pt-0.5 border-t border-piedra-soft">
            <span className="flex items-center gap-1">
              <Droplets className="h-3 w-3" /> Napa Freática
            </span>
            <span className="font-mono font-bold">1.8 m</span>
          </div>
        </div>
      </div>

      {/* Bottom Agronomic Telemetry Dock for the Active Sector */}
      {activeSector && (
        <div className="absolute bottom-4 left-4 right-4 z-20 pointer-events-auto flex justify-center transition-all duration-300">
          <div className="w-full max-w-2xl rounded-2xl bg-papel/95 border border-piedra-soft p-3.5 shadow-xl backdrop-blur-md">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              {/* Sector Title & Crop */}
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span
                    className="h-3 w-3 rounded-full shrink-0 shadow-xs transition-colors duration-300"
                    style={{ backgroundColor: activeSector.color }}
                  />
                  <h3 className="text-sm font-bold text-bosque leading-tight">
                    {activeSector.name}
                  </h3>
                  <span className="rounded-full bg-cielo/15 text-cielo-deep text-[10px] font-semibold px-2 py-0.5">
                    {activeSector.variety}
                  </span>
                </div>
                <p className="text-[11px] text-piedra">
                  {activeSector.soilHorizon}
                </p>
              </div>

              {/* Agronomic KPI Strip */}
              <div className="flex items-center gap-3 sm:gap-4 shrink-0 text-center">
                <div className="rounded-xl bg-nube border border-piedra-soft px-3 py-1.5">
                  <span className="text-[10px] text-piedra block font-medium">Área</span>
                  <span className="text-xs font-extrabold text-bosque">
                    {activeSector.hectares} ha
                  </span>
                </div>

                <div className="rounded-xl bg-musgo/10 border border-musgo/20 px-3 py-1.5 transition-colors duration-300">
                  <span className="text-[10px] text-musgo block font-medium">NDVI Satelital</span>
                  <span className="text-xs font-extrabold text-musgo">
                    {activeSector.ndvi.toFixed(2)}
                  </span>
                </div>

                <div className="rounded-xl bg-cielo/10 border border-cielo/30 px-3 py-1.5 transition-colors duration-300">
                  <span className="text-[10px] text-cielo-deep block font-medium">Humedad Suelo</span>
                  <span className="text-xs font-extrabold text-cielo-deep">
                    {activeSector.moisturePercent}%
                  </span>
                </div>

                <div className="rounded-xl bg-tierra/15 border border-tierra/40 px-3 py-1.5 transition-colors duration-300">
                  <span className="text-[10px] text-tierra-deep block font-medium">Rinde Est.</span>
                  <span className="text-xs font-extrabold text-tierra-deep">
                    {activeSector.expectedYield}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Orbit Interaction Hint */}
      <div className="absolute bottom-1 right-4 z-10 pointer-events-none text-[10px] text-piedra font-sans hidden sm:block">
        Gira 360° con el ratón para inspeccionar la maqueta 3D
      </div>
    </div>
  );
}
