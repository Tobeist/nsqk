# Trend Detectives · Climate Paradox

MVP de exploración climática para NASA Space Apps 2026. La pantalla principal usa **datos NASA procesados**, guardados en este repositorio. La [metodología](docs/METODOLOGIA.md) y el [glosario](docs/DATASETS.md) describen fuente, unidades, agregación e incertidumbre. Proyecto independiente, sin respaldo oficial de NASA.

## Ejecutar

Requiere Node.js 20.19 o posterior y Python 3.9–3.12 para calcular periodos distintos de 1992–2024.

```bash
npm ci
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-analysis.txt
source .venv/bin/activate
npm run dev
```

La app estará en `http://localhost:3000`. Para verificar: `npm run typecheck`, `npm run lint`, `npm test` y `npm run build`.

## Cobertura real del MVP

La interfaz permite analizar las [tres cajas de estudio del MVP](docs/REGIONES.md): noreste, Chihuahua interior y sur de Chiapas–Tabasco. Se pueden elegir años completos entre **1992 y 2024** y hasta tres variables por análisis. En cada caja están habilitadas seis series mensuales: T2M, T2M_MIN, T2M_MAX y PRECTOTCORR de NASA POWER; precipitación GPCP y RX5Day mensual de Giovanni. También está habilitado el **RX5day anual derivado de POWER**. Las seis series mensuales requieren al menos diez años: regresión con indicadores de mes y Niño 3.4, comparada con el mismo modelo sin ENSO. El índice anual requiere veinte años y se analiza sin ENSO. Ambos usan bootstrap-t con criba AR (4,999 réplicas); la certeza se decide con Holm sobre las 18 series mensuales o los tres índices anuales, y diagnósticos de sensibilidad y escalones. Un IC individual sin cero no basta para declarar una tendencia concluyente.

Gráfica, mapa, explicación y CSV comparten el resultado auditado del periodo elegido. El rango completo se entrega precalculado; otros rangos se ejecutan en el servidor Python, sin sustituirlos por estadísticas de otro periodo. Protocolo, familias, límites, reproducción y despliegue: [docs/APP_TREND_PROTOCOL.md](docs/APP_TREND_PROTOCOL.md). La gráfica conserva su resumen anual; el modelo mensual usa todos los meses y controla el calendario estacional.

Las variables sin archivos procesados siguen deshabilitadas. Ninguna caja equivale a un estado completo ni a los cinco polígonos regionales propuestos. Las diferencias de malla y procesamiento entre POWER, GPCP y MERRA-2 se explican en la metodología. El RX5Day mensual de Giovanni y el RX5day anual de POWER tienen definiciones y fuentes distintas. T2M_MIN y T2M_MAX no son índices de noches cálidas u olas de calor. Comparar muchos periodos y elegir el más llamativo aumenta el riesgo de interpretar una señal casual como robusta.

La conversación usa Claude desde el servidor y conserva el contexto de la caja, variable y periodo visibles. El servidor reconstruye las estadísticas antes de consultar Anthropic; el navegador no envía cifras que puedan sustituir el análisis. La significancia se calcula con p de Holm < 0.05 y se muestra por separado de la solidez de la conclusión. Configuración y límites: [docs/CLAUDE.md](docs/CLAUDE.md). Las fixtures sintéticas y la ruta `/demo` fueron retiradas del MVP.

## Mapa del área de estudio

La vista «Estados» muestra fronteras reales de Natural Earth alrededor de la caja seleccionada. En el noreste intersecta Coahuila, Nuevo León, Tamaulipas y Texas; en Chihuahua interior intersecta Chihuahua; en el sur intersecta Chiapas, Tabasco, Veracruz y Oaxaca. Sólo el recuadro representa el análisis. La contribución efectiva de cada producto depende de sus celdas y máscaras; no hay resultados por estado completo. «Planeta 3D» conserva el globo como vista alterna.

La leyenda cambia con la variable y el periodo ejecutados y amplía su escala para cubrir la pendiente visible, incluido RX5Day. Más detalles y procedencia en [docs/INTERFAZ_MAPA.md](docs/INTERFAZ_MAPA.md).

## Qué falta para ampliar el producto

- Las regiones administrativas posteriores requerirán polígonos, máscara y pesos espaciales definidos. Las tres cajas actuales son rectángulos exploratorios.
- Descargar y validar los índices de calor, `R95P` y FLDAS. Habilitar una variable únicamente cuando existan su serie, unidades, procedencia y análisis reproducible.
- Cotejar T2M de POWER con la extracción directa de Giovanni y estudiar las diferencias entre el `RX5Day` oficial mensual y el índice anual derivado de POWER antes de presentar comparaciones de extremos.
- Extender los controles de variabilidad natural y contrastar los posibles escalones con productos independientes. ENSO y el calendario no representan todos los factores naturales. Un intervalo que incluye cero no demuestra ausencia de cambio.
- Evaluar las explicaciones de Claude con preguntas del equipo y casos de resultados inconclusos o pendientes. Las explicaciones de IA no sustituyen la validación científica ni atribuyen causas.

Los scripts Python en `scripts/` y los archivos originales en `data/raw/` se conservan para reproducibilidad. La cartografía local y sus atribuciones están en `public/assets/`.

La [auditoría estadística original](analysis/README.md) se reproduce con `python scripts/run_analysis.py` (informe: [docs/INFORME_TENDENCIAS.md](docs/INFORME_TENDENCIAS.md)). Se conserva intacta. Su extensión a las 21 series alimenta la app desde `analysis/app/1992-2024.json`, generado por `scripts/app_trends.py`; no reescribe los datos originales de `data/results/`.
