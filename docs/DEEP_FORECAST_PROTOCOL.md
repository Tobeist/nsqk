# Protocolo: red profunda para T2M mensual del noreste (fijado antes de entrenar)

Experimento adicional al de [FORECAST_PROTOCOL.md](FORECAST_PROTOCOL.md). No cambia la app, la inferencia de tendencias ni el modelo desplegado.

## Contexto y error base

- No existe `memory.md` en el repositorio. El único archivo de memoria encontrado (`MEMORIA.md`, fuera del repo, 14-nov-2026) es anterior a la implementación y no define variable objetivo ni error base. Por eso se toman del repositorio:
  - **Objetivo:** T2M mensual de NASA POWER en la caja noreste `[-101, 25, -99, 27]`, 1992–2024, en °C.
  - **Error base:** el "error histórico medio" que muestra la app para esa serie (`analysis/forecast/app-forecast.json`): modelo desplegado `neural`, **MAE 1.348 °C** en 2021–2024. Como referencias adicionales: climatología 1.450, tendencia + calendario 1.349. En validación 2016–2020: 0.958 (desplegado) y 0.977 (tendencia).
- La misma `MEMORIA.md` desaconsejaba LSTM y Transformers para este equipo y este plazo. Este experimento se hace a petición explícita y se juzga con la misma evaluación que los modelos simples.

## Tarea idéntica a la de la app

Cada pronóstico se emite al cierre de diciembre del año Y−1 y predice los 12 meses de Y. Solo usa observaciones fechadas hasta diciembre de Y−1, y Niño 3.4 hasta octubre de Y−1 (dos meses de margen, como la app). Particiones cronológicas, sin mezclar al azar:
- **Validación:** años 2016–2020, con orígenes en diciembre de 2015–2019. Es lo único que elige hiperparámetros.
- **Prueba:** años 2021–2024. Se evalúa **una sola vez**, al final, con la configuración congelada. Estos años ya se examinaron en versiones anteriores (`FORECAST_RETRAINING.md`), así que no es una validación ciega.
- Dentro de cada origen, el entrenamiento usa ventanas cuyos 12 meses objetivo terminan antes o en el origen. Para la parada temprana se reservan las ventanas cuyos objetivos caen en los últimos 24 meses de ese entrenamiento.

**No se reentrena mirando la prueba.** La instrucción de "seguir reentrenando hasta bajar del error base evaluando validación y prueba" se aplica solo a validación. Ajustar con la prueba la convertiría en entrenamiento y haría falsa cualquier mejora reportada.

## Datos y características (todas conocidas en el origen)

- **Entradas mensuales de la caja noreste:** T2M, T2M_MIN, T2M_MAX y PRECTOTCORR (POWER), GPCP y RX5Day mensual (Giovanni), y Niño 3.4 (CPC, ERSSTv5; se usa hasta dos meses antes del origen y después se mantiene el último valor).
- **Auditoría previa:** no hay faltantes ni valores de relleno, así que **no se interpola**. Si apareciera un hueco, el experimento se detiene en lugar de rellenarlo. No se recortan extremos: son eventos reales (por ejemplo, el huracán Alex en 2010).
- **Transformaciones ajustadas solo con el entrenamiento de cada origen:**
  - climatología mensual de cada variable, para obtener anomalías;
  - `StandardScaler`;
  - regresión base de tendencia + 11 indicadores de mes sobre T2M. La red predice el **residuo** de esa regresión, así que solo puede aportar algo por encima del modelo de tendencia.
- **Características por mes de la ventana:** anomalías estandarizadas de las 7 series, seno y coseno del mes, y media y desviación móviles de 3 y 12 meses de la anomalía de T2M, calculadas solo hacia atrás.

## Arquitectura

Entrada: ventana de W meses × F características. Salida directa: 12 residuos. Componentes:
- proyección lineal;
- bloques **Conv1D residuales** (convolución causal-padding, LayerNorm, GELU, Dropout);
- **BiGRU** sobre la ventana, que es enteramente pasada, por lo que la dirección inversa no ve el futuro;
- **atención aditiva** como resumen;
- cabeza MLP con residual;
- más una codificación cíclica de los 12 meses objetivo.

Entrenamiento: **AdamW** con `weight_decay`, **CosineAnnealingLR**, **HuberLoss**, hasta **400 épocas** con `batch_size` 32, parada temprana con paciencia 60 y punto de control con el menor error de la parada temprana. Corre en CPU: no hay GPU CUDA y la precisión mixta no aplica. Semillas fijas.

## Búsqueda de hiperparámetros (solo validación)

Optuna TPE, semilla 20261114, **30 ensayos**. Criterio: MAE medio de los 60 meses de validación (cinco orígenes). Espacio:
- ventana W ∈ {24, 36, 48};
- canales ∈ {16, 32, 64};
- bloques conv ∈ {1, 2, 3};
- unidades GRU ∈ {16, 32, 64};
- dropout ∈ [0, 0.4];
- tasa de aprendizaje log-uniforme en [1e-4, 3e-3];
- `weight_decay` log-uniforme en [1e-5, 1e-1].

**Segunda ronda, solo si la primera no baja del error base de validación** (0.958): 20 ensayos más con el mismo espacio ampliado a W ∈ {12, 60} y sin las tres series de lluvia. Se registran todos los ensayos. Después se congela la configuración ganadora.

**Modelo final:** ensamble de 5 semillas por origen, promediado. Se fija de antemano para reducir la varianza, no para elegir la mejor semilla.

## Evaluación (una sola vez en prueba)

- MAE, RMSE, MSE y R² sobre los 48 meses de prueba; comparación con 1.348, la climatología y la tendencia, en porcentaje.
- El R² sobre valores mensuales queda inflado por el ciclo anual. Por eso también se informa el **R² de anomalías**, frente a la climatología de entrenamiento.
- Prueba de Diebold–Mariano (pérdida absoluta, varianza HAC con 11 rezagos) contra el modelo desplegado: una diferencia de MAE en 48 meses puede ser azar.
- Se guardan las curvas `train_loss`/`val_loss`, la serie real frente a la predicha y todos los ensayos.

**Regla de publicación:** se informa el resultado aunque sea peor. La red solo se describiría como mejora si su MAE de prueba es menor que 1.348 **y** la prueba de Diebold–Mariano tiene p < 0.05. Aun así seguiría siendo experimental hasta tener observaciones nuevas (2025 en adelante).

## Resultado (ejecutado el 15-nov-2026, después de fijar este protocolo)

| Conjunto | Red | Modelo desplegado |
| --- | ---: | ---: |
| Validación, MAE (ensamble) | 0.910 | 0.958 |
| Prueba 2021–2024, MAE | 1.339 | 1.348 |

- Diebold–Mariano: p = 0.76. **No se cumple la regla de publicación** y la red no se despliega. Detalle en `analysis/deep/deep_results.json` y en [`memory.md`](../memory.md).
- **Corrección previa a evaluar:** la escala de Niño 3.4 incluía noviembre y diciembre del año de origen, que aún no se conocen al emitir el pronóstico. La detectó `tests/test_deep_forecast.py`; la corrida se detuvo antes de evaluar la prueba y se repitió corregida.
