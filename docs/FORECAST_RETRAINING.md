# Reentrenamiento exploratorio con ENSO — v2

Comparación ejecutada el 15 de noviembre de 2026 con las mismas 18 series mensuales de 1992–2024. La búsqueda de cuatro configuraciones ENSO quedó fijada en el protocolo antes de calcular sus errores; no se ajustó después. No se añadieron observaciones nuevas. La red original y los tres comparadores originales conservan sus resultados.

El modelo ENSO ganó la validación 2016–2020 en **7 de 18 series**. En esas siete, la auditoría reutilizada 2021–2024 mejoró respecto al modelo que estaba desplegado en tres y empeoró en cuatro. Frente a la red original, la nueva red ENSO mejoró en **6 de 18 series**. No hay evidencia de mejora general y estos periodos conocidos no constituyen una confirmación nueva.

**Decisión de publicación posterior a los resultados:** conservar el modelo original por defecto en las 18 series; ofrecer la red ENSO sólo como comparación experimental. No se cambia de modelo por caja según el resultado 2021–2024. La interfaz distingue el modelo desplegado (`selectedModel`) del ganador de validación (`validationWinner`). Se necesitan nuevas observaciones y validación independiente antes de promover una versión.

| Caja / variable | Modelo previo, error de auditoría | Red original | ENSO, error de auditoría | Cambio vs. modelo previo |
|---|---:|---:|---:|---:|
| Noreste / T media | 1.348 °C | 1.348 °C | 1.426 °C | 5.8 % más error |
| Noreste / T mínima | 1.989 °C | 1.989 °C | 1.956 °C | 1.7 % menos error |
| Noreste / T máxima | 1.748 °C | 1.553 °C | 1.612 °C | 7.8 % menos error |
| Chihuahua interior / T media | 1.249 °C | 1.249 °C | 1.298 °C | 3.9 % más error |
| Sur húmedo / T media | 0.717 °C | 0.740 °C | 0.720 °C | 0.4 % más error |
| Sur húmedo / T mínima | 1.318 °C | 0.923 °C | 1.004 °C | 23.9 % menos error |
| Sur húmedo / GPCP | 1.134 mm/día | 1.124 mm/día | 1.165 mm/día | 2.7 % más error |

Los errores son MAE mensual, no porcentaje de acierto. El 23.9 % de mejora de T mínima del sur se compara con el modelo previo que repetía el último año: **no es una mejora sobre la red original**, que en esta auditoría tuvo menor error (0.923 °C frente a 1.004 °C de ENSO). Para T máxima de Chihuahua se conserva la red original: 1.220 °C frente a 1.272 °C con ENSO.

El CSV incluye todas las series y las comparaciones emparejadas de 4 y 8 neuronas con alpha=10, con y sin ENSO, tanto en validación como en auditoría. Sirven para distinguir el agregado de ENSO de los cambios de regularización; los candidatos alpha=50 cambian ambas cosas y su posible mejora no se atribuye sólo a ENSO.

No hubo advertencias de falta de convergencia. Las bandas permanecen orientativas y no garantizan 80 % de cobertura. El modelo ENSO sólo conoce el índice hasta octubre del año anterior y supone persistencia para cualquier fecha posterior; no usa ENSO futuro observado. Las fuentes son versiones actuales revisadas con una normal fija 1991–2020, no datos archivados disponibles realmente en cada origen.

El CSV guarda la huella del artefacto original y la actual. Se puede reproducir con el entorno de `requirements-forecast.txt`:

```sh
git show a026fec:analysis/forecast/app-forecast.json > /tmp/nsqk-forecast-v1-baseline.json
OPENBLAS_NUM_THREADS=1 python scripts/app_forecast.py --comparison-baseline /tmp/nsqk-forecast-v1-baseline.json
python -m unittest tests/test_app_forecast.py
```

La proyección sigue siendo de 2025 desde observaciones hasta diciembre de 2024. No se ha contrastado con 2025 ni es un pronóstico meteorológico actual. No cambia la inferencia ni las clasificaciones de las tendencias históricas.

Fuentes y método: [protocolo](FORECAST_PROTOCOL.md), [comparación completa](../analysis/forecast/retraining-comparison.csv), [NOAA CPC Niño 3.4 ERSSTv5](https://www.cpc.ncep.noaa.gov/data/indices/ersst5.nino.mth.91-20.ascii).
