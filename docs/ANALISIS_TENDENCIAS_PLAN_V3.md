# Plan v3: cierre de la validación (definido antes de ejecutar)

Responde a la revisión del equipo sobre los resultados de v1 y v2 (ya conocidos al escribir este plan). No añade modelos predictivos. El SHA-256 de este archivo se guarda en `analysis/results/run_info_v2.json`.

## 1. Intervalos y valores p

**Qué se hizo antes y por qué se reemplaza.** En la simulación de v1/v2 (1000 réplicas), el ruido era AR(1) con φ = 0.37 fijo, tomado de los residuos de T2M sin ENSO. No se estimó para cada variable tras retirar calendario y ENSO. La "p de Holm 0.09" de v1 se obtuvo dividiendo el estadístico z entre un factor de inflación. Ese número no es un valor p válido bajo una hipótesis nula enunciada, así que **se retira** y no alimenta a Holm.

**Nuevo procedimiento: bootstrap-t con criba autorregresiva (sieve), por variable y modelo:**
1. Se ajusta el modelo restringido sin tendencia (calendario, o calendario + Niño 3.4 para M1) y se toman sus residuos.
2. Se ajusta un AR(p) a los residuos, con p ∈ {0,…,12} elegido por AIC (`statsmodels` `ar_select_order`). Las innovaciones se estandarizan por su desviación típica de cada mes del calendario.
3. Series nulas: valores ajustados del modelo restringido + AR(p) generado con innovaciones remuestreadas (con reemplazo) del conjunto estandarizado y reescaladas por la desviación del mes. 200 meses de calentamiento. B = 4999, semilla 20261114. Niño 3.4 se trata como regresor fijo.
4. En cada serie se calcula el mismo estadístico que en los datos: t = β̂/SE_HAC12 del modelo completo.
5. **p bootstrap** = (1 + #{|t*| ≥ |t_obs|})/(B + 1). Es un valor p válido bajo esa nula, y **es el que entra en Holm** (F1: M0, F2: M1). **Intervalo bootstrap-t:** β̂ ± q*·SE_HAC12, con q* el percentil 95 de |t*|. **Cobertura real del IC HAC nominal** bajo ese proceso: P(|t*| ≤ 1.96), que es válida porque t es pivotal en este modelo lineal.
6. Sensibilidades: AR(1) en lugar de la elección por AIC; innovaciones gaussianas; sin escalado por mes.
7. Índices anuales de extremos (TX90p, CDD, Rx5day): igual, con AR(p ≤ 3) y t = β̂/SE_HAC(2); Holm en la familia B con esos p.

Supuestos: errores lineales estacionarios tras el escalado mensual, regresores fijos y nula sin tendencia. No cubre rupturas ni no linealidades (sección 3).

## 2. Reconciliación de la lluvia diaria y mensual

Nueva descarga de PRECTOTCORR diaria en **LST** (`scripts/power_daily_rain_lst.py`, `data/external/power_daily_prectotcorr_lst/`); la API diaria permite UTC o LST. Comparaciones con el mismo producto, celdas (comprobando que coincidan), pesos cos(lat), fechas y unidades (mm/día, media aritmética de los días del mes):
- (a) mensual de la API frente a la media mensual de los datos diarios **LST** (mismo estándar horario): diferencia que permanece.
- (b) diario UTC frente a diario LST: efecto del estándar horario, por mes y por celda.
- Rx5day anual recalculado con LST como sensibilidad del hallazgo de extremos.

Se informan máximo, media, percentil 99 y los meses con mayor diferencia. Rx5day anual (máximo anual por celda) y RX5Day mensual de Giovanni (máximos mensuales promediados) miden cosas distintas: que uno aumente y el otro no tenga evidencia suficiente no es una contradicción.

## 3. Discontinuidades y forma del cambio

Fechas documentadas, verificadas en la GMAO Office Note 9 (MERRA-2 File Specification): las corrientes de producción empiezan el 1992-01-01 (200), el 2001-01-01 (300) y el 2011-01-01 (400), cada una inicializada desde MERRA con un año de spin-up. No se supone que causen un salto en esta región. GPCP no es MERRA-2: un salto en GPCP en esas fechas no se atribuiría a las corrientes.

Hipótesis, con calendario y Niño 3.4 en todos los modelos:
- H0: sin cambio de la media.
- HL: tendencia lineal.
- HS(d): escalón en d ∈ {2001-01, 2011-01}.
- HL+S(d): tendencia y escalón.

Para cada variable mensual y cada índice anual se informan los coeficientes con HAC, la prueba de Wald del escalón dado la tendencia y de la tendencia dado el escalón, y el AIC como descripción (supone errores independientes). En las simulaciones, el escenario de escalón se describe como "rechazo correcto de H0 (sin cambio) con la forma mal identificada", no como falso positivo.

## 4. Agrupaciones

Pendientes sin redondear. Errores HAC con rezagos equivalentes a **6, 12 y 24 meses** en cada agrupación (rezagos = duración/longitud del bloque, redondeado). Variante de mínimos cuadrados ponderados por días válidos en los bloques de 1–14 días. Se explica por qué la identidad de las medias anuales no implica regresiones iguales: los bloques desiguales pesan igual en MCO, cambian el modelo de calendario y la exclusión del DJF incompleto.

## 5. Disponibilidad de ENSO en el pronóstico

Tabla explícita: un pronóstico emitido a comienzos de enero del año Y usa Niño 3.4 de diciembre de Y−1. CPC publica el valor mensual de ERSSTv5 a comienzos del mes siguiente, pero el archivo usado es la versión de agosto de 2026, posiblemente revisada, no la que existía en tiempo real. Los modelos RECON usan enero–diciembre de Y, que no estarían disponibles.

## 6. Entrega

Commit en `analysis/trend-audit`, integración con `origin/main` sin reescribir trabajo ajeno, pruebas, instalación limpia de `requirements.txt` en un entorno nuevo y push de la rama (sin force). Tabla final: **sustentado**, **sensible** o **pendiente**.

## 7. Correcciones posteriores a la revisión del PR #1

- **Salida única.** Holm de F1 y F2 (`trend_results.csv`), la clasificación A–D (`classification.json`), los informes por variable, la familia B (`extremes_trends.csv`) y `SUMMARY.md` usan ahora los mismos p del bootstrap-t con criba AR (mismas semillas que `uncertainty_validation.csv`). El criterio "IC de M1 excluye cero" usa el IC bootstrap-t. `SUMMARY.md` y `final_status.csv` los escribe solo `scripts/final_summary.py`. Una prueba unitaria comprueba que coinciden.
- **Regla añadida después de ver resultados:** un resultado que pase las pruebas se marca **pendiente** si un escalón en una fecha documentada de cambio de procesamiento ajusta igual o mejor (ΔAIC ≤ 0 frente a la recta y p del escalón < 0.05).
- **ENSO:** la proporción atribuida a ENSO es el incremento de R² de las anomalías al añadir ENSO sobre calendario + tendencia (`enso_increment_of_anomaly_variance`), no el R² total, que incluye la tendencia.
- **Puerta de la red neuronal:** decide solo con las particiones externas 2016–2020 (MAE medio menor que OLS_TREND y menor en al menos 4 de 5). El periodo reservado ya no participa en ninguna decisión; solo se informa.
