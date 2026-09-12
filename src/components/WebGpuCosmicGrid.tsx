"use client";

import React, { useEffect, useRef, useState } from "react";

export default function WebGpuCosmicGrid() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [hasWebGpu, setHasWebGpu] = useState(false);

  useEffect(() => {
    let disposed = false;
    let cleanupFn: (() => void) | null = null;

    async function setupWebGPU() {
      if (typeof window === "undefined" || !("gpu" in navigator) || !canvasRef.current) {
        return;
      }
      try {
        const { init, surface, effect, frameLoop, clock } = await import("vgpu");
        const gpu = await init();
        if (disposed || !canvasRef.current) {
          gpu.dispose();
          return;
        }

        const canvas = canvasRef.current;
        const canvasSurface = surface(gpu, canvas, { dpr: [1, 2] });

        // Clean light mode subtle shader
        const subtleShader = `
          struct Params {
            time: f32,
            width: f32,
            height: f32,
            pad: f32,
          };
          @group(0) @binding(0) var<uniform> params: Params;

          @fragment
          fn fs_main(@location(0) uv: vec2f) -> @location(0) vec4f {
            let aspect = params.width / max(params.height, 1.0);
            
            // Ultra-subtle light grid
            let gridUv = uv * vec2f(40.0 * aspect, 40.0);
            let grid = step(0.98, fract(gridUv.x)) + step(0.98, fract(gridUv.y));
            let gridVal = grid * 0.025;

            // Very soft light gradient
            let baseColor = vec3f(0.975, 0.982, 0.99) - vec3f(gridVal);
            return vec4f(baseColor, 0.5);
          }
        `;

        const lightEffect = effect(gpu, subtleShader, {
          set: {
            params: {
              time: 0,
              width: canvas.clientWidth || 800,
              height: canvas.clientHeight || 600,
              pad: 0,
            },
          },
        });

        canvasSurface.onResize(() => {
          lightEffect.set({
            params: {
              width: canvas.clientWidth || 800,
              height: canvas.clientHeight || 600,
            },
          });
        });

        const timeTracker = clock(gpu);
        const loopHandle = frameLoop(gpu, (frame) => {
          lightEffect.set({
            params: {
              time: timeTracker.time,
            },
          });
          frame.pass(canvasSurface, lightEffect);
        });

        setHasWebGpu(true);

        cleanupFn = () => {
          try {
            loopHandle.stop();
            gpu.dispose();
          } catch {}
        };
      } catch (err) {
        console.info("WebGPU ambient canvas using light CSS fallback");
      }
    }

    setupWebGPU();

    return () => {
      disposed = true;
      if (cleanupFn) cleanupFn();
    };
  }, []);

  return (
    <div className="pointer-events-none absolute inset-0 z-0 overflow-hidden">
      <canvas
        ref={canvasRef}
        className={`h-full w-full transition-opacity duration-1000 ${
          hasWebGpu ? "opacity-60" : "opacity-0"
        }`}
      />
      {/* Soft light clean background */}
      <div className="absolute inset-0 bg-gradient-to-b from-[#f8fafc] via-[#f1f5f9]/60 to-[#f8fafc]" />
    </div>
  );
}
