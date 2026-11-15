export type VariableId =
  | "temperature"
  | "temperature-min"
  | "temperature-max"
  | "warm-nights"
  | "heatwave"
  | "precipitation"
  | "precipitation-power"
  | "rain5"
  | "rain5-power-annual"
  | "extreme-rain"
  | "surface-moisture"
  | "deep-moisture"
  | "evapotranspiration";
export type Family = "Calor" | "Lluvia" | "Suelo";
export interface Variable {
  id: VariableId;
  name: string;
  short: string;
  description: string;
  unit: string;
  family: Family;
  available: boolean;
  color: string;
  plannedSource: string;
}
export const variables: Variable[] = [
  {
    id: "temperature",
    name: "Temperatura media del aire",
    short: "Temperatura",
    description: "Promedio mensual de la temperatura del aire a 2 m del suelo.",
    unit: "°C",
    family: "Calor",
    available: true,
    color: "#f2a58e",
    plannedSource: "NASA POWER · T2M, datos integrados",
  },
  {
    id: "temperature-min",
    name: "Temperatura mínima",
    short: "T mínima",
    description: "Serie mensual de temperatura mínima, según NASA POWER.",
    unit: "°C",
    family: "Calor",
    available: true,
    color: "#e9b59b",
    plannedSource: "NASA POWER · T2M_MIN, datos integrados",
  },
  {
    id: "temperature-max",
    name: "Temperatura máxima",
    short: "T máxima",
    description: "Serie mensual de temperatura máxima, según NASA POWER.",
    unit: "°C",
    family: "Calor",
    available: true,
    color: "#f48a6c",
    plannedSource: "NASA POWER · T2M_MAX, datos integrados",
  },
  {
    id: "warm-nights",
    name: "Noches cálidas",
    short: "Noches cálidas",
    description:
      "Noches que superan un umbral de referencia; definición pendiente.",
    unit: "días/año",
    family: "Calor",
    available: false,
    color: "#f2a58e",
    plannedSource: "Producto por validar",
  },
  {
    id: "heatwave",
    name: "Días en ola de calor",
    short: "Olas de calor",
    description: "Requiere umbral y duración definidos y datos diarios.",
    unit: "días/año",
    family: "Calor",
    available: false,
    color: "#f2a58e",
    plannedSource: "Producto por validar",
  },
  {
    id: "precipitation",
    name: "Lluvia media (GPCP)",
    short: "Lluvia GPCP",
    description: "Promedio mensual de lluvia, según el producto GPCP.",
    unit: "mm/día",
    family: "Lluvia",
    available: true,
    color: "#83b8f5",
    plannedSource: "NASA Giovanni · GPCP, datos integrados",
  },
  {
    id: "precipitation-power",
    name: "Lluvia media (POWER)",
    short: "Lluvia POWER",
    description: "Promedio mensual de lluvia, según NASA POWER.",
    unit: "mm/día",
    family: "Lluvia",
    available: true,
    color: "#6ac9d5",
    plannedSource: "NASA POWER · PRECTOTCORR, datos integrados",
  },
  {
    id: "rain5",
    name: "Mayor lluvia en 5 días (mensual)",
    short: "Lluvia en 5 días",
    description: "Mayor acumulado de cinco días de cada mes; fuente Giovanni.",
    unit: "mm",
    family: "Lluvia",
    available: true,
    color: "#83b8f5",
    plannedSource: "NASA Giovanni · MERRA-2 RX5Day, datos integrados",
  },
  {
    id: "rain5-power-annual",
    name: "Mayor lluvia en 5 días (anual)",
    short: "Máxima de 5 días anual",
    description: "Mayor acumulado de cinco días de cada año, calculado con datos diarios. Requiere 20 años.",
    unit: "mm",
    family: "Lluvia",
    available: true,
    color: "#4f9df3",
    plannedSource: "NASA POWER · PRECTOTCORR diario, índice derivado",
  },
  {
    id: "extreme-rain",
    name: "Precipitación en días extremos",
    short: "Lluvia extrema",
    description: "Acumulado sobre un percentil; referencia pendiente.",
    unit: "mm/año",
    family: "Lluvia",
    available: false,
    color: "#83b8f5",
    plannedSource: "Producto por validar",
  },
  {
    id: "surface-moisture",
    name: "Humedad superficial",
    short: "Humedad del suelo",
    description: "Contenido de agua en una capa superficial; producto por validar.",
    unit: "m³/m³",
    family: "Suelo",
    available: false,
    color: "#bdc997",
    plannedSource: "FLDAS pendiente; ninguna serie descargada",
  },
  {
    id: "deep-moisture",
    name: "Humedad profunda",
    short: "Humedad profunda",
    description: "Requiere un producto y una profundidad definidos.",
    unit: "m³/m³",
    family: "Suelo",
    available: false,
    color: "#bdc997",
    plannedSource: "Producto por validar",
  },
  {
    id: "evapotranspiration",
    name: "Evapotranspiración",
    short: "Evapotranspiración",
    description: "Agua transferida del suelo y la vegetación a la atmósfera.",
    unit: "mm/día",
    family: "Suelo",
    available: false,
    color: "#bdc997",
    plannedSource: "Producto por validar",
  },
];
export const getVariable = (id: VariableId) =>
  variables.find((v) => v.id === id)!;
export interface Region {
  id: string;
  name: string;
  country: "México";
  countryCode: "MX";
  bbox: [number, number, number, number];
  lat: number;
  lon: number;
  extent: string;
}
export const regions: Region[] = [
  {
    id: "mx-northeast",
    name: "Caja del noreste de México",
    country: "México",
    countryCode: "MX",
    bbox: [-101, 25, -99, 27],
    lat: 26,
    lon: -100,
    extent: "25–27° N · 101–99° O",
  },
  {
    id: "mx-chihuahua-interior",
    name: "Chihuahua interior",
    country: "México",
    countryCode: "MX",
    bbox: [-107, 28, -105, 30],
    lat: 29,
    lon: -106,
    extent: "28–30° N · 107–105° O",
  },
  {
    id: "mx-south-humid",
    name: "Caja sur · Chiapas–Tabasco",
    country: "México",
    countryCode: "MX",
    bbox: [-94, 16, -92, 18],
    lat: 17,
    lon: -93,
    extent: "16–18° N · 94–92° O",
  },
];
export const getRegion = (id: string) => regions.find((r) => r.id === id)!;
