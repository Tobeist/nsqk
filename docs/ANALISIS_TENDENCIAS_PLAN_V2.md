# Plan v2: agrupaciones, extremos, predicción y simulaciones (definido antes de ejecutar)

Amplía [el plan v1](ANALISIS_TENDENCIAS_PLAN.md), cuyas definiciones (modelos M0/M1, HAC, bootstrap, ventanas W0–W3, familias F1/F2, reglas A–D) se mantienen sin cambios. Los scripts guardan el SHA-256 de este archivo en `analysis/results/run_info_v2.json`.

**Divulgación.** Antes de escribir este plan ya se conocían todos los resultados del plan v1, incluida la calibración por simulación, y la tendencia del RX5Day anual derivado de POWER que publica el repositorio (+15.96 mm/década). No se había ejecutado ningún análisis con datos diarios de temperatura, ninguna agregación por bloques, ningún modelo predictivo ni las simulaciones de esta versión.

**Método principal (por indicación del equipo, no por resultados):** regresión mensual MCO con efectos de mes y Niño 3.4 contemporáneo (M1, L = 0), comparada con la regresión actual sin ENSO (M0), con HAC(12), bootstrap por bloques y diagnósticos. Las cifras son las del plan v1.

## 1. Preguntas y resolución

| Pregunta | Qué se mide | Datos | Resolución analizada |
| --- | --- | --- | --- |
| A. Cambio de la media | pendiente por década de la media de T2M (°C) y de la tasa de precipitación (mm/día) | mensual: POWER T2M, GPCP, RX5Day mensual (plan v1); diaria: POWER T2M y PRECTOTCORR | mensual (principal); bloques diarios solo como estudio de agregación |
| B. Cambio de extremos | índices anuales ETCCDI calculados con datos diarios reales | POWER diario T2M_MAX y PRECTOTCORR (UTC) | diaria → anual |
| C. Calendario y ENSO | varianza mensual asociada a calendario, tendencia y Niño 3.4 | mensual | mensual |
| D. Predicción | error fuera de muestra a 1–12 meses | mensual | mensual |

La resolución del dato (mensual o diaria), la frecuencia de publicación de los productos, su retraso de disponibilidad y la agrupación elegida son cosas distintas. Con datos mensuales no se estudian ventanas de pocos días; no se generan datos diarios por interpolación. Las preguntas A–D se reportan por separado; no se declara un ganador universal entre escalas.

## 2. Estudio de agrupaciones (pregunta A con datos diarios)

**Fuente única** para que las diferencias no procedan de cambiar de producto: POWER diario (MERRA-2), T2M (`scripts/power_daily_temperature.py`, nueva descarga en `data/external/power_daily_t2m/`) y PRECTOTCORR (`data/raw/power_daily_prectotcorr/`, sin modificar). Hora: días UTC, como la descarga de lluvia ya existente. Región: media de los 15 centros de celda con peso cos(lat), igual que el repositorio.

**Lista cerrada de agrupaciones:** 1, 3, 7 y 14 días en bloques **no solapados**; mes calendario; estación meteorológica; año calendario. No se usan medias móviles para la inferencia.

- Anclaje: los bloques de 1–14 días empiezan el 1 de enero de cada año y se reinician cada año; el último bloque de cada año es más corto (por ejemplo, 1 o 2 días en bloques de 7 en años normales o bisiestos).
- Bisiestos: el 29 de febrero se conserva como un día más; el día del año se expresa como fracción del año (día − 0.5)/longitud del año.
- Estaciones: DJF se asigna al año de enero y febrero; el DJF de 1992 queda incompleto (falta diciembre de 1991) y se excluye. MAM, JJA y SON completas.
- Cobertura mínima: todo bloque requiere el 100 % de los días válidos. El valor de relleno −999 se excluye (nunca se convierte en cero). Si apareciera un faltante, el bloque se excluye y se informa.
- Cantidad: media de T2M (°C) y media de la tasa PRECTOTCORR (mm/día). La precipitación acumulada de un bloque sería tasa × días; para la pendiente de la media se usa la tasa.

**Identidad que se comprueba en todos los años y agrupaciones:** media anual = Σ(n_días_bloque · media_bloque)/Σ n_días_bloque = Σ valores_diarios/N. Agrupar en 3 o 7 días antes de una media anual bien ponderada no cambia la media anual y no es una mejora de detección.

**Modelo para cada agrupación (mismo objetivo: tendencia de la media):** MCO con `t` = punto medio del bloque en años reales; calendario con tres armónicos del día del año para bloques de 1–14 días, efectos de mes para el mensual, de estación para el estacional y ninguno para el anual. HAC de Bartlett con rezagos equivalentes a un año: 365, 122, 52, 26, 12, 4 y 1 observaciones. Se comparan pendientes, errores estándar e intervalos. La agrupación **no se elige por p**: para A se mantiene la mensual porque es la resolución común a los tres productos y al índice ENSO.

**Coherencia de producto:** media mensual de los datos diarios POWER (UTC) frente a la serie mensual POWER (que declara LST); se informa la diferencia máxima.

## 3. Extremos (pregunta B)

Índices anuales con definiciones del ETCCDI (Zhang et al., 2011, *WIREs Climate Change*; lista de 27 índices de expertdb ETCCDI), calculados sobre datos diarios reales:

- **TX90p:** porcentaje de días del año con T2M_MAX regional por encima del percentil 90 del día del calendario, estimado en 1992–2021 con una ventana centrada de 5 días. Simplificación declarada: en años de la referencia el umbral se calcula dejando fuera ese año (en lugar del bootstrap de Zhang et al., 2005); en 2022–2024 se usan los 30 años.
- **CDD:** máxima racha de días consecutivos con precipitación < 1 mm (media regional) dentro del año calendario; las rachas no cruzan el 31 de diciembre.
- **Rx5day anual:** definición del repositorio (máximo anual por celda de cinco días consecutivos, después media ponderada); se recalcula y se coteja con `data/processed/power_rx5day_annual_region_1992_2024.csv`.

Distinciones: un día de TX90p es un día habitualmente cálido para su fecha, no un récord local ni mundial. Los índices usan reanálisis en malla, no estaciones. No se eliminan años con huracanes u olas de calor.

Tendencia: MCO anual sobre el año; IC por bootstrap circular de residuos en bloques de 3 años (semilla 20261114, B = 5000); Theil–Sen con el mismo bootstrap como sensibilidad. **Familia B** (TX90p, CDD, Rx5day): Holm, m = 3. No se reconstruye un extremo anual promediando índices mensuales.

## 4. Calendario y ENSO (pregunta C)

R² secuencial mensual de cada variable: solo calendario; calendario + tendencia; calendario + tendencia + Niño 3.4 (L = 0); y el modelo con ENSO por estación. Es una descripción dentro de la muestra, no inferencia. Las figuras muestran el ciclo estacional (climatología 1992–2021 con dispersión por mes) y las anomalías junto con Niño 3.4.

## 5. Experimento predictivo (pregunta D)

**Objetivo único:** valor mensual de cada una de las tres variables, en sus unidades, horizonte de 1 a 12 meses. Cada pronóstico se emite en diciembre para el año calendario siguiente.

**Particiones:**
- **Periodo final reservado:** 2021–2024. No interviene en ninguna selección. Se evalúa una sola vez al final: los hiperparámetros se eligen con datos hasta 2020; cada año del periodo reservado se pronostica reajustando los modelos con los datos hasta el diciembre anterior, sin reoptimizar. Como el equipo ya vio gráficas de todo el periodo, esto no es una validación ciega.
- **Particiones externas:** años de prueba 2016, 2017, 2018, 2019 y 2020; entrenamiento con todo lo anterior (ventana creciente desde 1992).
- **Particiones internas (solo Optuna):** dentro de cada entrenamiento externo, los tres últimos años de ese entrenamiento como pruebas de 12 meses con ventanas crecientes. Ningún dato de una prueba externa elige parámetros.
- Climatologías, coeficientes y cualquier escalado se estiman solo dentro de cada entrenamiento. No hay imputación (no hay faltantes).

**Modelos:**
1. `CLIM`: media de cada mes del calendario en el entrenamiento.
2. `PERSIST`: el mismo mes del año anterior.
3. `OLS_TREND`: tendencia + efectos de mes.
4. `OLS_ENSO_OPER`: OLS_TREND + Niño 3.4 de diciembre del año anterior (conocido al emitir; en entrenamiento se construye igual).
5. `OLS_ENSO_RECON`: OLS_TREND + Niño 3.4 contemporáneo observado. **Reconstrucción condicionada**: usa ENSO futuro y no es un pronóstico operativo.
6. `PROPHET`: tendencia lineal por tramos, estacionalidad anual de Fourier, sin estacionalidad semanal ni diaria, aditiva, intervalo del 80 %.
7. `PROPHET_ENSO_OPER` y 8. `PROPHET_ENSO_RECON`: con el mismo regresor de Niño 3.4 que 4 y 5.

**Optuna (TPE, `seed = 20261114`, 25 ensayos por partición externa y por modelo Prophet):** `changepoint_prior_scale` log-uniforme en [0.001, 0.5]; `seasonality_prior_scale` log-uniforme en [0.01, 10]; `yearly_fourier_order` entero en [2, 6] (6 es el máximo identificable con 12 meses). Fijos: `changepoint_range = 0.8`, 25 puntos de cambio, `interval_width = 0.8`, `mcmc_samples = 0`, prior del regresor ENSO = 10. **Criterio:** MAE medio en las particiones internas. Nunca p ni pendiente. Se registran todos los ensayos.

**Métricas:** MAE (principal), RMSE, habilidad MAE frente a CLIM (1 − MAE/MAE_CLIM), cobertura empírica del intervalo del 80 % (Prophet; OLS con su intervalo de predicción clásico al 80 %, que supone errores independientes). Los intervalos de Prophet no son intervalos de confianza de la pendiente.

**Regla de mejora consistente:** un modelo mejora a otro si su MAE medio externo es menor, si es menor en al menos 4 de las 5 particiones externas y si es menor también en el periodo reservado. Si ningún modelo complejo cumple la regla frente a CLIM y OLS_TREND, se recomienda el más simple. Los modelos de reconstrucción se comparan solo entre sí.

**Red neuronal (puerta preespecificada):** solo se probaría una red pequeña si algún Prophet cumpliera la regla de mejora consistente frente a OLS. Con unas 300 observaciones mensuales de entrenamiento, sin esa evidencia no se justifica.

**Simplex:** no se usa. Las agrupaciones son una lista discreta pequeña (comparación explícita); los hiperparámetros de Prophet son mixtos (TPE); MCO tiene solución cerrada. No hay un problema lineal con restricciones (programación lineal) ni un objetivo continuo sin derivadas que justifique Nelder–Mead.

## 6. Simulaciones (series sintéticas, no NASA)

396 meses, ciclo estacional de amplitud 8 (unidades arbitrarias), ruido AR(1) con φ = 0.37 y desviación 1, y un índice tipo ENSO AR(1) con φ = 0.93 y efecto γ = −0.2. 1000 réplicas por escenario, semilla fija.

| Escenario | Verdad |
| --- | --- |
| S0 | sin tendencia |
| S1 | tendencia de 0.27 por década |
| S2 | sin tendencia, oscilación de 20 años y amplitud 0.4 |
| S3 | sin tendencia, escalón de +0.5 en 2008 |

Procedimientos evaluados: M0 y M1 con HAC(12), HAC(24), bootstrap de bloques de 12 meses (199 réplicas) y Theil–Sen estacional (solo la estimación puntual y su sesgo). Medidas: tasa de rechazo (falso positivo en S0, potencia en S1), sesgo y cobertura del IC del 95 % (S1). En S2 y S3 se informa con qué frecuencia una tendencia lineal se declara "significativa" aunque no exista una tendencia lineal.

**Selección dentro de la simulación:** (i) el procedimiento de "elegir entre W0–W3 la ventana con menor p", que ilustra la inflación por buscar; (ii) el criterio predictivo CLIM frente a OLS_TREND con las mismas particiones externas (2016–2020), para ver cuántas veces se prefiere la tendencia sin y con tendencia verdadera. El ajuste de Prophet con Optuna no se repite en las simulaciones por su coste (≈ 10⁵ ajustes); queda como limitación declarada.

## 7. Clasificación final

Para cada resultado: **evidencia consistente** dentro de las pruebas realizadas, **sensible a decisiones**, **inconcluso** o **no evaluable** por calidad o cobertura. Para A se usan las reglas A–D del plan v1. Para B, "consistente" exige p de Holm < 0.05 en la familia B, IC bootstrap sin cero y el mismo signo en Theil–Sen; "sensible" si solo se cumple parte; "inconcluso" si p de Holm ≥ 0.05. Para D se usa la regla de mejora consistente.

## 8. Adiciones posteriores a la primera ejecución

- **La puerta de la red neuronal se activó.** En la primera ejecución del experimento predictivo, `PROPHET_ENSO_OPER` cumplió la regla de mejora consistente frente a `OLS_TREND` para `rx5d`. Antes de ejecutar la red se fijó su especificación: perceptrón de una capa oculta (`tanh`, `lbfgs`, `random_state = 20261114`). Entradas: tiempo, Niño 3.4 de diciembre anterior y 12 indicadores de mes, estandarizados con el entrenamiento. Optuna busca `hidden_units` ∈ {2, 4, 8} y `alpha` log-uniforme en [0.001, 10], con las mismas particiones, ensayos, semilla y criterio. Se aplica solo a las variables que activaron la puerta.
- **Sesgo medio (pronóstico − observación)** añadido a las métricas por partición, para interpretar el periodo reservado.
- **Referencia adicional:** `consistent_vs_ols_enso_oper`, que compara cada modelo operativo con ENSO contra la OLS que usa la misma información.
