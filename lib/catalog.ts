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
    description: "Promedio anual del aire cerca de la superficie.",
    unit: "°C",
    family: "Calor",
    available: true,
    color: "#f2a58e",
    plannedSource:
      "NASA POWER · T2M (integración prevista, sin datos conectados)",
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
    description: "Promedio diario de precipitación, agregado por año.",
    unit: "mm/día",
    family: "Lluvia",
    available: true,
    color: "#83b8f5",
    plannedSource:
      "NASA POWER · PRECTOTCORR (integración prevista, sin datos conectados)",
  },
  {
    id: "rain5",
    name: "Lluvia máxima en cinco días",
    short: "Lluvia en 5 días",
    description: "Máximo anual acumulado en cinco días consecutivos.",
    unit: "mm",
    family: "Lluvia",
    available: false,
    color: "#83b8f5",
    plannedSource: "Producto por validar",
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
    description: "Contenido de agua en una capa superficial ilustrativa.",
    unit: "m³/m³",
    family: "Suelo",
    available: true,
    color: "#bdc997",
    plannedSource:
      "Producto y profundidad por validar; ninguna equivalencia con GLDAS aprobada",
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
  country: "México" | "Estados Unidos";
  countryCode: "MX" | "US";
  bbox: [number, number, number, number];
  lat: number;
  lon: number;
  extent: string;
}
export const regions: Region[] = [
  {
    id: "mx-northeast",
    name: "Noreste de México",
    country: "México",
    countryCode: "MX",
    bbox: [-101, 25, -99, 27],
    lat: 26,
    lon: -100,
    extent: "25–27° N · 101–99° O",
  },
  {
    id: "mx-northwest",
    name: "Noroeste de México",
    country: "México",
    countryCode: "MX",
    bbox: [-113, 29, -111, 31],
    lat: 30,
    lon: -112,
    extent: "29–31° N · 113–111° O",
  },
  {
    id: "us-texas",
    name: "Oeste de Texas",
    country: "Estados Unidos",
    countryCode: "US",
    bbox: [-103, 30, -101, 32],
    lat: 31,
    lon: -102,
    extent: "30–32° N · 103–101° O",
  },
  {
    id: "us-california",
    name: "California central",
    country: "Estados Unidos",
    countryCode: "US",
    bbox: [-121, 35, -119, 37],
    lat: 36,
    lon: -120,
    extent: "35–37° N · 121–119° O",
  },
];
export const getRegion = (id: string) => regions.find((r) => r.id === id)!;
