# Informe metodológico: tendencias, agrupaciones, ENSO y predicción

Reproducción: `python scripts/run_analysis.py` (≈ 5 min; semilla 20261114). Planes previos a cada ejecución: [v1](ANALISIS_TENDENCIAS_PLAN.md), [v2](ANALISIS_TENDENCIAS_PLAN_V2.md) y [v3](ANALISIS_TENDENCIAS_PLAN_V3.md); lo añadido o retirado después de ver resultados está marcado en cada uno. Tablas y figuras: [`analysis/`](../analysis/README.md). Caja `[-101, 25, -99, 27]`: 78 % Nuevo León, 12 % Coahuila, 7 % Tamaulipas y 3 % Texas (4 % de la huella de las celdas MERRA-2); no es una medición completa de ningún estado.

**Salida única:** la tabla de la sección 1 coincide con `analysis/results/final_status.csv` y `SUMMARY.md`, que genera `scripts/final_summary.py`; todos los p de Holm proceden del bootstrap-t con criba AR.

**Método que se conserva:** regresión mensual MCO con efectos de mes y Niño 3.4 contemporáneo (M1), mostrada junto al modelo actual sin ENSO (M0). La pendiente es HAC(12); los **valores p e intervalos válidos** salen del bootstrap-t con criba autorregresiva (sección 2). No se añaden modelos.

## 1. Tabla final

| Resultado | Cifras | Estado |
| --- | --- | --- |
| El calendario domina la varianza mensual | R² del calendario: T2M 0.94, GPCP 0.39, RX5Day 0.25 | **Sustentado** |
| ENSO casi no cambia las pendientes y su efecto depende de la estación | T2M: 0.2706 → 0.2673 °C/década; corr(t, Niño 3.4) = −0.02. Añadir ENSO con coeficientes por estación sobre calendario + tendencia suma **6.6 puntos** de la varianza de las anomalías de T2M (el 10.2 % total incluye 3.5 de la tendencia), 5.2 en GPCP y 5.4 en RX5Day | **Sustentado** (asociación, no causa) |
| Agrupar en bloques no cambia la tendencia de la media | WLS por días: 0.27287–0.27296 °C/década en bloques de 1–14 días; mismo producto y días | **Sustentado** |
| Lluvia diaria y mensual de POWER coinciden con el mismo estándar horario | mensual API frente a diario LST: ≤ 0.0023 mm/día | **Sustentado** |
| Los IC HAC nominales del 95 % son estrechos | cobertura real 90–93 % según la variable | **Sustentado** bajo el modelo AR estimado |
| Precipitación media (GPCP), RX5Day mensual, TX90p y CDD | p de Holm (bootstrap-t) 0.25–0.74; IC con cero | **Sustentado que no hay evidencia suficiente** (no implica ausencia de cambio) |
| Temperatura +0.27 °C/década | M1: IC bootstrap-t individual [+0.011, +0.523]; p = 0.044; **Holm 0.13** (M0: 0.033, Holm 0.098) | **Inconcluso** por las reglas fijadas (clase C): la estimación es positiva y su IC individual excluye cero, pero no supera Holm al 5 %; además 1992–2010 da −0.06 y un escalón en 2011 ajusta igual que la recta. Comunicable como "aumento estimado, no concluyente" |
| Rx5day anual (POWER diario) +16.0 mm/década | IC bootstrap-t [+5.1, +26.8]; Holm 0.020; igual con LST | **Pendiente**: un escalón en 2001-01, inicio de la corriente 300 de MERRA-2, explica los datos igual o mejor (+39 mm) |
| Mejora predictiva de Prophet con ENSO operativo en RX5Day | 4.0 % (particiones externas) y 5.7 % (periodo reservado, solo informado) frente a la climatología | **Pendiente / no se adopta**: pequeña y 1 de unas 20 comparaciones |
| Prophet y red neuronal | sin mejora consistente en T2M ni GPCP; la red (activada por la puerta, que decide solo con 2016–2020) empeora un 25 % | **Sustentado que no se justifican** |

## 2. Intervalos y valores p

**Qué estaba mal.** La simulación anterior usaba un AR(1) con φ = 0.37 fijo, tomado de los residuos de T2M sin ENSO, y no se estimaba para cada variable. La "p de Holm 0.09" se había obtenido ensanchando el error estándar; no era un valor p válido para Holm y **se retiró**.

**Qué se hizo** (`uncertainty_validation.py`, B = 4999):
1. Se ajusta el modelo nulo sin tendencia (calendario o calendario + Niño 3.4) y se estima un AR(p) en sus residuos, con p elegido por AIC: 2 en T2M, 0 en GPCP y 1 en RX5Day.
2. Las innovaciones se escalan por mes, se remuestrean y se generan series nulas.
3. En cada serie se recalcula el mismo t = β̂/SE_HAC12.
4. Con esa distribución se obtienen el p (fracción de |t*| ≥ |t|), el IC bootstrap-t y la cobertura real del IC nominal. Holm se aplica a esos p.

| Serie | p normal | p bootstrap | Holm | IC bootstrap-t | Cobertura real del IC HAC 95 % |
| --- | ---: | ---: | ---: | --- | ---: |
| T2M M0 | 0.012 | 0.033 | 0.098 | [+0.024, +0.517] | 90.7 % |
| T2M M1 | 0.014 | 0.044 | 0.132 | [+0.011, +0.523] | 90.0 % |
| GPCP M1 | 0.092 | 0.123 | 0.246 | [−0.032, +0.234] | 92.2 % |
| RX5Day M1 | 0.610 | 0.633 | 0.633 | [−2.83, +4.54] | 91.7 % |
| Rx5day anual | 0.0002 | 0.0066 | 0.020 | [+5.1, +26.8] | 88.3 % |
| TX90p anual | 0.189 | 0.273 | 0.547 | [−1.4, +4.5] | 88.3 % |
| CDD anual | 0.687 | 0.742 | 0.742 | [−9.5, +6.9] | 89.3 % |

Los resultados se mantienen con AR(1), innovaciones gaussianas y sin escalado mensual (`uncertainty_validation.csv`). Supuestos: errores lineales estacionarios tras el escalado y regresores fijos. No cubre rupturas: eso se trata en la sección 4.

## 3. Lluvia diaria y mensual

Las comparaciones usan el mismo producto (PRECTOTCORR), las mismas 15 celdas (verificadas), pesos cos(lat), unidades en mm/día y la media de los días del mes (`rain_reconciliation.json`):
- **Mensual de la API frente a diario LST** (mismo estándar horario): diferencia máxima regional de 0.0023 mm/día y de 0.005 por celda, que es redondeo.
- **Diario UTC frente a LST:** la diferencia máxima de 1.25 mm/día aparece en junio de 2010, con −1.21 en julio de 2010; le siguen noviembre y diciembre de 2009 (±0.5). Los signos opuestos en meses contiguos indican lluvia que cambia de mes según el estándar horario (finales de junio de 2010, huracán Alex). En un mismo día, la diferencia regional llega a 36 mm.
- El Rx5day anual con LST da +15.93 mm/década frente a +15.96 con UTC (diferencia anual máxima 3.6 mm).

Rx5day anual (máximo anual por celda) y RX5Day mensual de Giovanni (máximos de cada mes promediados) miden cosas distintas: que uno aumente y el otro no tenga evidencia suficiente no es una contradicción.

## 4. Discontinuidades y forma del cambio

Fechas documentadas en la GMAO Office Note 9 (MERRA-2 File Specification, v1.1, 2016): las corrientes empiezan el 1992-01-01, el 2001-01-01 y el 2011-01-01, cada una inicializada desde MERRA con un año de spin-up. La misma nota indica que PRECTOTCORR es la precipitación basada en observaciones (pluviómetros) que fuerza la superficie terrestre. No se supone que las transiciones causen saltos en esta región.

Comparación con calendario y Niño 3.4 (`form_of_change.csv`; AIC solo descriptivo):

| Serie | Recta sola | Escalón solo | Recta + escalón |
| --- | --- | --- | --- |
| Rx5day anual | +16.0 mm/década | 2001: **+39.1 mm** [26.5, 51.7], ΔAIC −1.7 | 2001: recta +4.6 [−10.2, +19.3], escalón +31.5 [4.7, 58.3] |
| GPCP (no es MERRA-2) | +0.10 mm/día | 2001: **+0.39** [0.18, 0.61], ΔAIC −5.1 | recta −0.10, escalón +0.57 |
| T2M | +0.27 °C/década | 2011: +0.52 [0.08, 0.96], ΔAIC −0.4 | 2001: recta +0.50, escalón −0.64 (p = 0.04), ΔAIC −5.3 |
| TX90p anual | +1.5 % | sin escalón claro | 2001: recta +3.8, escalón −6.3 (p = 0.002) |

Lectura:
- Con 33 años, una recta no distingue un aumento gradual de un cambio de nivel.
- El aumento del Rx5day anual coincide con el inicio de la corriente 300. Sin embargo, GPCP, un producto independiente de MERRA-2, también sube en 2001. Eso sugiere una componente climática, como un final de los años noventa más seco, sin que pueda descartarse un efecto de procesamiento.
- En las simulaciones, un escalón verdadero hizo rechazar H0 ("sin cambio") el 76 % de las veces. **Respecto a H0 eso es un rechazo correcto, no un falso positivo**; lo que falla es la identificación de la forma, porque se atribuye a una tendencia lineal.
- Estas pruebas de escalón son exploratorias (dos fechas por serie, sin corrección).

## 5. Agrupaciones

Pendientes sin redondear con el mismo producto diario de POWER y los mismos días (`grouping_trends.csv`), en °C/década:

| Agrupación | MCO | WLS por días | SE con rezagos de 6 / 12 / 24 meses |
| --- | ---: | ---: | --- |
| 1 día | 0.272957 | 0.272957 | 0.0932 / 0.1053 / 0.1152 |
| 3 días | 0.273315 | 0.272959 | 0.0934 / 0.1055 / 0.1155 |
| 7 días | 0.273994 | 0.272870 | 0.0956 / 0.1073 / 0.1178 |
| 14 días | 0.274972 | 0.272876 | 0.0997 / 0.1108 / 0.1216 |
| Mes | 0.270447 | — | 0.0957 / 0.1070 / 0.1164 |
| Estación | 0.247876 | — | 0.1007 / 0.1086 / 0.1137 |
| Año | 0.272029 | — | 0.1068 / 0.1164 / 0.1114 |

La identidad de las medias anuales ponderadas (verificada a 1e-10) no implica regresiones iguales. En MCO los bloques cortos de fin de año pesan lo mismo que los completos; con pesos por días, los bloques de 1–14 días coinciden con el diario hasta la cuarta cifra. Las diferencias que quedan en mes, estación y año vienen del modelo de calendario (armónicos frente a indicadores) y, en la estación, de excluir el DJF incompleto de 1992. Con duraciones de rezago iguales, los errores estándar son comparables entre agrupaciones. Las de PRECTOTCORR se comportan igual (WLS 0.071603–0.071651 mm/día por década).

## 6. Disponibilidad de ENSO en el pronóstico

| Modelo | Niño 3.4 usado para pronosticar el año Y | ¿Disponible al emitir el pronóstico (inicio de enero de Y)? |
| --- | --- | --- |
| `*_ENSO_OPER` | diciembre de Y−1 | Sí: CPC publica el valor mensual de ERSSTv5 a comienzos del mes siguiente. Pero usamos la versión de agosto de 2026, que puede incluir revisiones posteriores, no la que existía entonces. |
| `*_ENSO_RECON` | enero a diciembre de Y | No: reconstrucción condicionada a conocer ENSO |
| Resto | ninguno | — |

## 7. Lo que no se puede establecer

- Atribución causal.
- Que el cambio de temperatura sea lineal y no un cambio de nivel.
- Que el Rx5day anual sea climático y no un efecto de procesamiento.
- Ausencia de cambio donde el intervalo incluye cero.
- Extremos de pocos días con datos mensuales.
- Representatividad estatal o regional.

**Siguiente comprobación para cerrar lo pendiente:** calcular el Rx5day anual con un producto diario independiente de MERRA-2 (por ejemplo, estaciones GHCN-Daily o CHIRPS) en la misma caja, y ver si aparece el mismo salto en 2001.

## Referencias

- Bosilovich, Lucchesi y Suarez (2016), *MERRA-2: File Specification*, GMAO Office Note 9 v1.1.
- NASA POWER, documentación de la Daily API (parámetro `time-standard`, UTC o LST, LST por defecto).
- NOAA CPC, índices Niño de ERSSTv5 (base 1991–2020).
- Zhang et al. (2011), índices ETCCDI.
