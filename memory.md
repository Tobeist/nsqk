# memory.md — estado del proyecto para continuar

Actualizado: 15 de noviembre de 2026. Sustituye para este repositorio a la antigua `MEMORIA.md` (fuera del repo, 14-nov), que es anterior a la implementación y no definía variable objetivo ni error base.

## Datos

- **Series mensuales 1992–2024** (396 meses, sin faltantes ni valores de relleno): `data/results/*.json` para el noreste, y `data/results/<region-id>/` para `mx-chihuahua-interior` y `mx-south-humid`. Variables:
  - POWER: T2M, T2M_MIN, T2M_MAX y PRECTOTCORR.
  - Giovanni: GPCP y RX5Day mensual.
  - Rx5day anual derivado de POWER diario.
- **Diarios POWER (UTC):** T2M y T2M_MAX en `data/external/power_daily_t2m/`; PRECTOTCORR en `data/raw/power_daily_prectotcorr/` (y en LST en `data/external/power_daily_prectotcorr_lst/`).
- **ENSO:** Niño 3.4 mensual de NOAA CPC (ERSSTv5, base 1991–2020) en `data/external/enso/`.
- **Cajas:** noreste `[-101,25,-99,27]` (78 % Nuevo León, 3 % Texas), Chihuahua interior `[-107,28,-105,30]` y sur húmedo `[-94,16,-92,18]`. No representan estados completos.

## Estado de los análisis

- **Tendencias (app):**
  - Método: MCO mensual con calendario + Niño 3.4, bootstrap-t con criba AR y Holm sobre 18 series mensuales y, por separado, 3 anuales (`docs/APP_TREND_PROTOCOL.md`).
  - T2M del noreste: +0.267 °C/década, IC [+0.011, +0.523], p de Holm 0.48, **inconcluso**.
  - Rx5day anual del noreste y T2M/T2M_MIN de Chihuahua: significativos pero **pendientes**, porque un escalón en las fechas de cambio de corriente de MERRA-2 ajusta igual.
- **Auditoría histórica:** `docs/INFORME_TENDENCIAS.md` y `analysis/results/`.
- **Predicción de la app** (`docs/FORECAST_PROTOCOL.md`): pronósticos a 12 meses emitidos cada diciembre. Hiperparámetros elegidos con 2016–2020; prueba retrospectiva 2021–2024, ya examinada varias veces.

## Experimento de red profunda (15-nov-2026)

Protocolo previo: `docs/DEEP_FORECAST_PROTOCOL.md`. Código: `scripts/t2m_heatmaps.py` y `scripts/deep_forecast.py`. Dependencias: `requirements-deep.txt`. Resultados: `analysis/deep/`.

- **Objetivo:** T2M mensual del noreste.
- **Error base:** el "error histórico medio" de la app para esa serie, **MAE 1.348 °C** en 2021–2024 (modelo desplegado `neural`). Referencias: climatología 1.450, tendencia 1.349.
- **Arquitectura ganadora (v2, tras corregir la parada temprana):**
  - proyección lineal → 1 bloque Conv1D causal residual (32 canales, LayerNorm, GELU) → BiGRU de 32 unidades → atención aditiva → cabeza MLP con salto, que da 12 salidas directas;
  - predice el residuo sobre tendencia + mes ajustado en cada origen.
- **Hiperparámetros congelados:**
  - ventana de 12 meses;
  - variables: T2M, T2M_MIN, T2M_MAX + Niño 3.4 (sin las series de lluvia);
  - dropout 0.388, AdamW con lr 5.56e-04 y weight_decay 7.29e-05;
  - CosineAnnealingLR, HuberLoss, batch 32, hasta 400 épocas con paciencia 60;
  - ensamble de 5 semillas.
- **Búsqueda:** Optuna TPE con 30 + 20 ensayos, solo en validación 2016–2020.
- **Métricas (v2):**

| Conjunto | Red | Modelo desplegado |
| --- | ---: | ---: |
| Validación 2016–2020, MAE (ensamble) | 0.943 | 0.958 |
| Prueba 2021–2024, MAE | **1.307** | 1.348 |
| Prueba, RMSE / MSE | 1.675 / 2.805 | 1.731 / 2.995 |
| Prueba, R² de valores mensuales | 0.908 | 0.901 |
| Prueba, R² de anomalías | 0.144 | 0.086 |

  - Mejora frente al modelo desplegado: **3.0 %**; frente a la climatología: 9.8 %.
  - **Diebold–Mariano:** p = 0.35, sin diferencia significativa. No cumple la regla de publicación; no se despliega.
  - **v1, con validación solapada (archivada):** prueba 1.339, p = 0.76.
- **Lectura:**
  - Corregir el solapamiento cambió la configuración elegida y bajó el error de prueba, pero la diferencia con el modelo desplegado sigue sin ser significativa en 48 meses.
  - La prueba ya se había visto en v1, así que v2 no es una evaluación ciega.
  - La anomalía de T2M casi no tiene memoria más allá de 2–3 meses (r ≤ 0.24 desde el rezago 2).
  - El R² de 0.91 refleja sobre todo el ciclo anual.
- **No se reentrenó mirando la prueba.** Hacerlo convertiría 2021–2024 en entrenamiento y cualquier "mejora" sería falsa.
- **Correcciones:** (1) la parada temprana compartía hasta 11 meses objetivo con el entrenamiento; se separaron y se repitió el experimento (v2). (2) **Fuga corregida antes de evaluar v1:** la escala de Niño 3.4 usaba noviembre y diciembre del año de origen. Se detectó con `tests/test_deep_forecast.py`, se detuvo la corrida (sin haber evaluado la prueba) y se relanzó corregida.

## Siguientes pasos razonables

- No invertir más en redes para T2M mensual con este conjunto de datos. Una mejora real requeriría información nueva con capacidad predictiva, como pronósticos de ENSO, en lugar de ENSO persistido.
- Contrastar las tendencias pendientes (Rx5day del noreste, temperaturas de Chihuahua) con datos independientes de MERRA-2, por ejemplo estaciones GHCN-Daily.
- Evaluar los pronósticos con observaciones de 2025 cuando existan.
