import type { VariableId } from "./catalog";

export interface SourceLink {
  label: string;
  href: string;
  description: string;
}

const monthlyPower: SourceLink = {
  label: "NASA POWER",
  href: "https://power.larc.nasa.gov/docs/services/api/temporal/monthly/",
  description: "Series mensuales de temperatura o precipitación de POWER, procedentes de MERRA-2.",
};
const nino34: SourceLink = {
  label: "NOAA · Niño 3.4",
  href: "https://www.cpc.ncep.noaa.gov/data/indices/ersst5.nino.mth.91-20.ascii",
  description: "Índice mensual ERSSTv5 Niño 3.4, base 1991–2020, utilizado como control de ENSO.",
};
const sources: Partial<Record<VariableId, SourceLink>> = {
  temperature: monthlyPower,
  "temperature-min": monthlyPower,
  "temperature-max": monthlyPower,
  "precipitation-power": monthlyPower,
  precipitation: {
    label: "NASA · GPCP 3.3",
    href: "https://disc.gsfc.nasa.gov/datasets/GPCPMON_3.3/summary",
    description: "Precipitación mensual de satélites y pluviómetros, exportada mediante Giovanni.",
  },
  rain5: {
    label: "NASA · MERRA-2",
    href: "https://disc.gsfc.nasa.gov/datasets/M2SMNXEDI_2/summary",
    description: "RX5Day mensual de M2SMNXEDI v2, exportado mediante Giovanni.",
  },
  "rain5-power-annual": {
    label: "NASA POWER diario",
    href: "https://power.larc.nasa.gov/docs/services/api/temporal/daily/",
    description: "Datos diarios de POWER con los que el equipo calcula el índice Rx5day anual; no es el índice mensual de Giovanni.",
  },
};

export function getSourceLinks(variableId: VariableId): SourceLink[] {
  const primary = sources[variableId];
  if (!primary) return [];
  return variableId === "rain5-power-annual" ? [primary] : [primary, nino34];
}
