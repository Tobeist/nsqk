# Resumen final

Salida única generada por `scripts/final_summary.py` a partir de las tablas de esta carpeta. Valores p de Holm sobre bootstrap-t con criba AR (plan v3); intervalos bootstrap-t del 95 % individuales. Estados: sustentado, sensible, inconcluso (evidencia insuficiente, no ausencia de cambio), pendiente (pasa las pruebas, pero un escalón en una fecha de cambio de procesamiento documentada lo explica igual) y no evaluable.

| Resultado | Estimación [IC 95 %] | p Holm | Estado | Nota |
| --- | --- | ---: | --- | --- |
| Tendencia mensual: Temperatura media a 2 m (NASA POWER, MERRA-2) | +0.267 [+0.0112, +0.523] °C/década | 0.132 | **inconcluso** | IC individual sin cero; escalón documentado que ajusta igual: 2011-01 (+0.521) |
| Tendencia mensual: Precipitación media (GPCP satélite + pluviómetros, Giovanni) | +0.101 [-0.0316, +0.233] mm/día/década | 0.246 | **inconcluso** | IC individual con cero; escalón documentado que ajusta igual: 2001-01 (+0.395) |
| Tendencia mensual: RX5Day mensual (MERRA-2, Giovanni) | +0.855 [-2.83, +4.54] mm/5 días/década | 0.633 | **inconcluso** | IC individual con cero |
| Extremo anual TX90p (POWER diario) | +1.53 [-1.41, +4.47] % de días/década | 0.547 | **inconcluso** |  |
| Extremo anual CDD (POWER diario) | -1.32 [-9.5, +6.86] días/década | 0.742 | **inconcluso** |  |
| Extremo anual Rx5day (POWER diario) | +16 [+5.09, +26.8] mm/década | 0.0198 | **pendiente** | escalón documentado que ajusta igual: 2001-01 (+39.1); falta un producto diario independiente de MERRA-2 |
| Predicción mensual a 12 meses: t2m | — | — | **sustentado** | ningún modelo complejo mejora de forma consistente; se mantiene el más simple |
| Predicción mensual a 12 meses: gpcp | — | — | **sustentado** | ningún modelo complejo mejora de forma consistente; se mantiene el más simple |
| Predicción mensual a 12 meses: rx5d | — | — | **pendiente** | mejora pequeña de PROPHET_ENSO_OPER (habilidad +4.0% externa, +5.7% reservado); no se adopta |

Informe metodológico: `docs/INFORME_TENDENCIAS.md`. Informes por variable: [t2m](informe_t2m.md), [gpcp](informe_gpcp.md), [rx5d](informe_rx5d.md).
