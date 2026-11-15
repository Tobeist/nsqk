# Metodología de datos y análisis — Climate Paradox

**Estado:** cuatro variables mensuales y una serie diaria de NASA POWER, más dos series mensuales oficiales exportadas desde Giovanni: GPCP y `RX5Day`, procesadas para tres cajas de estudio en 1992–2024. Este documento describe el método aplicado primero a la caja noreste y distingue los análisis pendientes. No representa todavía un protocolo validado para las nueve variables del producto.

## 1. Pregunta y alcance inicial

Queremos medir cómo cambió la temperatura media mensual en una caja de prueba del noreste de México y establecer un pipeline reproducible que después permita comparar promedios y extremos. La primera caja es **[-101, 25, -99, 27]** (oeste, sur, este, norte). Es un área rectangular de validación técnica; no representa la región Norte-Noreste formada por estados completos. También se [fijaron y procesaron dos cajas adicionales](REGIONES.md) antes de comparar sus tendencias. Sus archivos están en subcarpetas identificadas por región y pueden analizarse en la aplicación.

Usamos enero de 2010 a diciembre de 2012 para verificar extracción y estructura, y enero de 1992 a diciembre de 2024 para el primer análisis histórico. Elegimos el periodo antes de calcular la tendencia. Los tres años de prueba no se usan para inferencia de tendencias.

## 2. Fuente y procedencia

La serie descargada procede de la [API Monthly Regional de NASA POWER](https://power.larc.nasa.gov/docs/services/api/temporal/monthly/), parámetro `T2M`, comunidad `SB`, formato JSON. El encabezado de la respuesta consultada indica fuente `MERRA2`, unidad `C` y 15 puntos de malla en la caja. Según la [documentación de POWER](https://power.larc.nasa.gov/docs/methodology/data/sources_meteorology/), sus parámetros meteorológicos se basan en MERRA-2. **POWER es un producto procesado por su propia plataforma; no asumimos que sus valores coincidan exactamente con los del campo `M2TMNXSLV_5_12_4_T2M` solicitado a Giovanni.**

Inicialmente solicitamos T2M de Giovanni sin sesión Earthdata: el servicio localizó los archivos mensuales, pero el flujo falló y una petición directa por OPeNDAP respondió HTTP 401. Después activamos una sesión Earthdata en el navegador y descargamos GPCP y `RX5Day`; el cotejo de T2M Giovanni–POWER sigue pendiente. No se mezclan fuentes bajo un mismo identificador.

## 3. Extracción y archivos

Ejecutamos `scripts/power_t2m.py` con los años 2010–2012 y 1992–2024. El script consulta la API, verifica que haya datos, unidad `C` y fuente `MERRA2`, y conserva cada respuesta JSON sin modificar en `data/raw/`. Los archivos derivados se guardan por separado:

| Archivo | Contenido |
| --- | --- |
| `data/raw/power_t2m_1992_2024.json` | Respuesta íntegra de la API. |
| `data/processed/power_t2m_grid_1992_2024.csv` | Un valor por mes y punto de malla, con latitud y longitud. |
| `data/processed/power_t2m_region_1992_2024.csv` | Una media espacial por mes y número de celdas válidas. |
| `data/processed/power_t2m_region_1992_2024.metadata.json` | URL de la petición, cobertura, unidades y regla de agregación. |
| `data/results/power_t2m_region_1992_2024.json` | Series, anomalías, promedios anuales y estadísticos de tendencia. |

La respuesta de POWER usa claves `AAAAMM`. También incluye `AAAA13` como resumen anual: se excluye de la serie mensual para evitar contarlo como un decimotercer mes. Las fechas del CSV son el primer día de cada mes como etiqueta del periodo, no una medición instantánea de ese día. POWER reporta `LST` en el encabezado de la respuesta; para esta serie mensual usamos el mes de calendario publicado por la API.

## 4. Validación y limpieza

Comprobamos que los puntos devueltos estén dentro de la caja solicitada, que cada año contenga los doce meses, que no haya fechas repetidas y que los valores utilizados sean finitos. El valor de relleno `-999` o un valor nulo se representa vacío en el CSV de malla y se excluye de la media regional. La serie histórica obtenida contiene **396 meses, 15 celdas válidas por mes y cero faltantes**. No se interpoló ningún dato.

POWER entrega `T2M` en **°C**; no aplicamos conversión. Si más adelante descargamos T2M de Giovanni en Kelvin, convertiremos explícitamente con `°C = K − 273.15` después de verificar sus metadatos. No se convierte una columna basándose únicamente en su rango de valores.

## 5. Agregación espacial

Para cada mes calculamos la media de los centros de celda devueltos por POWER, con peso `cos(latitud)` para aproximar la diferencia de área entre latitudes:

`T_regional = Σ[T_celda × cos(latitud)] / Σ[cos(latitud)]`, usando solo celdas válidas.

Esta regla no recorta parcialmente las celdas que tocan el borde, no usa una máscara de tierra ni polígonos estatales, y tampoco pondera por población o elevación. Es una aproximación apropiada para probar el pipeline en una caja pequeña; las cinco regiones del producto requerirán polígonos y una decisión explícita sobre fracciones de celda y máscara espacial.

## 6. Climatología y descripciones

Definimos como referencia fija **1992–2021** (30 años). Para cada mes del calendario calculamos su media dentro de ese periodo. La anomalía de un mes es su temperatura regional menos la media de ese mismo mes de la referencia. Esta referencia se fijó antes de interpretar resultados y no se cambia buscando mayor significancia.

Los promedios anuales del JSON son medias aritméticas de los doce valores mensuales. Sirven como resumen descriptivo; **no están ponderados por el número de días de cada mes**. La regresión utiliza los 396 valores mensuales, no los 33 promedios anuales.

## 7. Primera estimación de tendencia

El script `scripts/analyze_t2m.py` ajusta una regresión lineal ordinaria con intercepto, tiempo en años desde enero de 1992 y once indicadores de mes (enero como referencia):

`T_t = β₀ + β₁·tiempo_t + Σ(γ_m·indicador_mes_m) + ε_t`.

Reportamos `10 × β₁` en °C por década. Para la incertidumbre usamos la covarianza HAC/Newey–West de `statsmodels` con **12 rezagos mensuales**, un intervalo de confianza bilateral del 95 % y el valor p bilateral del coeficiente de tiempo. El modelo contempla un ciclo estacional fijo y autocorrelación de los residuos hasta el rezago especificado; no modela explícitamente cambios en el ciclo estacional ni relaciones no lineales.

En esta serie POWER, el cálculo produjo **+0.271 °C por década**, **IC 95 % [+0.061, +0.480]** y **p = 0.0115**. Es un resultado exploratorio para esta fuente, caja y ventana temporal. El valor p aún no tiene corrección por múltiples pruebas. La significancia estadística no demuestra causalidad ni atribuye el cambio a un mecanismo concreto.

## 8. Reproducibilidad

Desde la raíz del proyecto:

```powershell
python -m pip install -r requirements.txt
python scripts/power_t2m.py
python scripts/power_t2m.py --start 1992 --end 2024
python scripts/analyze_t2m.py data/processed/power_t2m_region_1992_2024.csv data/results/power_t2m_region_1992_2024.json
```

El archivo `*.metadata.json` conserva la URL exacta de la petición. Como POWER puede actualizar datos o procesamiento, una descarga posterior debe compararse con el JSON original versionado antes de sustituir resultados. Los scripts validan estructura y cobertura, pero todavía no generan un informe de diferencias entre versiones.

## 9. Antes de publicar hallazgos comparativos

1. Obtener T2M `M2TMNXSLV_5_12_4_T2M` mediante la sesión Earthdata y comparar unidades, malla, agregación temporal y valores con POWER.
2. Definir las cinco regiones mediante polígonos verificables y una media espacial consistente para cada producto.
3. Descargar y verificar las variables de extremos; registrar unidades, definiciones de índices, periodo base de percentiles, cobertura y valores faltantes. No equiparar noches tropicales (`TR`) con noches cálidas (`TN90p`), ni días secos (`CDD`) con lluvia extrema (`R95P`).
4. Fijar por adelantado periodos y análisis de sensibilidad; revisar residuos, elección de rezagos HAC, años influyentes y posible no linealidad.
5. Decidir y documentar controles de variabilidad natural (por ejemplo, ENSO y PDO) y corrección por pruebas múltiples antes de etiquetar un resultado como robusto.
6. Presentar por separado observación, reanálisis y modelos. Una relación entre variables o una tendencia significativa no establece causalidad.

## 10. Ampliación POWER: temperatura mínima, máxima y precipitación

El mismo endpoint regional permite solicitar **un parámetro por petición**. Descargamos `T2M_MIN`, `T2M_MAX` y `PRECTOTCORR` para la misma caja y periodo 1992–2024, conservando las respuestas originales y generando CSV de malla y región con el mismo promedio espacial. La API devolvió 15 celdas válidas en cada uno de los 396 meses, sin faltantes. Para temperatura reportó unidad `C` y fuentes `MERRA2` y `POWER`; para precipitación reportó `mm/day` y fuente `MERRA2`.

Se analizaron con `scripts/analyze_power.py`, usando la misma climatología 1992–2021 y regresión con indicadores mensuales y HAC de 12 rezagos. Resultados **exploratorios, sin ajuste por pruebas múltiples**:

| Parámetro POWER | Pendiente por década | IC 95 % | p individual |
| --- | ---: | ---: | ---: |
| `T2M_MIN` | +0.360 °C | +0.090 a +0.630 | 0.0090 |
| `T2M_MAX` | +0.241 °C | −0.047 a +0.528 | 0.1010 |
| `PRECTOTCORR` | +0.071 mm/día | −0.040 a +0.183 | 0.2082 |

**Interpretación restringida:** que una pendiente individual cruce el umbral p = 0.05 y otra no lo haga **no demuestra que las dos pendientes sean diferentes**. Haría falta estimar directamente la diferencia con su incertidumbre. Tampoco `T2M_MIN` equivale al índice de noches cálidas `TN90p` ni `T2M_MAX` a los días en ola de calor `HWF`. `PRECTOTCORR` es una tasa media mensual de precipitación corregida de POWER/MERRA-2; no es el producto GPCP satélite + pluviómetros y no representa por sí misma lluvia acumulada mensual. La interpretación precisa de los extremos temporales de POWER debe cotejarse con sus metadatos antes de usarlos como indicadores de eventos.

```powershell
python scripts/power_t2m.py --start 1992 --end 2024 --variable T2M_MIN
python scripts/power_t2m.py --start 1992 --end 2024 --variable T2M_MAX
python scripts/power_t2m.py --start 1992 --end 2024 --variable PRECTOTCORR
python scripts/analyze_power.py data/processed/power_t2m_min_region_1992_2024.csv data/results/power_t2m_min_region_1992_2024.json
python scripts/analyze_power.py data/processed/power_t2m_max_region_1992_2024.csv data/results/power_t2m_max_region_1992_2024.json
python scripts/analyze_power.py data/processed/power_prectotcorr_region_1992_2024.csv data/results/power_prectotcorr_region_1992_2024.json
```

## 11. Primera variable de lluvia extrema calculada a partir de datos diarios

La [API diaria regional de POWER](https://power.larc.nasa.gov/docs/services/api/temporal/daily/) exige peticiones de **366 días o menos**. Descargamos `PRECTOTCORR` en UTC por año de 1992 a 2024, conservando cada JSON original en `data/raw/power_daily_prectotcorr/`. La API reportó mm/día y fuente MERRA2. Verificamos la cobertura de cada día, la misma malla de 15 celdas todos los años, valores finitos y precipitación no negativa; no hubo faltantes.

Para cada celda calculamos la **máxima suma de cinco días consecutivos dentro de cada año calendario**. Una tasa media diaria de 1 mm/día equivale numéricamente a 1 mm acumulado durante ese día; por eso la suma de cinco valores diarios queda en mm. Luego promediamos los máximos anuales de las 15 celdas con pesos `cos(latitud)`. No calculamos el máximo de la lluvia ya promediada sobre la región: sería otra pregunta. Las ventanas de cinco días no cruzan el 31 de diciembre; esto debe recordarse al comparar con índices externos.

La serie anual regional tiene 33 valores. Una regresión anual lineal con covarianza HAC de 3 rezagos produjo **+15.96 mm por década**, IC 95 % **[+8.23, +23.69]**, p individual **0.000052**. Como comprobación exploratoria, al excluir 2010 y 2024 la pendiente fue +12.04 mm por década (p = 0.00264). Estos cálculos todavía requieren sensibilidad a rezagos, periodos, corrección por múltiples pruebas y validación frente al índice oficial de Giovanni antes de presentarse como hallazgo firme. La precipitación media mensual y este máximo anual tienen unidades y definiciones diferentes; sus pendientes no se comparan numéricamente de forma directa.

```powershell
python scripts/power_daily_rain.py
python scripts/analyze_annual.py data/processed/power_rx5day_annual_region_1992_2024.csv data/results/power_rx5day_annual_region_1992_2024.json
```

## 12. Primeras series oficiales de Giovanni: GPCP y RX5Day

Con una sesión Earthdata autenticada en el navegador solicitamos el servicio **Time Series, Area-Averaged** de Giovanni para la misma caja y el periodo 1992–2024. Descargamos CSV originales de `GPCPMON_3_3_sat_gauge_precip` y `M2SMNXEDI_2_RX5Day`, además de pruebas de 2010–2012. Cada archivo histórico contiene 396 valores mensuales, sin faltantes. Conservamos los CSV originales en `data/raw/giovanni/` y generamos copias limpias independientes con `scripts/normalize_giovanni.py`. Este script verifica la columna de variable, fechas completas, caja solicitada y valor de relleno de cada archivo. Giovanni reporta una caja efectiva de datos diferente para GPCP y `RX5Day`; sus agregaciones regionales **no deben suponerse idénticas** entre sí ni a la media espacial calculada para POWER.

Según los títulos de los gráficos de Giovanni, GPCP se expresa en **mm/día** y `RX5Day` en **mm por cinco días**. El CSV original no incluye un campo de unidades legible por máquina, por lo que las unidades se registran en el archivo de metadatos procesado y deben corroborarse con el producto fuente antes de publicar.

Aplicando el mismo modelo mensual estacional con HAC de 12 rezagos, obtuvimos resultados exploratorios para 1992–2024: **GPCP +0.099 mm/día por década** (IC 95 % −0.026 a +0.223; p = 0.121) y **`RX5Day` Giovanni +0.778 mm por cinco días por década** (IC 95 % −2.583 a +4.139; p = 0.650). Ninguno de estos intervalos excluye cero. Eso no prueba ausencia de cambio. Tampoco confirma la hipótesis de lluvia media estable con intensificación de extremos para este índice y caja.

La discrepancia con el índice anual derivado de POWER es material: además de usar productos distintos, Giovanni entrega **máximos mensuales promediados regionalmente** y nuestro cálculo POWER entrega **máximos anuales por celda promediados después**. Las pendientes y p no deben compararse como si midieran la misma magnitud. El siguiente paso científico es alinear definiciones y periodos, analizar la sensibilidad y cotejar ambos a escala comparable antes de crear un hallazgo para la aplicación.

```powershell
python scripts/normalize_giovanni.py data/raw/giovanni/gpcp_1992_2024.csv data/processed/giovanni_gpcp_1992_2024.csv data/processed/giovanni_gpcp_1992_2024.metadata.json --variable GPCPMON_3_3_sat_gauge_precip
python scripts/normalize_giovanni.py data/raw/giovanni/rx5day_1992_2024.csv data/processed/giovanni_rx5day_1992_2024.csv data/processed/giovanni_rx5day_1992_2024.metadata.json --variable M2SMNXEDI_2_RX5Day
python scripts/analyze_power.py data/processed/giovanni_gpcp_1992_2024.csv data/results/giovanni_gpcp_1992_2024.json --product-source Giovanni
python scripts/analyze_power.py data/processed/giovanni_rx5day_1992_2024.csv data/results/giovanni_rx5day_1992_2024.json --product-source Giovanni
```

## 13. Selección interactiva de años en el MVP

Los seis JSON mensuales integrados conservan enero de 1992 a diciembre de 2024 sin meses faltantes. La interfaz permite seleccionar años completos dentro de esa cobertura, con un mínimo de diez años como en los scripts de análisis. Al analizar, `lib/seasonal-trend.ts` aplica a los meses elegidos la misma regresión de tiempo lineal e indicadores de mes, con covarianza HAC/Newey–West de Bartlett y 12 rezagos. El intervalo bilateral del 95 % usa el cuantil normal, como `statsmodels` para estos ajustes. Con la ventana completa, pendiente y extremos del intervalo coinciden con los resultados Python versionados a una tolerancia de `1e-9`.

La gráfica y el CSV usan las medias simples de los doce meses de cada año seleccionado. La recta mostrada conserva la pendiente mensual y se centra en la media de esos resúmenes anuales; sirve de guía visual. Las anomalías almacenadas conservan la referencia fija 1992–2021, pero no entran en el ajuste de tendencias por periodo. Cada periodo elegido constituye un análisis exploratorio nuevo; seleccionar varios hasta encontrar un intervalo que excluya cero requiere control de pruebas múltiples antes de presentar un hallazgo firme.

El RX5day **anual derivado de POWER** usa directamente sus máximos anuales, con un mínimo de veinte años consecutivos como `scripts/analyze_annual.py`. `lib/annual-trend.ts` recalcula la regresión anual lineal y la covarianza HAC de Bartlett con tres rezagos. La ventana completa reproduce pendiente e IC del resultado Python a una tolerancia de `1e-9`. La evidencia, el CSV y el chat local muestran el método y tamaño de muestra de la variable activa. El índice anual y el RX5Day mensual de Giovanni no se consideran intercambiables.

## 14. Aplicación a Chihuahua interior y la caja sur

Repetimos el flujo anterior para `mx-chihuahua-interior` (`[-107, 28, -105, 30]`) y `mx-south-humid` (`[-94, 16, -92, 18]`) con el mismo periodo 1992–2024. Los scripts aceptan `--region` y guardan originales, procesados y resultados en subcarpetas con ese ID. Antes del análisis, comprueban que el ID y la caja de los metadatos coincidan con la ruta solicitada. Se ejecutaron cuatro consultas mensuales POWER por caja y 33 consultas diarias POWER por caja, una por año. También se exportaron por Giovanni GPCP y RX5Day para cada caja.

Las cuatro series mensuales POWER y las dos de Giovanni tienen 396 meses consecutivos sin valores faltantes en cada caja. Las respuestas mensuales POWER contienen 20 centros de celda válidos en Chihuahua y 15 en la caja sur. El índice anual derivado de los datos diarios tiene 33 valores por caja. Giovanni guarda en sus CSV una caja efectiva específica del producto; sus límites figuran en el [glosario](DATASETS.md) y en los metadatos procesados. La interfaz recalcula tendencias con la región, variable y periodo seleccionados. Los resultados son **exploratorios**: todavía no hay prueba directa de la diferencia entre pendientes regionales ni corrección por comparaciones múltiples.

## 15. Auditoría estadística de tendencias

La auditoría reproducible de tres series de la caja noreste integradas en la app (T2M de POWER, GPCP y `RX5Day` de Giovanni) está en [`analysis/`](../analysis/README.md) y se define en el [plan](ANALISIS_TENDENCIAS_PLAN.md). Reproduce a precisión de máquina las pendientes, los intervalos y los valores p de las secciones 7, 10 y 12, y los compara con la app (`tests/python-parity.test.ts`). Añade el control por Niño 3.4, bootstrap por bloques, rupturas, ventanas preespecificadas y corrección de Holm. No sustituye ninguna cifra anterior ni cambia el significado de los campos de `data/results/`. Esta auditoría todavía no se ha repetido para Chihuahua interior ni para la caja sur.
