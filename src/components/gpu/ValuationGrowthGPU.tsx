"use client";

import React, { useEffect, useRef, useState } from "react";
import { FieldItem } from "@/data/fieldsData";
import type { LandValuation, ValuationSource } from "@/types/valuation";
import {
  init,
  surface,
  target,
  draw,
  effect,
  frameLoop,
  clock,
  geometry,
  sampler,
  type Gpu,
} from "vgpu";
import { box, plane, perspectiveCamera } from "vgpu/scene";

/* ------------------------------------------------------------------ */
/* WGSL shaders                                                        */
/* ------------------------------------------------------------------ */

const SLAB_SHADER = /* wgsl */ `
struct Camera { viewProjection: mat4x4f, }
struct Params {
  time: f32,
  growth: f32,
  dLog: f32,
  dAgro: f32,
  dMkt: f32,
  yaw: f32,
  tilt: f32,
}
@group(0) @binding(0) var<uniform> camera: Camera;
@group(0) @binding(1) var<uniform> params: Params;

struct VOut {
  @builtin(position) clip: vec4f,
  @location(0) normal: vec3f,
  @location(1) uv: vec2f,
  @location(2) world: vec3f,
}

fn rotY(p: vec3f, a: f32) -> vec3f {
  let c = cos(a); let s = sin(a);
  return vec3f(p.x * c - p.z * s, p.y, p.x * s + p.z * c);
}
fn rotX(p: vec3f, a: f32) -> vec3f {
  let c = cos(a); let s = sin(a);
  return vec3f(p.x, p.y * c - p.z * s, p.y * s + p.z * c);
}

@vertex fn vs_main(@location(0) position: vec3f, @location(1) normal: vec3f) -> VOut {
  var wp = position * vec3f(2.35, 0.085, 1.6);
  wp = rotX(rotY(wp, params.yaw), params.tilt);
  wp.y += sin(params.time * 0.7) * 0.028;
  var out: VOut;
  out.clip = camera.viewProjection * vec4f(wp, 1.0);
  out.world = wp;
  out.normal = rotX(rotY(normal, params.yaw), params.tilt);
  out.uv = vec2f(position.x + 0.5, position.z + 0.5);
  return out;
}

@fragment fn fs_main(in: VOut) -> @location(0) vec4f {
  let up = in.normal.y;

  // Caras laterales: estratos oscuros con luz esmeralda (misma firma que timelapse)
  if (up < 0.72) {
    let strata = 0.5 + 0.5 * sin(in.world.y * 260.0);
    let fres = pow(clamp(1.0 - abs(up), 0.0, 1.6), 1.6);
    var col = vec3f(0.10, 0.16, 0.13) * 0.35 + vec3f(0.008, 0.045, 0.035);
    col += vec3f(0.0, 0.42, 0.28) * strata * 0.35;
    col += vec3f(0.05, 0.9, 0.55) * fres * 0.10;
    return vec4f(col, 1.0);
  }

  let uv = in.uv;

  // Base del terreno: verde suelo agrícola apagado, editorial
  var col = mix(vec3f(0.13, 0.23, 0.16), vec3f(0.22, 0.34, 0.20), uv.y);

  // Zona logística (azul): corredor vial que barre de oeste a este
  let corridor = exp(-abs(uv.y - 0.62) * 9.0)
    * smoothstep(0.0, 0.12, uv.x) * (1.0 - smoothstep(0.75, 1.0, uv.x));
  let beamSweep = 0.6 + 0.4 * sin(params.time * 1.6 - uv.x * 7.0);
  col += vec3f(0.20, 0.45, 1.0) * corridor * beamSweep * params.dLog * 0.9;

  // Zona agronómica (esmeralda): anillos de crecimiento desde el centro
  let rc = length((uv - vec2f(0.42, 0.45)) * vec2f(1.3, 1.0));
  let rings = 0.5 + 0.5 * sin(rc * 26.0 - params.time * 2.2);
  col += vec3f(0.05, 0.9, 0.5) * rings * exp(-rc * 2.6) * params.dAgro * 0.55;

  // Zona mercado (ámbar): glow ambiental cálido desde el horizonte norte
  let mkt = smoothstep(0.55, 1.0, uv.y) * (0.7 + 0.3 * sin(params.time * 0.9));
  col += vec3f(0.95, 0.68, 0.20) * mkt * params.dMkt * 0.40;

  // Barrido holográfico de proyección (el "futuro" recorriendo el lote)
  let sweepY = fract(params.time * 0.05);
  col += vec3f(0.35, 0.85, 1.0) * (1.0 - smoothstep(0.0, 0.030, abs(uv.y - sweepY))) * 0.22;

  // Grilla cartográfica
  let gx = 1.0 - smoothstep(0.0, 0.025, fract(uv.x * 10.0));
  let gy = 1.0 - smoothstep(0.0, 0.025, fract(uv.y * 10.0));
  col += vec3f(0.9, 1.0, 0.95) * max(gx, gy) * 0.05;

  // Perímetro neón esmeralda (límite certificado del lote)
  let d = min(min(uv.x, 1.0 - uv.x), min(uv.y, 1.0 - uv.y));
  let borderPulse = 0.72 + 0.28 * sin(params.time * 2.1);
  col += vec3f(0.05, 0.95, 0.52) * ((1.0 - smoothstep(0.0, 0.010, d)) * borderPulse
        + (1.0 - smoothstep(0.0, 0.085, d)) * 0.30);

  return vec4f(col, 1.0);
}
`;

const PILLAR_SHADER = /* wgsl */ `
struct Camera { viewProjection: mat4x4f, }
struct Params {
  time: f32,
  height: f32,
  rise: f32,
  active: f32,
  px: f32,
  yaw: f32,
  tilt: f32,
}
@group(0) @binding(0) var<uniform> camera: Camera;
@group(0) @binding(1) var<uniform> params: Params;

struct VOut {
  @builtin(position) clip: vec4f,
  @location(0) local: vec3f,
  @location(1) normal: vec3f,
}

fn rotY(p: vec3f, a: f32) -> vec3f {
  let c = cos(a); let s = sin(a);
  return vec3f(p.x * c - p.z * s, p.y, p.x * s + p.z * c);
}
fn rotX(p: vec3f, a: f32) -> vec3f {
  let c = cos(a); let s = sin(a);
  return vec3f(p.x, p.y * c - p.z * s, p.y * s + p.z * c);
}

@vertex fn vs_main(@location(0) position: vec3f, @location(1) normal: vec3f) -> VOut {
  let h = params.height * params.rise;
  var wp = position * vec3f(0.055, h, 0.055);
  wp.y += 0.055 + h * 0.5;              // base apoyada sobre la cara del slab
  wp.x += params.px;
  wp.z += -0.52;                        // fila trasera del lote
  wp.y += sin(params.time * 0.7) * 0.028; // misma flotación que el slab
  wp = rotX(rotY(wp, params.yaw), params.tilt);
  var out: VOut;
  out.clip = camera.viewProjection * vec4f(wp, 1.0);
  out.local = position;
  out.normal = rotX(rotY(normal, params.yaw), params.tilt);
  return out;
}

@fragment fn fs_main(in: VOut) -> @location(0) vec4f {
  // Gradiente vertical holográfico: base densa → punta luminosa
  let t = in.local.y + 0.5;
  var col = mix(vec3f(0.02, 0.35, 0.24), vec3f(0.20, 1.0, 0.65), t);
  // Scanline ascendente
  let scan = 1.0 - smoothstep(0.0, 0.06, abs(fract(t * 3.0 - params.time * 0.8) - 0.5) - 0.30);
  col += vec3f(0.4, 1.0, 0.8) * scan * 0.35;
  // Punta del pilar más brillante
  col += vec3f(0.6, 1.0, 0.8) * smoothstep(0.90, 1.0, t) * (0.5 + params.active * 0.5);
  let alpha = (0.34 + 0.30 * t + params.active * 0.20) * params.rise;
  return vec4f(col, alpha);
}
`;

const CAP_SHADER = /* wgsl */ `
struct Camera { viewProjection: mat4x4f, }
struct Params { time: f32, height: f32, growth: f32, yaw: f32, tilt: f32, }
@group(0) @binding(0) var<uniform> camera: Camera;
@group(0) @binding(1) var<uniform> params: Params;

struct VOut {
  @builtin(position) clip: vec4f,
  @location(0) uv: vec2f,
  @location(1) world: vec3f,
}

fn rotY(p: vec3f, a: f32) -> vec3f {
  let c = cos(a); let s = sin(a);
  return vec3f(p.x * c - p.z * s, p.y, p.x * s + p.z * c);
}
fn rotX(p: vec3f, a: f32) -> vec3f {
  let c = cos(a); let s = sin(a);
  return vec3f(p.x, p.y * c - p.z * s, p.y * s + p.z * c);
}

@vertex fn vs_main(@location(0) position: vec3f) -> VOut {
  var wp = vec3f(position.x * 2.35, params.height * params.growth, position.z * 1.6);
  wp.y += 0.10 + sin(params.time * 0.7) * 0.028;
  wp = rotX(rotY(wp, params.yaw), params.tilt);
  var out: VOut;
  out.clip = camera.viewProjection * vec4f(wp, 1.0);
  out.uv = vec2f(position.x + 0.5, position.z + 0.5);
  out.world = wp;
  return out;
}

@fragment fn fs_main(in: VOut) -> @location(0) vec4f {
  let uv = in.uv;
  // Techo de valor: lámina holográfica ámbar-esmeralda con grilla y borde
  var col = mix(vec3f(0.05, 0.75, 0.45), vec3f(0.95, 0.72, 0.25), uv.x);
  let gx = 1.0 - smoothstep(0.0, 0.03, fract(uv.x * 12.0));
  let gy = 1.0 - smoothstep(0.0, 0.03, fract(uv.y * 8.0));
  col += vec3f(1.0) * max(gx, gy) * 0.18;
  let d = min(min(uv.x, 1.0 - uv.x), min(uv.y, 1.0 - uv.y));
  let edge = 1.0 - smoothstep(0.0, 0.05, d);
  col += vec3f(0.3, 1.0, 0.7) * edge * (0.7 + 0.3 * sin(params.time * 2.0));
  let sweep = 1.0 - smoothstep(0.0, 0.05, abs(uv.x - fract(params.time * 0.08)));
  col += vec3f(0.5, 1.0, 0.9) * sweep * 0.35;
  let alpha = (0.10 + edge * 0.28 + max(gx, gy) * 0.10 + sweep * 0.12) * params.growth;
  return vec4f(col, alpha);
}
`;

const FLOOR_SHADER = /* wgsl */ `
struct Camera { viewProjection: mat4x4f, }
struct Params { time: f32, }
@group(0) @binding(0) var<uniform> camera: Camera;
@group(0) @binding(1) var<uniform> params: Params;

struct VOut {
  @builtin(position) clip: vec4f,
  @location(0) world: vec3f,
}

@vertex fn vs_main(@location(0) position: vec3f) -> VOut {
  var wp = vec3f(position.x * 8.0, -0.30, position.z * 8.0);
  var out: VOut;
  out.clip = camera.viewProjection * vec4f(wp, 1.0);
  out.world = wp;
  return out;
}

@fragment fn fs_main(in: VOut) -> @location(0) vec4f {
  let xz = in.world.xz;
  let gx = 1.0 - smoothstep(0.0, 0.030, abs(fract(xz.x * 1.35 + 0.5) - 0.5));
  let gz = 1.0 - smoothstep(0.0, 0.030, abs(fract(xz.y * 1.35 + 0.5) - 0.5));
  let grid = max(gx, gz);
  // Anillos de horizonte: los "años futuros" radiando desde el lote
  let r = length(xz / vec2f(1.0, 0.68));
  let ring = 1.0 - smoothstep(0.0, 0.045, abs(fract(r * 1.35 - params.time * 0.10) - 0.5) - 0.42);
  let shadow = exp(-dot(xz / vec2f(1.55, 1.05), xz / vec2f(1.55, 1.05)) * 2.6);
  let fade = exp(-dot(xz, xz) * 0.10);

  var col = vec3f(0.04, 0.50, 0.40) * (grid * 0.16 + ring * 0.20);
  col += vec3f(0.85, 0.65, 0.25) * ring * 0.10; // matiz ámbar de horizonte
  col += vec3f(0.6, 0.9, 0.8) * grid * 0.05;
  let alpha = clamp((grid * 0.20 + ring * 0.30) * fade, 0.0, 0.55);
  col = col - vec3f(shadow * 0.14);
  return vec4f(col, alpha + shadow * 0.30);
}
`;

const POST_SHADER = /* wgsl */ `
struct P { time: f32, texel: vec2f, }
@group(0) @binding(0) var src: texture_2d<f32>;
@group(0) @binding(1) var samp: sampler;
@group(0) @binding(2) var<uniform> p: P;

@fragment fn fs_main(@location(0) uv: vec2f) -> @location(0) vec4f {
  let d = uv - vec2f(0.5);
  let ca = dot(d, d) * 0.010;
  let r = textureSampleLevel(src, samp, uv + d * ca, 0.0).r;
  let g = textureSampleLevel(src, samp, uv, 0.0).g;
  let b = textureSampleLevel(src, samp, uv - d * ca, 0.0).b;
  var col = vec3f(r, g, b);
  col *= 1.0 - dot(d, d) * 0.42;
  let gr = fract(sin(dot(uv + vec2f(p.time * 0.017, p.time * 0.011), vec2f(12.9898, 78.233))) * 43758.5453);
  col += (gr - 0.5) * 0.024;
  col += vec3f(0.015, 0.045, 0.035) * (1.0 - uv.y) * 0.30;
  return vec4f(col, 1.0);
}
`;

/* ------------------------------------------------------------------ */
/* Tipos internos                                                      */
/* ------------------------------------------------------------------ */

interface ViewState {
  yaw: number;
  tilt: number;
  yawTarget: number;
  tiltTarget: number;
  growth: number;
  heights: number[];
  heightTargets: number[];
  rises: number[];
  riseStart: number;
  dLog: number;
  dAgro: number;
  dMkt: number;
}

export interface ValuationGrowthGPUProps {
  valuation: LandValuation | null;
  source: ValuationSource;
  field?: FieldItem;
  onBack?: () => void;
  className?: string;
}

const fmtUsd = (n: number) =>
  n.toLocaleString("es-AR", { maximumFractionDigits: 0 });

/* ------------------------------------------------------------------ */
/* Componente                                                          */
/* ------------------------------------------------------------------ */

export default function ValuationGrowthGPU({
  valuation,
  source,
  field,
  onBack,
  className = "",
}: ValuationGrowthGPUProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const hostRef = useRef<HTMLDivElement>(null);
  const [gpuError, setGpuError] = useState<string | null>(null);
  const [sceneReady, setSceneReady] = useState(false);

  const engineRef = useRef<{
    gpu: Gpu;
    pillars: ReturnType<typeof draw>[];
    cap: ReturnType<typeof draw>;
    slab: ReturnType<typeof draw>;
    viewProjection: Float32Array;
  } | null>(null);
  const pillarsRef = useRef<ReturnType<typeof draw>[]>([]);
  const viewRef = useRef<ViewState>({
    yaw: 0,
    tilt: 0,
    yawTarget: 0,
    tiltTarget: 0,
    growth: 0,
    heights: [],
    heightTargets: [],
    rises: [],
    riseStart: 0,
    dLog: 0,
    dAgro: 0,
    dMkt: 0,
  });

  /* ---------- init WebGPU una sola vez ---------- */
  useEffect(() => {
    if (!canvasRef.current) return;

    let disposed = false;
    let stopLoop: (() => void) | undefined;
    let gpu: Gpu | undefined;

    (async () => {
      if (typeof navigator === "undefined" || !("gpu" in navigator)) {
        if (!disposed) setGpuError("WebGPU no disponible en este navegador");
        return;
      }
      try {
        gpu = await init({ label: "terria-valuation" });
      } catch {
        if (!disposed) setGpuError("No se pudo inicializar WebGPU");
        return;
      }
      if (disposed || !canvasRef.current) {
        gpu?.dispose();
        return;
      }

      const g = gpu;
      const surf = surface(g, canvasRef.current, { dpr: [1, 2] });
      const sceneTarget = target(g, {
        size: [Math.max(1, surf.size[0]), Math.max(1, surf.size[1])],
        depth: true,
        clearColor: [0.968, 0.977, 0.984, 1],
        label: "valuation-scene",
      });
      const cam = perspectiveCamera({
        fov: 34,
        aspect: surf.size[0] / Math.max(1, surf.size[1]),
        position: [0, 2.1, 3.25],
        target: [0, 0.08, 0],
        near: 0.1,
        far: 40,
      });

      const texSampler = sampler(g, {
        minFilter: "linear",
        magFilter: "linear",
        addressModeU: "clamp-to-edge",
        addressModeV: "clamp-to-edge",
      });

      const slab = draw(g, {
        shader: SLAB_SHADER,
        geometry: geometry(g, box({ size: 1 })),
        cull: "back",
        depth: { write: true, compare: "less-equal" },
        label: "valuation-slab",
      });
      slab.set({
        camera: { viewProjection: cam.viewProjection },
        params: { time: 0, growth: 0, dLog: 0, dAgro: 0, dMkt: 0, yaw: 0, tilt: 0 },
      });

      const cap = draw(g, {
        shader: CAP_SHADER,
        geometry: geometry(g, plane({ width: 1, height: 1 })),
        blend: "alpha",
        depth: { write: false, compare: "less-equal" },
        label: "valuation-cap",
      });
      cap.set({
        camera: { viewProjection: cam.viewProjection },
        params: { time: 0, height: 0.55, growth: 0, yaw: 0, tilt: 0 },
      });

      const floor = draw(g, {
        shader: FLOOR_SHADER,
        geometry: geometry(g, plane({ width: 1, height: 1 })),
        blend: "alpha",
        depth: { write: false, compare: "less-equal" },
        label: "valuation-floor",
      });
      floor.set({
        camera: { viewProjection: cam.viewProjection },
        params: { time: 0 },
      });

      const post = effect(g, POST_SHADER);
      const postParams = {
        time: 0,
        texel: [surf.texelSize[0], surf.texelSize[1]] as [number, number],
      };
      post.set({ src: sceneTarget, samp: texSampler, p: postParams });

      surf.onResize((e) => {
        sceneTarget.resize([e.width, e.height]);
        cam.set({ aspect: e.width / Math.max(1, e.height) });
        cam.lookAt([0, 0.08, 0]);
        postParams.texel = [
          e.width ? 1 / e.width : 0,
          e.height ? 1 / e.height : 0,
        ];
      });

      engineRef.current = {
        gpu: g,
        pillars: [],
        cap,
        slab,
        viewProjection: cam.viewProjection,
      };
      setSceneReady(true);

      const clk = clock(g);
      const loop = frameLoop(g, (frame) => {
        const v = viewRef.current;
        const dt = Math.min(0.05, clk.deltaTime || 0.016);
        const t = clk.time;

        v.yaw += (v.yawTarget - v.yaw) * Math.min(1, dt * 6);
        v.tilt += (v.tiltTarget - v.tilt) * Math.min(1, dt * 6);
        v.growth += (1 - v.growth) * Math.min(1, dt * 1.2);

        // Pilares: altura ease + aparición escalonada
        if (v.riseStart < 0) v.riseStart = t;
        const elapsed = t - v.riseStart;
        for (let i = 0; i < v.heights.length; i++) {
          const target = v.heightTargets[i] ?? 0;
          v.heights[i] += (target - v.heights[i]) * Math.min(1, dt * 3);
          const delay = i * 0.09;
          const rTarget = elapsed > delay ? 1 : 0;
          v.rises[i] += (rTarget - v.rises[i]) * Math.min(1, dt * 4);
        }

        cam.set({
          position: [
            Math.sin(t * 0.11) * 0.10 + v.yaw * 1.1,
            2.1 + v.tilt * 1.1,
            3.25,
          ],
        });
        cam.lookAt([0, 0.08, 0]);

        const yaw = Math.sin(t * 0.16) * 0.10 + v.yaw * 0.55;
        const tilt = v.tilt * 0.35;

        slab.set({
          params: {
            time: t,
            growth: v.growth,
            dLog: v.dLog,
            dAgro: v.dAgro,
            dMkt: v.dMkt,
            yaw,
            tilt,
          },
        });
        cap.set({
          params: { time: t, height: 0.58, growth: v.growth, yaw, tilt },
        });
        floor.set({ params: { time: t } });

        const n = v.heights.length;
        pillarsRef.current.forEach((pillar, i) => {
          const px = n <= 1 ? 0 : -0.95 + (i / (n - 1)) * 1.9;
          pillar.set({
            params: {
              time: t,
              height: Math.max(0.001, v.heights[i] ?? 0),
              rise: v.rises[i] ?? 0,
              active: i === n - 1 ? 1 : 0,
              px,
              yaw,
              tilt,
            },
          });
        });

        postParams.time = t;
        post.set({ p: postParams });

        frame.pass(sceneTarget, (p) => {
          p.draw(floor);
          p.draw(slab);
          pillarsRef.current.forEach((pillar) => p.draw(pillar));
          p.draw(cap);
        });
        frame.pass(surf, post);
      });
      stopLoop = () => loop.stop();
    })();

    return () => {
      disposed = true;
      stopLoop?.();
      pillarsRef.current = [];
      engineRef.current = null;
      gpu?.dispose();
    };
  }, []);

  /* ---------- parallax con el mouse ---------- */
  useEffect(() => {
    const host = hostRef.current;
    if (!host) return;
    const onMove = (e: PointerEvent) => {
      const r = host.getBoundingClientRect();
      const nx = ((e.clientX - r.left) / r.width) * 2 - 1;
      const ny = ((e.clientY - r.top) / r.height) * 2 - 1;
      viewRef.current.yawTarget = nx * 0.22;
      viewRef.current.tiltTarget = ny * 0.16;
    };
    const onLeave = () => {
      viewRef.current.yawTarget = 0;
      viewRef.current.tiltTarget = 0;
    };
    host.addEventListener("pointermove", onMove);
    host.addEventListener("pointerleave", onLeave);
    return () => {
      host.removeEventListener("pointermove", onMove);
      host.removeEventListener("pointerleave", onLeave);
    };
  }, []);

  /* ---------- valuación → pilares-año y drivers ---------- */
  useEffect(() => {
    const engine = engineRef.current;
    const v = viewRef.current;
    if (!valuation) return;

    const n = Math.max(1, valuation.projectionYears);
    const mTotal =
      valuation.projectedValueUsdHa / Math.max(1, valuation.baseValueUsdHa);
    const appreciation = Math.max(0.0001, mTotal - 1);
    // Escala: el pilar del año target mide 0.5 unidades de mundo
    const scale = 0.5 / appreciation;

    v.heightTargets = Array.from({ length: n }, (_, i) => {
      const cum = Math.pow(mTotal, (i + 1) / n) - 1;
      return Math.min(0.55, cum * scale);
    });
    if (v.heights.length !== n) {
      v.heights = new Array(n).fill(0);
      v.rises = new Array(n).fill(0);
      v.growth = 0;
    }

    const impacts =
      valuation.driversBreakdown.logisticImprovement.impactPercentage +
      valuation.driversBreakdown.agronomicTrend.impactPercentage +
      valuation.driversBreakdown.marketAppreciation.impactPercentage;
    const norm = Math.max(0.0001, impacts);
    v.dLog = valuation.driversBreakdown.logisticImprovement.impactPercentage / norm;
    v.dAgro = valuation.driversBreakdown.agronomicTrend.impactPercentage / norm;
    v.dMkt = valuation.driversBreakdown.marketAppreciation.impactPercentage / norm;

    // (Re)crear draws de pilares si cambia la cantidad de años
    if (engine && pillarsRef.current.length !== n) {
      pillarsRef.current = Array.from({ length: n }, () => {
        const pillar = draw(engine.gpu, {
          shader: PILLAR_SHADER,
          geometry: geometry(engine.gpu, box({ size: 1 })),
          blend: "alpha",
          depth: { write: false, compare: "less-equal" },
          label: "valuation-pillar",
        });
        pillar.set({
          camera: { viewProjection: engine.viewProjection },
          params: {
            time: 0, height: 0, rise: 0, active: 0, px: 0, yaw: 0, tilt: 0,
          },
        });
        return pillar;
      });
      engine.pillars = pillarsRef.current;
      v.riseStart = -1; // el primer frame lo fija en clk.time → stagger de entrada
    }
  }, [valuation, sceneReady]);

  /* ---------- HUD ---------- */

  const d = valuation?.driversBreakdown;

  return (
    <div
      ref={hostRef}
      className={`relative h-full w-full overflow-hidden bg-nube ${className}`}
    >
      <canvas ref={canvasRef} className="block h-full w-full" />

      {gpuError && (
        <div className="absolute inset-0 z-10 flex items-center justify-center bg-nube">
          <div className="max-w-xs text-center">
            <p className="text-xs font-mono font-bold text-bosque/80 uppercase tracking-wider">
              Vista GPU no disponible
            </p>
            <p className="mt-1 text-[11px] font-mono text-piedra">{gpuError}</p>
          </div>
        </div>
      )}

      {/* HUD superior */}
      <div className="pointer-events-none absolute left-4 top-4 z-20 flex flex-col gap-1.5">
        <div className="flex items-center gap-2">
          <span className="rounded-lg border border-tierra/50 bg-papel/85 px-2 py-1 text-[10px] font-mono font-bold uppercase tracking-wider text-tierra-deep backdrop-blur-sm">
            Futurología · Valor del suelo
          </span>
          <span
            className={`rounded-lg border px-2 py-1 text-[10px] font-mono font-bold uppercase tracking-wider backdrop-blur-sm ${
              source === "live"
                ? "border-musgo/40 bg-musgo/10 text-musgo"
                : "border-piedra-soft bg-papel/85 text-piedra"
            }`}
          >
            {source === "live" ? "● En vivo" : source === "demo" ? "Demo local" : "Conectando…"}
          </span>
        </div>
        {valuation && (
          <span className="rounded-lg border border-piedra-soft bg-papel/85 px-2 py-1 text-[10px] font-mono text-bosque/70 backdrop-blur-sm w-fit">
            USD/ha {fmtUsd(valuation.baseValueUsdHa)} →{" "}
            {fmtUsd(valuation.projectedValueUsdHa)} ·{" "}
            {valuation.currentYear}→{valuation.targetYear}
          </span>
        )}
        {field && (
          <span className="rounded-lg border border-piedra-soft bg-papel/85 px-2 py-1 text-[10px] font-mono font-semibold text-bosque backdrop-blur-sm w-fit">
            {field.name}
          </span>
        )}
      </div>

      {onBack && (
        <button
          onClick={onBack}
          className="absolute right-4 top-4 z-20 rounded-xl border border-piedra-soft bg-papel/90 px-3 py-1.5 text-xs font-mono font-bold text-bosque/80 shadow-sm transition-colors hover:border-bosque cursor-pointer backdrop-blur-sm"
        >
          ‹ Mapa
        </button>
      )}

      {/* HUD inferior: leyenda de drivers */}
      <div className="pointer-events-none absolute bottom-4 left-4 right-4 z-20 flex items-end justify-between">
        <div className="flex items-center gap-2">
          {d && (
            <>
              <span className="rounded-lg border border-cielo/40 bg-cielo/15 px-2 py-1 text-[10px] font-mono font-bold text-cielo-deep backdrop-blur-sm">
                Vial ×{d.logisticImprovement.multiplier.toFixed(2)}
              </span>
              <span className="rounded-lg border border-musgo/30 bg-musgo/10 px-2 py-1 text-[10px] font-mono font-bold text-musgo backdrop-blur-sm">
                Agro ×{d.agronomicTrend.multiplier.toFixed(2)}
              </span>
              <span className="rounded-lg border border-tierra/50 bg-tierra/15 px-2 py-1 text-[10px] font-mono font-bold text-tierra-deep backdrop-blur-sm">
                Mercado ×{d.marketAppreciation.multiplier.toFixed(2)}
              </span>
            </>
          )}
        </div>
        <span className="rounded-lg border border-piedra-soft bg-papel/80 px-2 py-1 text-[9px] font-mono uppercase tracking-wider text-piedra backdrop-blur-sm">
          WebGPU · vgpu
        </span>
      </div>
    </div>
  );
}
