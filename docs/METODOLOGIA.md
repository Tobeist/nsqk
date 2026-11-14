# Metodología de datos y análisis — Climate Paradox

**Estado:** cuatro variables mensuales procesadas de NASA POWER: temperatura media (`T2M`), temperatura mínima (`T2M_MIN`), temperatura máxima (`T2M_MAX`) y precipitación corregida (`PRECTOTCORR`). Este documento describe lo que ya ejecutamos y distingue los análisis pendientes. No representa todavía un protocolo validado para las nueve variables del producto.

## 1. Pregunta y alcance inicial

Queremos medir cómo cambió la temperatura media mensual en una caja de prueba del noreste de México y establecer un pipeline reproducible que después permita comparar promedios y extremos. La caja es **[-101, 25, -99, 27]** (oeste, sur, este, norte). Es un área rectangular de validación técnica; no representa la región Norte-Noreste formada por estados completos.

Usamos enero de 2010 a diciembre de 2012 para verificar extracción y estructura, y enero de 1992 a diciembre de 2024 para el primer análisis histórico. Elegimos el periodo antes de calcular la tendencia. Los tres años de prueba no se usan para inferencia de tendencias.

## 2. Fuente y procedencia

La serie descargada procede de la [API Monthly Regional de NASA POWER](https://power.larc.nasa.gov/docs/services/api/temporal/monthly/), parámetro `T2M`, comunidad `SB`, formato JSON. El encabezado de la respuesta consultada indica fuente `MERRA2`, unidad `C` y 15 puntos de malla en la caja. Según la [documentación de POWER](https://power.larc.nasa.gov/docs/methodology/data/sources_meteorology/), sus parámetros meteorológicos se basan en MERRA-2. **POWER es un producto procesado por su propia plataforma; no asumimos que sus valores coincidan exactamente con los del campo `M2TMNXSLV_5_12_4_T2M` solicitado a Giovanni.**

Intentamos solicitar ese campo de Giovanni directamente. El servicio reconoció la consulta y localizó los archivos mensuales, pero el flujo indicó que requiere inicio de sesión en Earthdata. La petición directa por OPeNDAP respondió HTTP 401. El cotejo Giovanni–POWER queda pendiente hasta contar con una extracción autenticada. No se mezclan ambas fuentes bajo un mismo identificador.

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

1. Obtener T2M `M2TMNXSLV_5_12_4_T2M` mediante una sesión Earthdata autenticada y comparar unidades, malla, agregación temporal y valores con POWER.
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

