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
    description: "Temperatura media a 2 m; serie POWER 1992–2024.",
    unit: "°C",
    family: "Calor",
    available: true,
    color: "#f2a58e",
    plannedSource: "NASA POWER · T2M, datos integrados",
  },
  {
    id: "temperature-min",
    name: "Temperatura mínima mensual (POWER)",
    short: "T mínima POWER",
    description: "T2M_MIN mensual a 2 m. No cuenta noches cálidas.",
    unit: "°C",
    family: "Calor",
    available: true,
    color: "#e9b59b",
    plannedSource: "NASA POWER · T2M_MIN, datos integrados",
  },
  {
    id: "temperature-max",
    name: "Temperatura máxima mensual (POWER)",
    short: "T máxima POWER",
    description: "T2M_MAX mensual a 2 m. No mide olas de calor.",
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
    name: "Precipitación media",
    short: "Precipitación",
    description: "Precipitación media mensual GPCP, resumida por año.",
    unit: "mm/día",
    family: "Lluvia",
    available: true,
    color: "#83b8f5",
    plannedSource: "NASA Giovanni · GPCP, datos integrados",
  },
  {
    id: "precipitation-power",
    name: "Precipitación corregida (POWER)",
    short: "Lluvia POWER",
    description: "PRECTOTCORR mensual en mm/día. Fuente distinta de GPCP.",
    unit: "mm/día",
    family: "Lluvia",
    available: true,
    color: "#6ac9d5",
    plannedSource: "NASA POWER · PRECTOTCORR, datos integrados",
  },
  {
    id: "rain5",
    name: "RX5Day mensual (Giovanni)",
    short: "RX5Day Giovanni",
    description: "Índice mensual RX5Day de Giovanni, resumido por año.",
    unit: "mm",
    family: "Lluvia",
    available: true,
    color: "#83b8f5",
    plannedSource: "NASA Giovanni · MERRA-2 RX5Day, datos integrados",
  },
  {
    id: "rain5-power-annual",
    name: "RX5day anual derivado de POWER",
    short: "RX5day POWER",
    description: "Máximo anual de cinco días calculado desde precipitación diaria; requiere 20 años.",
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
