# Glosario de datos y variables

**Actualizado:** 14 de noviembre de 2026. Las series disponibles proceden de [NASA POWER Monthly Regional API](https://power.larc.nasa.gov/docs/services/api/temporal/monthly/) para la caja de prueba `[-101, 25, -99, 27]` (oeste, sur, este, norte). POWER informa MERRA-2 como fuente meteorológica. La caja no representa una de las cinco regiones completas propuestas para la aplicación.

## Fuentes

**NASA POWER.** Servicio que entrega series listas para análisis. Conservamos sus respuestas JSON originales. Sus valores procesados no se consideran automáticamente idénticos a los de Giovanni.

**MERRA-2.** Reanálisis meteorológico que POWER reporta como fuente de las cuatro variables descargadas. [Documentación de POWER](https://power.larc.nasa.gov/docs/methodology/data/sources_meteorology/).

**Giovanni.** Servicio NASA del que ya descargamos series regionales de GPCP y `RX5Day` mediante una sesión Earthdata autenticada. La descarga directa desde Python sin esa sesión sigue devolviendo HTTP 401.

## Variables descargadas

En la interfaz actual están habilitadas T2M, T2M_MIN, T2M_MAX, PRECTOTCORR mensual, GPCP, RX5Day mensual de Giovanni y el RX5day anual derivado de POWER. Se pueden seleccionar hasta tres a la vez. El índice anual requiere un periodo mínimo de veinte años; las seis series mensuales requieren diez.

**`T2M` — Temperatura media del aire a 2 m.** Serie mensual en °C; es la base para estudiar el cambio del promedio. Tenemos una prueba de 2010–2012 y la serie histórica de 1992–2024. [JSON original](../data/raw/power_t2m_1992_2024.json) · [CSV regional](../data/processed/power_t2m_region_1992_2024.csv) · [Resultado](../data/results/power_t2m_region_1992_2024.json).

**`T2M_MIN` — Temperatura mínima a 2 m.** Valor mensual en °C reportado por POWER. No cuenta noches cálidas o tropicales. Periodo: 1992–2024. [JSON original](../data/raw/power_t2m_min_1992_2024.json) · [CSV regional](../data/processed/power_t2m_min_region_1992_2024.csv) · [Resultado](../data/results/power_t2m_min_region_1992_2024.json).

**`T2M_MAX` — Temperatura máxima a 2 m.** Valor mensual en °C reportado por POWER. No equivale a frecuencia o duración de olas de calor. Periodo: 1992–2024. [JSON original](../data/raw/power_t2m_max_1992_2024.json) · [CSV regional](../data/processed/power_t2m_max_region_1992_2024.csv) · [Resultado](../data/results/power_t2m_max_region_1992_2024.json).

**`PRECTOTCORR` — Precipitación corregida.** Tasa media del mes en mm/día, derivada de POWER/MERRA-2. No es acumulado mensual ni el producto GPCP de satélite y pluviómetros. Periodo: 1992–2024. [JSON original](../data/raw/power_prectotcorr_1992_2024.json) · [CSV regional](../data/processed/power_prectotcorr_region_1992_2024.csv) · [Resultado](../data/results/power_prectotcorr_region_1992_2024.json).

**`PRECTOTCORR` diario — Precipitación corregida por día.** Datos en mm/día y tiempo UTC para 1992–2024. POWER limita cada petición diaria a 366 días, por lo que conservamos [un JSON original por año](../data/raw/power_daily_prectotcorr/) y un [CSV de valores diarios por celda](../data/processed/power_prectotcorr_daily_grid_1992_2024.csv). Esta serie es la entrada de nuestro índice de lluvia intensa.

**GPCP `GPCPMON_3_3_sat_gauge_precip` — Precipitación combinada de satélite y pluviómetros.** Media regional mensual en mm/día exportada por Giovanni para 1992–2024. Es una fuente distinta de `PRECTOTCORR` de POWER. El CSV original contiene metadatos de fecha, caja, valor de relleno `-99999` y URL de reproducción. [CSV original](../data/raw/giovanni/gpcp_1992_2024.csv) · [CSV limpio](../data/processed/giovanni_gpcp_1992_2024.csv) · [Resultado](../data/results/giovanni_gpcp_1992_2024.json). También conservamos la [prueba 2010–2012](../data/raw/giovanni/gpcp_2010_2012.csv).

**MERRA-2 `M2SMNXEDI_2_RX5Day` — Lluvia máxima en un intervalo de cinco días.** Índice mensual en mm por cinco días, promediado espacialmente por Giovanni para 1992–2024. No es la misma operación que nuestro máximo **anual** calculado con datos diarios de POWER. Su CSV original informa valor de relleno `-9999`. [CSV original](../data/raw/giovanni/rx5day_1992_2024.csv) · [CSV limpio](../data/processed/giovanni_rx5day_1992_2024.csv) · [Resultado](../data/results/giovanni_rx5day_1992_2024.json). También conservamos la [prueba 2010–2012](../data/raw/giovanni/rx5day_2010_2012.csv).

Las cuatro series históricas cubren **396 meses**, con **15 celdas válidas por mes** y sin faltantes. Los CSV de cada punto de malla y los archivos `*.metadata.json` están en [`data/processed/`](../data/processed/). El [JSON de prueba 2010–2012](../data/raw/power_t2m_2010_2012.json) también se conserva.

## Campos y resultados derivados

**`date`.** Mes etiquetado `AAAA-MM-01`. El día 1 identifica el periodo, no una medición instantánea.

**`latitude` y `longitude`.** Centro de cada punto de malla, en grados; aparecen en los CSV `*grid*.csv`.

**`t2m_c`, `t2m_min_c`, `t2m_max_c`.** Temperatura en °C para `T2M`, `T2M_MIN` y `T2M_MAX`, respectivamente.

**`prectotcorr_mm_day`.** Tasa media mensual de precipitación corregida, en mm/día.

**`gpcp_mm_day`.** Tasa media mensual de precipitación GPCP según la serie regional de Giovanni, en mm/día.

**`rx5day_mm_per_5days`.** Valor mensual del índice oficial `RX5Day` regional de Giovanni, en mm por cinco días.

**`valid_grid_cells`.** Número de celdas válidas usadas en la media regional del mes.

**Media regional mensual.** Promedio de los puntos de la caja ponderado por `cos(latitud)`. No recorta estados ni aplica máscara de tierra. Está en los CSV `*region*.csv`.

**Climatología mensual.** Promedio de cada mes del calendario durante el periodo fijo 1992–2021.

**Anomalía mensual.** Diferencia entre un valor y la climatología de su mismo mes. Está en los JSON de resultados y conserva la unidad original.

**Promedio anual.** Media aritmética de los doce valores mensuales, sin ponderar por los días del mes. Es descriptivo.

**Tendencia por década, intervalo de confianza y valor p.** Resultados exploratorios de regresión con estacionalidad mensual y errores HAC de 12 rezagos. Los valores p son individuales y no tienen corrección por múltiples pruebas. Véase la [metodología](METODOLOGIA.md).

**`RX5day` derivado de POWER — Lluvia máxima acumulada en cinco días.** Para cada celda y año calculamos la mayor suma de cinco días consecutivos, sin cruzar el límite entre años. Después promediamos esos máximos de celda con pesos `cos(latitud)`. Unidad: mm. Disponible como [CSV anual por celda](../data/processed/power_rx5day_annual_grid_1992_2024.csv), [CSV anual regional](../data/processed/power_rx5day_annual_region_1992_2024.csv) y [resultado exploratorio](../data/results/power_rx5day_annual_region_1992_2024.json). **Es un índice calculado por el equipo, no el `RX5Day` oficial de Giovanni.**

POWER también devuelve una clave `AAAA13` de resumen anual; se excluye de los CSV mensuales. El código excluye `-999` como valor faltante, aunque no apareció en estas cuatro series.

## Variables propuestas, aún sin datos descargados

**Giovanni `M2TMNXSLV_5_12_4_T2M`.** Extracción directa para cotejar con `T2M` de POWER. Aún no descargada; la sesión Earthdata ya está disponible.

**Otros índices `M2SMNXEDI`.** Falta descargar y validar noches cálidas o tropicales (`TN90p` o `TR`), días en ola de calor (`HWF`) y lluvia de días extremos (`R95P`). `TN90p` y `TR`, o `RX5Day` y `R95P`, responden preguntas diferentes.

**FLDAS.** Fuente propuesta para humedad superficial y profunda del suelo y evapotranspiración. Segunda fase; aún no hay archivos descargados.
