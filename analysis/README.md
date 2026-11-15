# Auditoría de tendencias

Plan y reglas definidos antes de comparar resultados: [`docs/ANALISIS_TENDENCIAS_PLAN.md`](../docs/ANALISIS_TENDENCIAS_PLAN.md).

## Reproducir

```bash
python -m pip install -r requirements.txt
python scripts/fetch_enso.py        # solo si falta data/external/enso/ (Niño 3.4 de NOAA CPC)
python scripts/trend_audit.py       # semilla 20261114, 5000 réplicas de bootstrap, unos 10 s
python -m unittest tests/test_trend_lib.py
npm test                            # incluye tests/python-parity.test.ts (Python frente a la app)
```

`trend_audit.py` no modifica `data/raw/`, `data/processed/` ni `data/results/`. Escribe solo en `analysis/`.

`scripts/final_summary.py`, ejecutado al final de `run_analysis.py`, genera `final_status.csv`, `final_status.json` y `SUMMARY.md` desde los mismos resultados. Es la auditoría original, limitada a la caja noreste y el periodo completo 1992–2024. La app usa ahora su extensión reproducible a 21 series en `analysis/app/1992-2024.json` y recalcula otros periodos con `scripts/app_trends.py`; véase [el protocolo de integración](../docs/APP_TREND_PROTOCOL.md). La familia mensual ampliada tiene 18 pruebas en lugar de tres: los p ajustados de ambos informes no son intercambiables.

## Resultados (`analysis/results/`)

| Archivo | Contenido |
| --- | --- |
| `SUMMARY.md`, `informe_<variable>.md` | Resumen e informes por variable (se regeneran con cada ejecución) |
| `trend_results.csv` / `.json` | Una fila por variable, ventana, modelo y método de incertidumbre: pendiente, SE, IC, p original y de Holm, familia, n, diagnósticos de residuos |
| `enso_comparison.csv`, `enso_by_season.csv` | β sin y con ENSO (mismas fechas), coeficiente de ENSO, colinealidad, ENSO por estación |
| `breaks_linearity.csv`, `influence_leave_one_year_out.csv`, `rolling_slopes.csv` | Rupturas y linealidad, omisión de años, pendientes de ventanas móviles |
| `data_audit.json`, `spatial_audit.json` | Auditoría de datos y de cobertura espacial |
| `reproduction_check.csv`, `consistency_checks.json`, `parity_fixture.json` | Comparación con los JSON versionados y con la app |
| `coverage_simulation.json`, `size_calibration_exploratory.json` | Tamaño empírico de las pruebas y calibración exploratoria |
| `classification.json`, `run_info.json` | Clasificación por las reglas del plan; semilla, versiones, hashes de entradas, del plan y de ENSO |

Figuras en `analysis/figures/`: series con ajuste, pendientes por modelo, diagnósticos de residuos y ventanas móviles.

Columnas clave de `trend_results.csv`: `model` (`M0` base; `M1_L{0,3,6}` con Niño 3.4 y rezago L; `M1S_L0` ENSO por estación; `SEASONAL_THEIL_SEN`; `M0_pct_of_monthly_mean`), `method` (`HAC6/12/24`, `HAC12_t`, `BOOT12/24/36`, `THEILSEN_BOOT2y`), `family` (`F1`, `F2` o `exploratory`), `p_holm` solo en F1 y F2. Los intervalos son del 95 % individuales; `ci_simultaneous_*` (Bonferroni, tres pruebas) solo en F1.

## Versión 2: agrupaciones, extremos, predicción y simulaciones

Informe: [`docs/INFORME_TENDENCIAS.md`](../docs/INFORME_TENDENCIAS.md). Plan: [`docs/ANALISIS_TENDENCIAS_PLAN_V2.md`](../docs/ANALISIS_TENDENCIAS_PLAN_V2.md).

```bash
python scripts/power_daily_temperature.py   # solo si falta data/external/power_daily_t2m/ (T2M y T2M_MAX diarios POWER, UTC)
python scripts/run_analysis.py              # todo: v1, agrupaciones, simulaciones, Prophet + Optuna y pruebas (≈ 2 min con 7 procesos)
```

| Archivo | Contenido |
| --- | --- |
| `grouping_definitions.csv`, `grouping_trends.csv`, `aggregation_identity.csv` | Agrupaciones (definición, cobertura, finalidad, justificación), pendiente por agrupación con el mismo producto diario, identidad de la media anual |
| `extremes_annual.csv`, `extremes_trends.csv` | TX90p, CDD y Rx5day anuales (POWER diario) y sus tendencias (familia B, Holm) |
| `variance_decomposition.csv`, `product_coherence.json` | R² de calendario, tendencia y ENSO; diferencias diario–mensual entre productos |
| `forecast_performance_by_fold.csv`, `forecast_summary.csv`, `optuna_trials.csv`, `forecast_config.json` | Desempeño por partición (MAE, RMSE, sesgo, cobertura del 80 %), resumen y regla de mejora consistente, los 1500 ensayos de Optuna (1350 de Prophet y 150 de la red), configuración y mejores parámetros |
| `simulation_study.csv`, `simulation_config.json` | Falsos positivos, potencia, sesgo y cobertura con series sintéticas |
| `run_info_v2.json` | Versiones, semilla, hashes de los planes y de las entradas diarias |

Figuras nuevas: `ciclo_estacional.png`, `anomalias_enso.png`, `agrupaciones.png`, `extremos.png`, `prediccion_mae.png`. Pruebas: `tests/test_v2_procedures.py` (identidad de agregación, bloques, estaciones incompletas y ausencia de fuga temporal).

## Versión 3: cierre de la validación

Plan: [`docs/ANALISIS_TENDENCIAS_PLAN_V3.md`](../docs/ANALISIS_TENDENCIAS_PLAN_V3.md). `python scripts/power_daily_rain_lst.py` descarga la lluvia diaria en LST si falta `data/external/power_daily_prectotcorr_lst/`. `run_analysis.py` ya incluye estos pasos.

| Archivo | Contenido |
| --- | --- |
| `uncertainty_validation.csv` | Bootstrap-t con criba AR: p válidos, Holm (F1, F2, B), IC bootstrap-t, cobertura real del IC HAC nominal y sensibilidades |
| `rain_reconciliation.json`, `rx5day_utc_vs_lst.csv` | Mensual API frente a diario LST/UTC con el mismo producto, celdas, pesos y unidades; Rx5day con ambos estándares horarios |
| `form_of_change.csv` | Recta frente a escalón en las transiciones documentadas de MERRA-2 (2001-01, 2011-01) |
| `grouping_trends.csv` | Columnas añadidas: SE con rezagos equivalentes a 6/12/24 meses y WLS por días |

La "calibración exploratoria" de la versión 1 (`size_calibration_exploratory.json`) se retiró: no producía valores p válidos.
