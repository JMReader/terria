export interface ParcelSector {
  id: string;
  name: string;
  hectares: number;
  crop: string;
  variety: string;
  ndvi: number;
  moisturePercent: number;
  expectedYield: string;
  soilHorizon: string;
  color: string;
  offsets: [number, number][];
}

export interface CadastreNeighborParcel {
  id: string;
  fieldId: string;
  name: string;
  hectares: number;
  crop?: string;
  color: string;
  offsets: [number, number][];
}

// 1. ACTIVE PORTFOLIO FIELDS (Interactive, real irregular pampa parcel boundaries)
export const FIELD_SECTORS_DATA: Record<string, ParcelSector[]> = {
  // Lote La Esperanza — Av. 11 de Septiembre (Coronel Olmedo, Córdoba)
  // Center: [-31.498, -64.136] - Matching user's satellite image (Av. 11 de Septiembre & Airfield)
  "la-esperanza": [
    {
      id: "esp-maiz",
      name: "Lote 1 — Maíz Tardío",
      hectares: 86.4,
      crop: "Maíz Tardío",
      variety: "DK 72-10 VTPRO4",
      ndvi: 0.88,
      moisturePercent: 88,
      expectedYield: "114 qq/ha",
      soilHorizon: "Hapludol Típico Serie Córdoba",
      color: "#eab308", // Maize Golden Yellow (OneSoil)
      offsets: [
        [0.0075, -0.0075],
        [0.0075, 0.0015],
        [0.0005, 0.0015],
        [0.0005, -0.0075],
        [0.0035, -0.0078],
        [0.0075, -0.0075],
      ],
    },
    {
      id: "esp-soja",
      name: "Lote 2 — Soja de 1ra",
      hectares: 142.0,
      crop: "Soja de 1ra",
      variety: "DM 46R18 Enlist",
      ndvi: 0.84,
      moisturePercent: 82,
      expectedYield: "46 qq/ha",
      soilHorizon: "Horizonte Árgico profundo a 45cm",
      color: "#dc2626", // Soy / Wheat Crimson Red (OneSoil)
      offsets: [
        [-0.0005, -0.0075],
        [-0.0005, 0.0015],
        [-0.0090, 0.0015],
        [-0.0090, -0.0075],
        [-0.0045, -0.0075],
        [-0.0045, -0.0058], // Indentation for historic farmstead & sheds
        [-0.0022, -0.0058],
        [-0.0022, -0.0075],
        [-0.0005, -0.0075],
      ],
    },
    {
      id: "esp-cebada",
      name: "Lote 3 — Cebada Cervecera",
      hectares: 115.6,
      crop: "Cebada Cervecera",
      variety: "Andreeta Quilmes",
      ndvi: 0.78,
      moisturePercent: 79,
      expectedYield: "54 qq/ha",
      soilHorizon: "Franco limoso de alta fertilidad",
      color: "#ca8a04", // Amber Gold (OneSoil)
      offsets: [
        [0.0075, 0.0023],
        [0.0075, 0.0086],
        [-0.0030, 0.0088], // Angled following rural windbreak
        [-0.0090, 0.0088],
        [-0.0090, 0.0023],
        [-0.0010, 0.0023],
        [0.0075, 0.0023],
      ],
    },
    {
      id: "esp-pastura",
      name: "Lote 4 — Bajo Hídrico & Pastura",
      hectares: 76.0,
      crop: "Pastizal & Cañada",
      variety: "Agropiro / Festuca",
      ndvi: 0.65,
      moisturePercent: 95,
      expectedYield: "Reserva Forrajera",
      soilHorizon: "Capa freática aflorante a 0.8m",
      color: "#16a34a", // Forest Green (OneSoil)
      offsets: [
        [0.0075, 0.0094],
        [0.0058, 0.0142], // Organic contour line along natural creek
        [-0.0012, 0.0152],
        [-0.0090, 0.0136],
        [-0.0090, 0.0094],
        [0.0075, 0.0094],
      ],
    },
  ],

  // Establecimiento Don Pedro (Pergamino, Buenos Aires)
  // Center: [-33.955, -60.485]
  "don-pedro": [
    {
      id: "dp-maiz",
      name: "Lote A — Maíz Temprano",
      hectares: 210,
      crop: "Maíz Temprano",
      variety: "Pioneer 2089 VYHR",
      ndvi: 0.89,
      moisturePercent: 89,
      expectedYield: "128 qq/ha",
      soilHorizon: "Argiudol Típico Clase I Serie Pergamino",
      color: "#eab308", // Maize Golden Yellow
      offsets: [
        [0.0130, -0.0150],
        [0.0130, -0.0035],
        [0.0095, -0.0018], // Diagonal chamfer along rural canal
        [0.0012, -0.0018],
        [0.0012, -0.0150],
        [0.0130, -0.0150],
      ],
    },
    {
      id: "dp-soja",
      name: "Lote B — Soja Premium",
      hectares: 270,
      crop: "Soja de 1ra",
      variety: "Don Mario 40R16 STS",
      ndvi: 0.86,
      moisturePercent: 91,
      expectedYield: "49 qq/ha",
      soilHorizon: "Suelo Clase I sin limitantes",
      color: "#dc2626", // Crimson Red
      offsets: [
        [-0.0010, -0.0150],
        [-0.0010, -0.0018],
        [-0.0125, -0.0018],
        [-0.0125, -0.0150],
        [-0.0075, -0.0150],
        [-0.0075, -0.0130], // Farmstead cutout
        [-0.0040, -0.0130],
        [-0.0040, -0.0150],
        [-0.0010, -0.0150],
      ],
    },
    {
      id: "dp-trigo",
      name: "Lote C — Trigo / Soja 2da",
      hectares: 200,
      crop: "Trigo Pan",
      variety: "Baguette 802",
      ndvi: 0.82,
      moisturePercent: 85,
      expectedYield: "56 qq/ha",
      soilHorizon: "Capacidad de almacenaje 310mm",
      color: "#ca8a04", // Amber Gold
      offsets: [
        [0.0125, -0.0006],
        [0.0125, 0.0125],
        [0.0035, 0.0145], // Angled boundary along tree shelterbelt
        [-0.0120, 0.0118],
        [-0.0120, -0.0006],
        [0.0125, -0.0006],
      ],
    },
  ],

  // Campo El Ombú (Venado Tuerto, Santa Fe)
  // Center: [-33.785, -61.865]
  "el-ombu": [
    {
      id: "ombu-maiz",
      name: "Lote Central — Maíz Tardío",
      hectares: 140,
      crop: "Maíz Tardío",
      variety: "Nidera AX 7784 VIPTERA3",
      ndvi: 0.81,
      moisturePercent: 82,
      expectedYield: "104 qq/ha",
      soilHorizon: "Clase IIe Serie Venado Tuerto",
      color: "#eab308", // Yellow
      offsets: [
        [0.0115, -0.0110],
        [0.0115, 0.0075],
        [0.0080, 0.0105], // Diagonal rural path
        [0.0010, 0.0105],
        [0.0010, -0.0110],
        [0.0115, -0.0110],
      ],
    },
    {
      id: "ombu-soja",
      name: "Lote Sur — Soja 2da",
      hectares: 110,
      crop: "Soja de 2da",
      variety: "Syngenta SYN 4x1 IPRO",
      ndvi: 0.76,
      moisturePercent: 78,
      expectedYield: "38 qq/ha",
      soilHorizon: "Siembra directa sobre rastrojo trigo",
      color: "#dc2626", // Red
      offsets: [
        [-0.0008, -0.0110],
        [-0.0008, 0.0105],
        [-0.0088, 0.0105],
        [-0.0088, -0.0110],
        [-0.0055, -0.0110],
        [-0.0055, -0.0088], // Windmill & corrals
        [-0.0030, -0.0088],
        [-0.0030, -0.0110],
        [-0.0008, -0.0110],
      ],
    },
    {
      id: "ombu-trigo",
      name: "Lote Este — Trigo / Girasol",
      hectares: 60,
      crop: "Trigo / Cobertura",
      variety: "Don Mario Ñandubay",
      ndvi: 0.79,
      moisturePercent: 80,
      expectedYield: "48 qq/ha",
      soilHorizon: "Suelo bien drenado con rastrojo",
      color: "#ca8a04", // Amber Gold
      offsets: [
        [0.0095, 0.0115],
        [0.0065, 0.0185],
        [-0.0078, 0.0170],
        [-0.0078, 0.0115],
        [0.0095, 0.0115],
      ],
    },
  ],

  // Finca San Jerónimo (Villa María, Córdoba)
  // Center: [-32.365, -63.145]
  "san-jeronimo": [
    {
      id: "sj-pivote1",
      name: "Pivote Central 1 — Trigo Riego",
      hectares: 140,
      crop: "Trigo Cervecero",
      variety: "Baguette 620 Premium",
      ndvi: 0.91,
      moisturePercent: 96,
      expectedYield: "62 qq/ha",
      soilHorizon: "Riego suplementario Valley 180mm",
      color: "#0284c7", // Sapphire Blue
      // 16-point circular pivot geometry
      offsets: [
        [0.0125, -0.0070],
        [0.0121, -0.0045],
        [0.0109, -0.0024],
        [0.0091, -0.0009],
        [0.0070, -0.0005],
        [0.0049, -0.0009],
        [0.0031, -0.0024],
        [0.0019, -0.0045],
        [0.0015, -0.0070],
        [0.0019, -0.0095],
        [0.0031, -0.0116],
        [0.0049, -0.0131],
        [0.0070, -0.0135],
        [0.0091, -0.0131],
        [0.0109, -0.0116],
        [0.0121, -0.0095],
        [0.0125, -0.0070],
      ],
    },
    {
      id: "sj-pivote2",
      name: "Pivote Central 2 — Maíz Riego",
      hectares: 140,
      crop: "Maíz Tardío",
      variety: "Dekalb 73-03 VT3P",
      ndvi: 0.88,
      moisturePercent: 94,
      expectedYield: "132 qq/ha",
      soilHorizon: "Lamina uniforme alta presión",
      color: "#0ea5e9", // Cyan
      // 16-point circular pivot geometry
      offsets: [
        [0.0125, 0.0065],
        [0.0121, 0.0090],
        [0.0109, 0.0111],
        [0.0091, 0.0126],
        [0.0070, 0.0130],
        [0.0049, 0.0126],
        [0.0031, 0.0111],
        [0.0019, 0.0090],
        [0.0015, 0.0065],
        [0.0019, 0.0040],
        [0.0031, 0.0019],
        [0.0049, 0.0004],
        [0.0070, 0.0000],
        [0.0091, 0.0004],
        [0.0109, 0.0019],
        [0.0121, 0.0040],
        [0.0125, 0.0065],
      ],
    },
    {
      id: "sj-secano",
      name: "Lote Sur — Soja de 1ra",
      hectares: 160,
      crop: "Soja de 1ra",
      variety: "Nidera NS 4309",
      ndvi: 0.79,
      moisturePercent: 81,
      expectedYield: "41 qq/ha",
      soilHorizon: "Secano alta productividad",
      color: "#dc2626", // Crimson Red
      offsets: [
        [-0.0010, -0.0135],
        [-0.0010, 0.0130],
        [-0.0125, 0.0130],
        [-0.0125, -0.0080],
        [-0.0085, -0.0135],
        [-0.0010, -0.0135],
      ],
    },
    {
      id: "sj-pastura",
      name: "Lote Cañada — Pastizal & Reserva",
      hectares: 80,
      crop: "Pastizal Natural",
      variety: "Festuca & Trébol Blanco",
      ndvi: 0.68,
      moisturePercent: 92,
      expectedYield: "Pastoreo Directo",
      soilHorizon: "Bajo tendido con napa superficial",
      color: "#16a34a", // Forest Green
      offsets: [
        [-0.0135, -0.0135],
        [-0.0135, 0.0130],
        [-0.0195, 0.0150],
        [-0.0210, 0.0030],
        [-0.0190, -0.0110],
        [-0.0135, -0.0135],
      ],
    },
  ],

  // Agropecuaria La Josefina (Balcarce, Buenos Aires)
  // Center: [-37.915, -58.325]
  "la-josefina": [
    {
      id: "jos-papa",
      name: "Lote Faldeo — Papa Semilla",
      hectares: 160,
      crop: "Papa Russet",
      variety: "Innovator / Spunta",
      ndvi: 0.88,
      moisturePercent: 90,
      expectedYield: "44 ton/ha",
      soilHorizon: "Suelo volcánico con tosca a 1.2m",
      color: "#ca8a04", // Amber Gold
      offsets: [
        [0.0125, -0.0120],
        [0.0135, -0.0015],
        [0.0090, 0.0065],
        [0.0035, 0.0085],
        [0.0012, -0.0010],
        [0.0012, -0.0120],
        [0.0125, -0.0120],
      ],
    },
    {
      id: "jos-cebada",
      name: "Lote Valle — Cebada Cervecera",
      hectares: 180,
      crop: "Cebada Cervecera",
      variety: "Shakira Maltería Pampa",
      ndvi: 0.84,
      moisturePercent: 86,
      expectedYield: "58 qq/ha",
      soilHorizon: "Franco arenoso profundo",
      color: "#dc2626", // Crimson Red
      offsets: [
        [-0.0008, -0.0120],
        [-0.0008, 0.0010],
        [0.0020, 0.0095],
        [-0.0065, 0.0135],
        [-0.0115, 0.0080],
        [-0.0115, -0.0080],
        [-0.0075, -0.0120],
        [-0.0008, -0.0120],
      ],
    },
    {
      id: "jos-girasol",
      name: "Lote Loma — Girasol Alto Oleico",
      hectares: 110,
      crop: "Girasol Alto Oleico",
      variety: "Nidera Paraíso 102 CL",
      ndvi: 0.82,
      moisturePercent: 84,
      expectedYield: "32 qq/ha",
      soilHorizon: "Pendiente 2% con curvas de nivel",
      color: "#eab308", // Golden Yellow
      offsets: [
        [0.0125, 0.0080],
        [0.0145, 0.0185],
        [0.0025, 0.0215],
        [-0.0055, 0.0145],
        [0.0035, 0.0095],
        [0.0125, 0.0080],
      ],
    },
  ],
};

// 2. SURROUNDING CADASTRAL LANDSCAPE LOTS (OneSoil-style real neighbor parcels)
// Authentic agricultural cadastre mosaic with roads, tracks and fence buffers
export const NEIGHBOR_CADASTRE_PARCELS: CadastreNeighborParcel[] = [
  // --- Surrounding Lote La Esperanza (Av. 11 de Septiembre, Coronel Olmedo, Córdoba) ---
  {
    id: "rc-vecino-norte-1",
    fieldId: "la-esperanza",
    name: "Parcela Rural Noroeste (Maíz)",
    hectares: 75,
    crop: "Maíz",
    color: "#eab308", // Golden Yellow
    offsets: [
      [0.0085, -0.0075],
      [0.0165, -0.0075],
      [0.0165, 0.0015],
      [0.0085, 0.0015],
      [0.0085, -0.0075],
    ],
  },
  {
    id: "rc-vecino-norte-2",
    fieldId: "la-esperanza",
    name: "Parcela Rural Noreste (Trigo)",
    hectares: 92,
    crop: "Trigo",
    color: "#dc2626", // Crimson Red
    offsets: [
      [0.0085, 0.0023],
      [0.0165, 0.0023],
      [0.0165, 0.0086],
      [0.0085, 0.0086],
      [0.0085, 0.0023],
    ],
  },
  {
    id: "rc-vecino-sur-1",
    fieldId: "la-esperanza",
    name: "Chacra Sur (Barbecho)",
    hectares: 88,
    crop: "Barbecho",
    color: "#475569", // Slate Gray
    offsets: [
      [-0.0098, -0.0075],
      [-0.0175, -0.0075],
      [-0.0175, 0.0015],
      [-0.0098, 0.0015],
      [-0.0098, -0.0075],
    ],
  },
  {
    id: "rc-vecino-sur-2",
    fieldId: "la-esperanza",
    name: "Chacra Sudeste (Soja)",
    hectares: 64,
    crop: "Soja",
    color: "#ca8a04", // Amber Gold
    offsets: [
      [-0.0098, 0.0023],
      [-0.0175, 0.0023],
      [-0.0175, 0.0088],
      [-0.0098, 0.0088],
      [-0.0098, 0.0023],
    ],
  },
  {
    id: "rc-vecino-pista-1",
    fieldId: "la-esperanza",
    name: "Buffer Pista Aeródromo (Pastura)",
    hectares: 55,
    crop: "Pastura Natural",
    color: "#16a34a", // Forest Green
    offsets: [
      [0.0012, -0.0085],
      [0.0135, -0.0085],
      [0.0012, -0.0155], // Triangular runway approach
      [0.0012, -0.0085],
    ],
  },
  {
    id: "rc-vecino-pista-2",
    fieldId: "la-esperanza",
    name: "Cabecera Pista (Rastrojo)",
    hectares: 42,
    crop: "Rastrojo",
    color: "#475569", // Gray
    offsets: [
      [-0.0092, -0.0085],
      [0.0005, -0.0085],
      [-0.0092, -0.0150],
      [-0.0092, -0.0085],
    ],
  },
  {
    id: "rc-vecino-este-1",
    fieldId: "la-esperanza",
    name: "Chacra Este (Trigo)",
    hectares: 110,
    crop: "Trigo",
    color: "#dc2626", // Crimson Red
    offsets: [
      [0.0075, 0.0150],
      [0.0165, 0.0150],
      [0.0165, 0.0225],
      [0.0075, 0.0225],
      [0.0075, 0.0150],
    ],
  },
  {
    id: "rc-vecino-este-2",
    fieldId: "la-esperanza",
    name: "Chacra Este 2 (Maíz)",
    hectares: 85,
    crop: "Maíz",
    color: "#eab308", // Golden Yellow
    offsets: [
      [-0.0095, 0.0145],
      [0.0068, 0.0145],
      [0.0068, 0.0225],
      [-0.0095, 0.0225],
      [-0.0095, 0.0145],
    ],
  },

  // --- Surrounding Pergamino ("don-pedro") ---
  {
    id: "dp-lindero-norte",
    fieldId: "don-pedro",
    name: "Establecimiento Vecino Norte (Maíz)",
    hectares: 210,
    crop: "Maíz",
    color: "#eab308",
    offsets: [
      [0.0140, -0.0150],
      [0.0245, -0.0150],
      [0.0245, 0.0125],
      [0.0140, 0.0125],
      [0.0140, -0.0150],
    ],
  },
  {
    id: "dp-lindero-sur",
    fieldId: "don-pedro",
    name: "Establecimiento Vecino Sur (Trigo)",
    hectares: 190,
    crop: "Trigo",
    color: "#dc2626",
    offsets: [
      [-0.0235, -0.0150],
      [-0.0135, -0.0150],
      [-0.0135, 0.0125],
      [-0.0235, 0.0125],
      [-0.0235, -0.0150],
    ],
  },
  {
    id: "dp-lindero-este",
    fieldId: "don-pedro",
    name: "Campo Vecino Este (Barbecho)",
    hectares: 180,
    crop: "Barbecho",
    color: "#475569",
    offsets: [
      [-0.0125, 0.0135],
      [0.0130, 0.0135],
      [0.0130, 0.0260],
      [-0.0125, 0.0260],
      [-0.0125, 0.0135],
    ],
  },

  // --- Surrounding Venado Tuerto ("el-ombu") ---
  {
    id: "ombu-lindero-norte",
    fieldId: "el-ombu",
    name: "Chacra Lindera Norte (Soja)",
    hectares: 160,
    crop: "Soja",
    color: "#dc2626",
    offsets: [
      [0.0125, -0.0110],
      [0.0225, -0.0110],
      [0.0225, 0.0105],
      [0.0125, 0.0105],
      [0.0125, -0.0110],
    ],
  },
  {
    id: "ombu-lindero-sur",
    fieldId: "el-ombu",
    name: "Chacra Lindera Sur (Maíz)",
    hectares: 140,
    crop: "Maíz",
    color: "#eab308",
    offsets: [
      [-0.0185, -0.0110],
      [-0.0098, -0.0110],
      [-0.0098, 0.0105],
      [-0.0185, 0.0105],
      [-0.0185, -0.0110],
    ],
  },
  {
    id: "ombu-lindero-oeste",
    fieldId: "el-ombu",
    name: "Chacra Lindera Oeste (Pastura)",
    hectares: 130,
    crop: "Pastura Natural",
    color: "#16a34a",
    offsets: [
      [-0.0088, -0.0220],
      [0.0115, -0.0220],
      [0.0115, -0.0120],
      [-0.0088, -0.0120],
      [-0.0088, -0.0220],
    ],
  },

  // --- Surrounding Villa María ("san-jeronimo") ---
  {
    id: "sj-lindero-norte",
    fieldId: "san-jeronimo",
    name: "Finca Lindera Norte (Trigo)",
    hectares: 220,
    crop: "Trigo",
    color: "#dc2626",
    offsets: [
      [0.0135, -0.0135],
      [0.0240, -0.0135],
      [0.0240, 0.0128],
      [0.0135, 0.0128],
      [0.0135, -0.0135],
    ],
  },
  {
    id: "sj-lindero-este",
    fieldId: "san-jeronimo",
    name: "Finca Lindera Este (Maíz)",
    hectares: 180,
    crop: "Maíz",
    color: "#eab308",
    offsets: [
      [-0.0120, 0.0140],
      [0.0125, 0.0140],
      [0.0125, 0.0255],
      [-0.0120, 0.0255],
      [-0.0120, 0.0140],
    ],
  },

  // --- Surrounding Balcarce ("la-josefina") ---
  {
    id: "jos-lindero-norte",
    fieldId: "la-josefina",
    name: "Lote Serrano Norte (Papa)",
    hectares: 170,
    crop: "Papa",
    color: "#ca8a04",
    offsets: [
      [0.0135, -0.0130],
      [0.0235, -0.0130],
      [0.0235, 0.0128],
      [0.0135, 0.0128],
      [0.0135, -0.0130],
    ],
  },
  {
    id: "jos-lindero-sur",
    fieldId: "la-josefina",
    name: "Lote Serrano Sur (Cebada)",
    hectares: 150,
    crop: "Cebada",
    color: "#dc2626",
    offsets: [
      [-0.0195, -0.0130],
      [-0.0125, -0.0130],
      [-0.0125, 0.0128],
      [-0.0195, 0.0128],
      [-0.0195, -0.0130],
    ],
  },
];
