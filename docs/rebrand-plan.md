# Re-brand TERRIA — Plan del Front

Del brand board ("La tierra tiene memoria") al front real:
`/Users/korita/hackathon/terria-frontend` — **Next.js 16 + React 19 + Tailwind v4 +
Three.js/VGPU + GSAP + mapa (mapbox-gl en esta rama; MapLibre en `master`)**.

> Estado: propuesta. Todavía no se tocó código.

---

## 1. Qué hay hoy

Una sola pantalla estilo "app" (`page.tsx`): `FloatingIslandHeader` + viewport 3D a
la izquierda (`Planet3D` / `Field3DIsoViewer` / `TimelapseTerrainGPU` /
`ValuationGrowthGPU`) + feed de cards a la derecha (`FieldCardsList` →
`FieldDetailView`). `globals.css` fija `h-screen overflow-hidden`: **no hay
landing ni scroll**.

Estética actual: SaaS genérico. Slate `#f8fafc`, `blue-600` por todos lados
(~90 refs), **neón esmeralda** (~102 refs, boundary "OneSoil" + cortina
holográfica), estados amber/purple, fuentes Geist. La marca pide lo contrario:
editorial, institucional, tierra primero, tecnología invisible.

## 2. Tokens de marca → `globals.css` (`@theme` de Tailwind v4)

```css
@theme {
  /* Paleta del board */
  --color-bosque: #1C3A2E;  /* tinta, hero, footer */
  --color-musgo:  #4A6B46;  /* acento primario / verified */
  --color-oliva:  #8A9A6B;  /* acento secundario, NDVI */
  --color-piedra: #A7A7A0;  /* muted, hairlines, metadata */
  --color-cielo:  #7BA7D9;  /* reservado: capa satélite / IA */
  --color-nube:   #F4F6F2;  /* superficie base */
  --color-tierra: #C9B28A;  /* sellos, acentos premium */

  /* Semánticos */
  --color-ink: var(--color-bosque);
  --color-surface: var(--color-nube);
  --color-accent: var(--color-musgo);
  --color-data: var(--color-cielo);
  --color-seal: var(--color-tierra);
  --color-muted: var(--color-piedra);

  --font-display: var(--font-fraunces), Georgia, serif;
}
```

Con `@theme` eso genera `bg-nube`, `text-bosque`, `border-piedra/40`,
`font-display`, etc. — un solo lugar para reskin todo.

## 3. Tipografía

| Rol | Fuente | Uso |
|---|---|---|
| Display | **Fraunces** (next/font/google) | wordmark TERRIA, titulares, hero |
| Sans | Geist (ya está) | UI, botones, labels |
| Mono | Geist Mono (ya está) | coordenadas, hashes, V01..V04, timestamps |

Tensión editorial ↔ data: titular serif amplio + microtipografía mono debajo
(coordenadas, estado `VERIFIED`). Sumar Fraunces en `layout.tsx` como tercera
variable de fuente; metadata → "TERRIA — Certificación de parcelas".

## 4. Estructura nueva (landing → producto)

Sacar el `overflow-hidden` global. `page.tsx` pasa a ser scroll narrativo; la app
actual se encapsula como sección.

```
<SiteHeader/>        header fijo: BrandMark + links + pill API/demo
<Hero/>              viewport completo, fondo bosque
<ExplorerSection/>   la app actual tal cual (Planet3D + cards → detail)
<CertificateSection/>"Parcel Certificate" premium
<SiteFooter/>        bosque, tagline, coords mono
```

- **Hero**: serif `El campo también tiene memoria.` + sub
  `Blockchain + IA para la historia del campo.` + strip mono
  (`33.89° S · 60.57° W · V04 · VERIFIED`) + CTA que scrollea al explorador.
  Fondo: `ContourLines` (SVG de estratos/curvas de nivel que se dibuja con GSAP).
- **ExplorerSection**: hoy ya es "mapa + cards" — queda debajo del hero sin
  cambios estructurales, solo reskin.
- **CertificateSection**: documento con id de parcela, coordenadas, timeline de
  cultivos, hash mono, sello `VERIFIED` tierra, QR. Datos del `public_slug` real
  cuando haya backend; mock si no.

## 5. Componentes reutilizables nuevos

| Componente | Rol |
|---|---|
| `BrandMark.tsx` | estratos SVG + wordmark; header, hero, certificado, footer, favicon |
| `ContourLines.tsx` | patrón de estratos; fondos hero/cert/footer |
| `Seal.tsx` | sello `VERIFIED`/`DEMO`/`PARCIAL` en tierra/musgo/piedra |
| `CoordinateTag.tsx` | coords mono reutilizable |
| `SectionHeading.tsx` | títulos serif + kicker mono consistentes |
| `VersionTimeline.tsx` | datasets como `V01 ─ V04` con fecha/cultivo/estado |
| `ParcelCertificate.tsx` | el certificado (usable también standalone) |

## 6. Reskin de lo existente (componente por componente)

| Hoy | Cambio |
|---|---|
| `FloatingIslandHeader` | pill nube/bosque, wordmark serif, pill de estado musgo |
| `FieldCard` | border piedra, nombre serif, coords mono, selección blue-600 → bosque, aptitud → tierra, tags → outline piedra |
| `Planet3D` | halo/border neón → stroke bosque + glow tierra sutil; sky/grilla cartográfica piedra sobre nube; pins bosque |
| `Field3DIsoViewer` | neón esmeralda + cortina holográfica → boundary bosque + hatch piedra; capas NDVI en rampa oliva→musgo |
| `TimelapseController` | mismo control, skin nube/bosque; labels V01..Vn |
| `NdviMetricCard` / `SparklineChart` | barras blue → rampa oliva/musgo |
| `SolanaAuditCard` / `ValuationAuditCard` | formato "certificado": sello, hash mono, sin estética crypto |
| `FieldDetailView` | se lee como "Pasaporte de parcela": header documento, tabs sobrios |
| `WebGpuCosmicGrid` | de cósmica a grilla cartográfica (hairlines piedra en nube) |
| `MetricStatBox`, `NaturalLanguageSearch`, `WeatherDailyCard` | mismos tokens: nube, piedra, bosque |

### Mapa de reemplazo de color

- `blue-*` → `bosque`/`musgo` (acciones, selección, links)
- `emerald`/neon → boundary `bosque` + sello `tierra`
- `amber` → `tierra`; `purple` → `piedra`
- `sky`/`cyan` → `cielo` (**solo** capa satélite/IA — la IA es una capa sobre la tierra, no protagonista)
- `slate`/`gray` → `nube`/`piedra`
- NDVI: `oliva`→`musgo`

## 7. Motion (GSAP se queda, cambia el lenguaje)

Estratos que se dibujan, capas que se apilan hasta "sellarse" en `VERIFIED`,
reveals al scroll. Preciso, silencioso, inevitable — no explosivo ni sci-fi.

## 8. Fases

1. **Tokens + tipografía**: `globals.css`, Fraunces, sacar `overflow-hidden`.
2. **Landing**: `BrandMark`, `SiteHeader`, `Hero`, `SectionHeading`, footer.
3. **Cards y badges**: FieldCard/List, MetricStatBox, seals, search.
4. **Mapa/3D + detalle**: Planet3D, IsoViewer, CosmicGrid, detail → pasaporte.
5. **Certificado + versiones + polish**: ParcelCertificate, VersionTimeline,
   favicon, metadata, OG.

## 9. Ojo con

- **AGENTS.md del repo**: Next 16 difiere del estándar — antes de codear, leer lo
  que aplique en `node_modules/next/dist/docs/`.
- **Divergencia de ramas**: este clon está en `feat/timelapse-live-vgpu` con
  `mapbox-gl` y cambios sin commitear; `master` remoto ya migró a MapLibre. Hay
  que alinear con el equipo sobre qué base se reskinea el mapa.
- `public/` tiene texturas del planeta y worker CSP de mapbox: revisar qué sigue
  aplicando según la rama que quede.
