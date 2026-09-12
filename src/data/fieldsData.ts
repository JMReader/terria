export interface FieldItem {
  id: string;
  code: string;
  name: string;
  locality: string;
  province: string;
  coordinates: string;
  lat: number;
  lng: number;
  hectares: number;
  primaryCrop: string;
  secondaryCrop?: string;
  suitabilityScore: number;
  soilSeries: string;
  rentUsdHa: number;
  rentQqSoja: number;
  ndvi: number;
  waterTable: string;
  irrigation: boolean;
  status: "disponible" | "en_negociacion" | "destacado";
  tags: string[];
  description: string;
}

export const FIELDS_DATA: FieldItem[] = [
  {
    id: "la-esperanza",
    code: "CAMPO 01",
    name: "Lote 'La Esperanza' — Av. 11 de Septiembre",
    locality: "Coronel Olmedo",
    province: "Córdoba",
    coordinates: "31°29'S 64°08'W",
    lat: -31.498,
    lng: -64.136,
    hectares: 420,
    primaryCrop: "Maíz Tardío (86.4 ha)",
    secondaryCrop: "Soja de 1ra (142 ha)",
    suitabilityScore: 95,
    soilSeries: "Clase IIw — Serie Córdoba Cinturón Productivo",
    rentUsdHa: 190,
    rentQqSoja: 12.0,
    ndvi: 0.86,
    waterTable: "Óptima a 1.8m",
    irrigation: false,
    status: "destacado",
    tags: ["Av. 11 de Septiembre", "Frente Asfalto", "Alta Productividad", "Suelo Clase II"],
    description: "Excelente establecimiento agropecuario ubicado sobre Avenida 11 de Septiembre (Coronel Olmedo, Córdoba). Lotes con delimitaciones reales bien definidas por caminos rurales y alambrados perimetrales. Historial de rotación maíz/soja de alto rendimiento y napa freática en cota estival.",
  },
  {
    id: "don-pedro",
    code: "CAMPO 02",
    name: "Establecimiento 'Don Pedro'",
    locality: "Pergamino",
    province: "Buenos Aires",
    coordinates: "33°57'S 60°29'W",
    lat: -33.955,
    lng: -60.485,
    hectares: 680,
    primaryCrop: "Soja de 1ra (98%)",
    secondaryCrop: "Maíz Temprano",
    suitabilityScore: 98,
    soilSeries: "Clase I — Argiudol Típico Serie Pergamino",
    rentUsdHa: 240,
    rentQqSoja: 15.0,
    ndvi: 0.89,
    waterTable: "Excelente a 1.4m",
    irrigation: false,
    status: "disponible",
    tags: ["Zona Núcleo Premium", "Suelo Clase I", "Rinde Histórico Top"],
    description: "Campo de máxima productividad en el corazón de la Zona Núcleo rural de Pergamino. Suelos profundos sin limitantes físico-químicas, con capacidad de almacenaje de agua de 300 mm.",
  },
  {
    id: "el-ombu",
    code: "CAMPO 03",
    name: "Campo 'El Ombú'",
    locality: "Venado Tuerto",
    province: "Santa Fe",
    coordinates: "33°47'S 61°51'W",
    lat: -33.785,
    lng: -61.865,
    hectares: 310,
    primaryCrop: "Maíz / Trigo (91%)",
    secondaryCrop: "Soja de 2da",
    suitabilityScore: 91,
    soilSeries: "Clase IIe — Hapludol Serie Venado Tuerto",
    rentUsdHa: 175,
    rentQqSoja: 11.0,
    ndvi: 0.79,
    waterTable: "Moderada a 2.3m",
    irrigation: false,
    status: "disponible",
    tags: ["Rotación Intensiva", "Galpón y Silos", "Luz Trifásica"],
    description: "Lote altamente tecnificado en el cinturón agrícola de Venado Tuerto con conectividad e infraestructura completa para almacenamiento y monitoreo de siembra variable.",
  },
  {
    id: "san-jeronimo",
    code: "CAMPO 04",
    name: "Finca 'San Jerónimo'",
    locality: "Villa María",
    province: "Córdoba",
    coordinates: "32°21'S 63°08'W",
    lat: -32.365,
    lng: -63.145,
    hectares: 520,
    primaryCrop: "Trigo / Soja 2da (92%)",
    secondaryCrop: "Maíz Bajo Riego",
    suitabilityScore: 92,
    soilSeries: "Clase IIs — Serie Ballesteros",
    rentUsdHa: 195,
    rentQqSoja: 12.0,
    ndvi: 0.82,
    waterTable: "Riego Pivote Central",
    irrigation: true,
    status: "en_negociacion",
    tags: ["2 Pivotes de Riego", "Trigo Cervecero", "Energía Solar"],
    description: "Campo mixto agrícola en la cuenca rural de Villa María con 280 ha bajo riego suplementario por pivote central Valley. Garantía de rendimiento aún en campañas de déficit hídrico.",
  },
  {
    id: "la-josefina",
    code: "CAMPO 05",
    name: "Agropecuaria 'La Josefina'",
    locality: "Balcarce",
    province: "Buenos Aires",
    coordinates: "37°55'S 58°19'W",
    lat: -37.915,
    lng: -58.325,
    hectares: 450,
    primaryCrop: "Papa / Cebada (88%)",
    secondaryCrop: "Girasol Alto Oleico",
    suitabilityScore: 88,
    soilSeries: "Clase III — Argiudol Lítico Serie Mar del Plata",
    rentUsdHa: 210,
    rentQqSoja: 13.0,
    ndvi: 0.81,
    waterTable: "Subterránea a 2.2m",
    irrigation: true,
    status: "disponible",
    tags: ["Apto Papa", "Cebada de Exportación", "Microclima Sureste"],
    description: "Ubicado en el polo de papa y cebada en los valles agrícolas del sudeste bonaerense. Suelo con alto tenor de materia orgánica (4.8%) y óptima fertilidad natural.",
  },
];
