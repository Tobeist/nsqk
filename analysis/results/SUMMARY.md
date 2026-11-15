# Resumen del análisis de tendencias

Generado por `scripts/trend_audit.py`. Reglas y definiciones: `docs/ANALISIS_TENDENCIAS_PLAN.md`. Cifras: pendiente por década [IC 95 % individual].

| Variable | M0 base (F1) | p original / Holm | M1 con Niño 3.4 (F2) | p original / Holm | Bootstrap bloque 12 | Clase |
| --- | --- | --- | --- | --- | --- | --- |
| Temperatura media a 2 m (NASA POWER, MERRA-2) (°C) | +0.271 [+0.0607, +0.48] | 0.0115 / 0.0345 | +0.267 [+0.0531, +0.481] | 0.0144 / 0.0433 | +0.271 [+0.0541, +0.495] | B |
| Precipitación media (GPCP satélite + pluviómetros, Giovanni) (mm/día) | +0.0985 [-0.0258, +0.223] | 0.121 / 0.241 | +0.101 [-0.0164, +0.218] | 0.0917 / 0.183 | +0.0985 [-0.0343, +0.229] | C |
| RX5Day mensual (MERRA-2, Giovanni) (mm/5 días) | +0.778 [-2.58, +4.14] | 0.65 / 0.65 | +0.855 [-2.43, +4.14] | 0.61 / 0.61 | +0.778 [-2.81, +4.16] | C |

Clases: **A** = Evidencia consistente de tendencia dentro de los análisis realizados; **B** = Resultado sensible al periodo, al modelo o a los controles; **C** = Evidencia insuficiente; **D** = Datos o supuestos que impiden una conclusión confiable.

La pendiente mensual coincide con la pendiente de MCO de los promedios anuales (diferencia máxima 4.2e-15); los intervalos difieren porque usan 396 meses con HAC frente a 33 promedios.

Cobertura espacial de la caja solicitada: Texas 3.2%, Coahuila 12.0%, Tamaulipas 6.9%, Nuevo León 77.9%. Huella de las celdas MERRA-2: Texas 4.0%; GPCP: Texas 3.2%.

Los p de Holm de esta tabla usan la aproximación normal del HAC; los p válidos por bootstrap-t con criba AR, que reemplazan a la calibración retirada de la versión anterior, están en `uncertainty_validation.csv`.

Informes: [t2m](informe_t2m.md), [gpcp](informe_gpcp.md), [rx5d](informe_rx5d.md).
