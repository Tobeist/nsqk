# Plan de análisis de tendencias (definido antes de ejecutar las comparaciones)

Este documento fija modelos, rezagos, ventanas, pruebas y criterios **antes** de ejecutar `scripts/trend_audit.py`. El script guarda el SHA-256 de este archivo en `analysis/results/run_info.json`; un cambio posterior al plan se detecta comparando ese hash.

**Divulgación de lo ya visto.** Antes de escribir este plan se conocían los resultados del modelo base de la app para 1992–2024 (`data/results/*.json`) y, por una revisión previa de la sesión, las pendientes de la app en 1992–2008, 2000–2024 y 2010–2024. Las ventanas de la sección 4 se eligieron por duración y reparto del periodo, no por esos resultados, pero no puede afirmarse que no hubiera influencia. No se había calculado ningún modelo con ENSO, bootstrap, diagnóstico de residuos ni prueba de rupturas.

## 1. Datos

Periodo principal: enero de 1992 a diciembre de 2024 (396 meses, 33 años). Tres variables, la caja `[-101, 25, -99, 27]`:

| Id | Variable | Producto | Unidad | Definición |
| --- | --- | --- | --- | --- |
| `t2m` | Temperatura media a 2 m | NASA POWER (MERRA-2), 15 celdas 0.5°×0.625° | °C | media mensual, media espacial con peso cos(lat) |
| `gpcp` | Precipitación media | GPCP v3.3 satélite + pluviómetros (Giovanni), 16 celdas 0.5° | mm/día | **tasa media diaria** del mes (no acumulado mensual) |
| `rx5d` | RX5Day mensual | MERRA-2 `M2SMNXEDI` (Giovanni), 15 celdas | mm por 5 días | máximo mensual de lluvia en cinco días, media espacial de los máximos de celda |

Observaciones: GPCP combina observaciones; T2M y RX5Day son de reanálisis (modelo + asimilación) y **no son observaciones directas**; T2M (POWER) y RX5Day (Giovanni) provienen ambos de MERRA-2, de modo que no son comprobaciones independientes entre sí. Series suplementarias (solo comprobación de coherencia, fuera de la familia de pruebas): `PRECTOTCORR` de POWER (también MERRA-2, con corrección con pluviómetros) frente a GPCP.

ENSO: Niño 3.4 mensual, columna `NINO3.4 ANOM` de NOAA CPC (ERSSTv5, anomalía respecto a 1991–2020 fijo), descargado con `scripts/fetch_enso.py`. Se usan 1991-01 a 2024-12 (meses previos para rezagos de hasta 12 meses). No se usa ONI (media móvil de tres meses de la misma señal) en el mismo modelo.

## 2. Modelo base (M0)

`y_t = α + β·t + Σ_{m=2..12} δ_m·I(mes_t = m) + ε_t`, con `t` = (índice mensual)/12 en años. Se estima por MCO con covarianza HAC de Newey–West (peso de Bartlett).

- Pendiente por década = 10·β.
- Intervalo de confianza del 95 % = 10·[β ± q·SE_HAC(β)], con **q = 1.959964** (normal). Justificación: el estimador HAC es asintóticamente normal; coincide con `statsmodels` (`use_t=False`) y con `lib/seasonal-trend.ts`. Como comprobación de muestra finita se reporta también la variante con la t de Student (n − k gl) y el bootstrap por bloques. Con rezago 12 y n = 396 la razón ancho de banda/n es ≈ 0.03, y con 24 es ≈ 0.06: la aproximación normal puede subestimar algo la incertidumbre (no se implementa el cuantil de ancho de banda fijo de Kiefer–Vogelsang; queda como limitación).
- Rezago HAC principal: **12** (un ciclo estacional). Sensibilidad: 6 y 24, sin elegir entre ellos. La regla de Newey–West (≈ 5 meses) se menciona como referencia, no se usa.
- Anomalías (solo para gráficas): climatología mensual fija 1992–2021.
- Con años completos y datos equilibrados, la pendiente del modelo mensual es **idéntica** a la pendiente de MCO de los promedios anuales de doce meses sobre el año; la gráfica anual y el modelo describen el mismo estimador puntual. Las diferencias aparecen solo en el intervalo (HAC mensual frente a una regresión de 33 puntos). Se verifica numéricamente.

## 3. Modelos con ENSO

- **M1 (ENSO principal, L = 0):** M0 más `γ·N34_t`. Se declara contemporáneo para las tres variables: la respuesta regional a ENSO se concentra en la estación fría y el rezago físico no es suficientemente preciso para fijar uno por variable.
- **Rezagos exploratorios fijados de antemano:** L = 3 y L = 6, cada uno como modelo separado (no se mezclan rezagos). L = 3 se motiva por la literatura general de respuesta térmica global a ENSO (retraso de unos tres meses, p. ej. Trenberth et al., 2002); esa referencia **no se verificó en esta sesión**. Con datos desde 1991 los 396 meses se conservan para cualquier L ≤ 12, así que todos los modelos usan exactamente las mismas fechas.
- **Exploratorio de estacionalidad:** M1S, con un coeficiente de ENSO por estación (DJF, MAM, JJA, SON), L = 0. Se reporta una prueba de Wald conjunta de igualdad de los cuatro coeficientes.
- Se revisa colinealidad con el tiempo (correlación y VIF de `t` y `N34`). No se incluye PDO ni otro índice.
- Se comparan β (M0) y β_E (M1): estimaciones, intervalos y el cambio relativo del error estándar. Una pendiente ajustada por ENSO es una asociación condicionada a ese modelo: no es atribución causal ni elimina otras fuentes de variabilidad.
- Serie "ajustada por ENSO" para gráficas: `y_t − γ̂·N34_t`; se rotula como construida, no observada.

## 4. Ventanas (exploratorias, solo estas)

| Id | Periodo | Años |
| --- | --- | ---: |
| W0 | 1992–2024 (principal) | 33 |
| W1 | 1992–2010 | 19 |
| W2 | 2006–2024 | 19 |
| W3 | 2000–2024 | 25 |

Además, de forma **solo descriptiva** (sin pruebas) se muestran las pendientes de ventanas móviles de 10 y 15 años para ilustrar cuánto varían frente al intervalo del periodo completo. En ENSO, cada ventana usa las mismas fechas con y sin ENSO. No se agregan ventanas tras ver resultados.

## 5. Robustez

1. **Residuos:** Ljung–Box (rezagos 12 y 24) y ACF; Breusch–Pagan; varianza por mes (Levene); asimetría/curtosis (Jarque–Bera); distancia de Cook (conteo > 4/n, máximo y fecha); DFBETA estandarizado de β con exclusión de un año completo (**diagnóstico, no filtro**: se reporta el rango completo y se conserva el resultado con todos los años).
2. **Linealidad y rupturas:** término cuadrático centrado (Wald HAC); cambio de nivel y pendiente (Wald HAC) en tres fechas fijadas: 2001-01 y 2011-01 (límites de las corrientes de producción de MERRA-2, según recuerdo de la documentación del GES DISC, **no verificado en esta sesión**) y 2008-01 (punto medio); Holm sobre las tres fechas por variable; CUSUM de residuos de MCO.
3. **Incertidumbre alternativa:** HAC con 6, 12 y 24 rezagos (dos variantes de q) y **bootstrap por bloques circulares de residuos**, con semilla `20261114` y B = 5000. Los bloques empiezan siempre en enero y su longitud es múltiplo de 12 meses para preservar la fase estacional y la dependencia local; así no se mezclan meses al azar. Longitud principal **12** (n^{1/3} ≈ 7 meses sugiere dependencia corta, y 12 es el menor múltiplo estacional); sensibilidad 24 y 36 para dependencia entre años. Se reporta SE bootstrap, intervalo percentil y p centrado (distribución de β* − β̂).
4. **No paramétrico:** pendiente de Theil–Sen estacional (mediana de las pendientes entre años dentro de cada mes, con las 12 estaciones agrupadas) con intervalo bootstrap por bloques de años de longitud 2 (semilla y B iguales). No se reporta una prueba de Mann–Kendall con varianza para observaciones independientes, porque los supuestos de independencia no se cumplen; esto es una comprobación de sensibilidad a valores atípicos y no una validación independiente (comparte el mismo bootstrap).
5. **Escala:** para `gpcp` y `rx5d`, que son positivas y asimétricas, se repite M0 sobre `100·y/clim_m − 100` (porcentaje respecto a la media mensual 1992–2021) como sensibilidad a la escala.
6. **Productos:** correlación de anomalías mensuales de GPCP y PRECTOTCORR como comprobación de coherencia; no se tratan como validaciones independientes.

## 6. Familias de pruebas y corrección

- **Familia principal F1:** β de M0, W0, HAC(12), tres variables; corrección de **Holm** con m = 3.
- **Familia secundaria F2:** β_E de M1 (L = 0), W0, HAC(12), tres variables; Holm con m = 3.
- Todo lo demás (otros rezagos, ventanas, HAC alternativos, bootstrap, escala, rupturas) es **exploratorio**: p sin ajustar, etiquetado así.
- Los intervalos de 95 % son **individuales**. Para F1 se añade además el intervalo simultáneo de Bonferroni (nivel 1 − 0.05/3).
- p no es la probabilidad de que la tendencia sea real. Un intervalo que contiene cero indica evidencia insuficiente bajo ese análisis, no ausencia de cambio.

## 7. Reglas de interpretación (aplicadas mecánicamente)

Para cada variable:

- **D – Datos o supuestos impiden una conclusión confiable:** hay ruptura en alguna de las tres fechas (p de Holm < 0.01 en el Wald de nivel+pendiente) **o** la razón SE bootstrap(ℓ = 12)/SE HAC(12) está fuera de [0.67, 1.5].
- **A – Evidencia consistente dentro de los análisis realizados:** no es D; p de Holm < 0.05 en F1 y en F2; el intervalo de M1 (L = 0) excluye cero; el intervalo bootstrap (ℓ = 12) excluye cero; los tres HAC (6, 12, 24) excluyen cero; y el signo de β coincide en W1, W2 y W3.
- **B – Resultado sensible al periodo o a los controles:** no es D; p de Holm < 0.05 en F1 o F2 pero no se cumple alguna condición de A.
- **C – Evidencia insuficiente:** no es D, y ninguna de F1 ni F2 tiene p de Holm < 0.05.

Estas etiquetas resumen el cumplimiento de criterios fijados de antemano; no equivalen a una conclusión física ni a atribución a cambio climático antropogénico, que requeriría un análisis de detección y atribución.

## 8. Entregables y reproducción

`python scripts/trend_audit.py` genera `analysis/results/` (tablas CSV/JSON, `run_info.json`, informes por variable) y `analysis/figures/`. La ENSO se descarga con `python scripts/fetch_enso.py`. Los archivos originales de `data/raw/` no se modifican.

## 9. Adiciones posteriores a la primera ejecución

El SHA-256 de este plan en la primera ejecución completa fue `ac06ea78e1f82f64bbbf046daae5a536ff3436e3b20ae365bbf15ecbccfd655c`; las secciones 1–8 no cambiaron desde entonces. Tras ver los resultados se añadió lo siguiente, que **no estaba en el plan inicial** y se marca como exploratorio:

- **Simulación de tamaño** (`coverage_simulation.json`): 1000 series sin tendencia de 396 meses con ruido AR(1) (φ = 0 y φ = 0.37; el segundo valor se tomó de la autocorrelación de lag 1 de los residuos de T2M observada en la primera ejecución). Se mide con qué frecuencia el intervalo del 95 % excluye cero. Es un diagnóstico del método, no usa los valores de tendencia de los datos.
- **Calibración exploratoria** (`size_calibration_exploratory.json`): se ensancha el error estándar HAC12 por el factor que restablece el 5 % nominal en la simulación con el φ más cercano a la autocorrelación residual de cada serie, y se recalcula p y Holm. No modifica la clasificación de la sección 7, que se aplica con los criterios originales.

**Retirado (plan v3):** la "calibración exploratoria" de esta sección no producía valores p válidos para Holm. Se reemplazó por el bootstrap-t con criba AR de [`ANALISIS_TENDENCIAS_PLAN_V3.md`](ANALISIS_TENDENCIAS_PLAN_V3.md). Se eliminó `size_calibration_exploratory.json`.
