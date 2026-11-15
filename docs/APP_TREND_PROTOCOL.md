# Protocolo de integración de tendencias

Extensión del análisis revisado en los PR #1 y #2 a las siete series de cada una de las tres cajas. Este protocolo se fija antes de ejecutar la extensión; no modifica los resultados históricos de `analysis/results/`.

- Periodo: años completos elegidos por el usuario entre 1992 y 2024. Al menos diez años para series mensuales y veinte para el índice anual. La selección de meses/días parciales necesita una validación adicional y no se simula mediante interpolación.
- Serie principal mensual: MCO con intercepto, tiempo en años, once indicadores mensuales y Niño 3.4 contemporáneo (NOAA CPC, ERSSTv5). Comparación: mismo modelo sin ENSO, sobre exactamente las mismas fechas.
- Incertidumbre principal: bootstrap-t con criba AR, 4,999 réplicas, 200 pasos de calentamiento, AR(p<=12) seleccionado por AIC, innovaciones estandarizadas por mes. HAC(12) para studentizar. Se conserva el generador del PR #2; la evaluación matricial se comprueba contra statsmodels.
- Dos familias mensuales, una por modelo: las 18 combinaciones de seis variables por tres regiones, aunque la pantalla muestre sólo una selección. Holm no cambia por las variables visibles. Esta familia ampliada sustituye para la app a las familias de tres pruebas de la auditoría original; sus p ajustados pueden ser diferentes.
- RX5day anual: MCO anual sin ENSO, HAC(2), criba AR(p<=3), 4,999 réplicas. Holm sobre tres cajas en una familia separada. No se convierte un índice mensual en máximo anual. Sensibilidades HAC(1/2/3) y bloques de tres años.
- Diagnósticos: dependencia residual, sensibilidad HAC(6/12/24) para meses, bootstrap por bloques y signo en subperiodos fijos: primera y segunda mitades si ambas tienen al menos diez años (o veinte en anual). Son diagnósticos descriptivos, sin búsqueda del menor p.
- Cambios de nivel: comparación exploratoria con escalones en enero de 2001 y 2011, cuando queden al menos cinco años a ambos lados. AIC es descriptivo bajo errores independientes, no prueba de causalidad. Un escalón con p HAC<0.05 y AIC no mayor que la recta marca un resultado significativo como pendiente de contraste independiente. Es una regla exploratoria heredada del cierre v3, posterior a los primeros resultados.
- Estado: no evaluable si el modelo AR no es estable; inconcluso si Holm>=0.05; pendiente si pasa Holm pero hay un escalón compatible; sensible si pasa Holm pero cambia el signo en subperiodos; consistente en las comprobaciones restantes. Los intervalos del 95% son individuales, no simultáneos. No se interpreta un intervalo sin cero como evidencia familiar suficiente.
- Se muestran la pendiente condicionada a ENSO y la pendiente sin ENSO. La recta de la gráfica anual es una guía centrada en las medias, no reconstruye la contribución estacional ni es una regresión anual adicional.
- No hay atribución causal, predicción ni selección de hiperparámetros en el análisis de tendencia. El ensamble AR es una aproximación condicionada a sus supuestos, no una garantía universal de cobertura.
- Cada resultado identifica periodo, fuentes, hashes, semilla, réplicas, familia y método. La app, el mapa, la explicación local y el CSV comparten esos resultados. Un rango sin resultado calculado no puede recuperar estadísticas del rango completo.

Reproducción: `python scripts/app_trends.py --start 1992 --end 2024 --output analysis/app/1992-2024.json`. La API usa el mismo comando mediante stdin, sin ejecutar texto de shell recibido del usuario. Los demás rangos se guardan en `.cache/trends/`, invalidada por los hashes de datos, código y protocolo.

## Ejecutar la app con cálculo de periodos

Se necesita un servidor Node con Python 3.9–3.12; no es una exportación estática. Desde la raíz:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-analysis.txt
source .venv/bin/activate
npm ci
npm run dev
```

En Windows o con otro entorno, configura `PYTHON_BIN` con la ruta del ejecutable. El periodo 1992–2024 tiene un artefacto reproducible incluido; otros rangos se calculan en `POST /api/analysis`. El servidor conserva los datos y scripts mediante el trazado de Next, pero el despliegue debe instalar Python y sus dependencias por separado. Un alojamiento que sólo ejecute JavaScript no puede calcular otros periodos. Si falla el motor, la interfaz conserva el análisis anterior identificado como tal y muestra el error; no presenta un cálculo antiguo como si correspondiera al rango nuevo.

Las peticiones simultáneas del mismo periodo comparten el cálculo; se admiten dos periodos en proceso y un máximo de 120 segundos por cálculo. La caché se escribe de forma atómica y no depende de las variables que se muestran. Los p de Holm controlan la familia del periodo elegido, no la búsqueda entre muchos periodos elegidos después de mirar resultados.

Comprobaciones: `.venv/bin/python -m unittest tests/test_app_trends.py tests/test_trend_lib.py tests/test_region_routes.py`, `npm test`, `npm run typecheck`, `npm run lint` y `npm run build`. La prueba de frescura compara todos los hashes del artefacto con las entradas actuales. Las pruebas de referencia HAC anteriores se conservan por separado; no alimentan las etiquetas de la app.
