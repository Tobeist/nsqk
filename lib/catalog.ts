export type VariableId =
  | "temperature"
  | "warm-nights"
  | "heatwave"
  | "precipitation"
  | "rain5"
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
    id: "rain5",
    name: "Lluvia máxima en cinco días",
    short: "Lluvia en 5 días",
    description: "Índice mensual RX5Day de Giovanni, resumido por año.",
    unit: "mm",
    family: "Lluvia",
    available: true,
    color: "#83b8f5",
    plannedSource: "NASA Giovanni · MERRA-2 RX5Day, datos integrados",
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
];
export const getRegion = (id: string) => regions.find((r) => r.id === id)!;
