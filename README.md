# Trend Detectives · Climate Paradox

MVP de exploración climática para NASA Space Apps 2026. La pantalla principal usa **datos NASA procesados**, guardados en este repositorio. La [metodología](docs/METODOLOGIA.md) y el [glosario](docs/DATASETS.md) describen fuente, unidades, agregación e incertidumbre. Proyecto independiente, sin respaldo oficial de NASA.

## Ejecutar

Requiere Node.js 20.19 o posterior.

```bash
npm ci
npm run dev
```

La app estará en `http://localhost:3000`. Para verificar: `npm run typecheck`, `npm run lint`, `npm test` y `npm run build`.

## Cobertura real del MVP

La interfaz permite analizar **una caja de estudio** en el noreste de México (`[-101, 25, -99, 27]`). Ya están [fijadas tres cajas para el MVP](docs/REGIONES.md), pero las otras dos aún no tienen series procesadas. Se pueden elegir años completos entre **1992 y 2024** y hasta tres variables por análisis. Están habilitadas seis series mensuales: T2M, T2M_MIN, T2M_MAX y PRECTOTCORR de NASA POWER; precipitación GPCP y RX5Day mensual de Giovanni. También está habilitado el **RX5day anual derivado de POWER**. Al pulsar **Analizar selección**, la app filtra el periodo y recalcula medias anuales, pendientes e intervalos. Las seis series mensuales requieren al menos diez años y usan regresión mensual con estacionalidad y HAC(12); el índice anual requiere al menos veinte años y usa regresión anual con HAC(3).

Otras regiones y las variables sin archivos procesados están deshabilitadas. La caja no equivale a toda la región Norte-Noreste ni a los cinco polígonos regionales propuestos. Las diferencias de malla y procesamiento entre POWER, GPCP y MERRA-2 se explican en la metodología. El RX5Day mensual de Giovanni y el RX5day anual de POWER tienen definiciones y fuentes distintas. T2M_MIN y T2M_MAX no son índices de noches cálidas u olas de calor. Comparar muchos periodos y elegir el más llamativo aumenta el riesgo de interpretar una señal casual como robusta.

La sección de preguntas ofrece respuestas locales deterministas basadas en el resultado visible; **no consulta un modelo de IA**. Las fixtures sintéticas y la ruta `/demo` fueron retiradas del MVP.

## Mapa del área de estudio

La vista «Estados» muestra fronteras reales de Natural Earth y señala Coahuila, Nuevo León, Tamaulipas y Texas (EE. UU.), que intersectan la caja solicitada. Su relleno es contexto geográfico: sólo el recuadro representa el análisis. La contribución efectiva de cada producto depende de sus celdas y máscaras; no hay resultados por estado completo. «Planeta 3D» conserva el globo como vista alterna.

La leyenda cambia con la variable y el periodo ejecutados y amplía su escala para cubrir la pendiente visible, incluido RX5Day. Más detalles y procedencia en [docs/INTERFAZ_MAPA.md](docs/INTERFAZ_MAPA.md).

## Qué falta para ampliar el producto

- Descargar y procesar las mismas variables para las otras dos [cajas ya definidas](docs/REGIONES.md). No reutilizar la serie de la caja actual. Las regiones administrativas posteriores requerirán polígonos, máscara y pesos espaciales definidos.
- Descargar y validar los índices de calor, `R95P` y FLDAS. Habilitar una variable únicamente cuando existan su serie, unidades, procedencia y análisis reproducible.
- Cotejar T2M de POWER con la extracción directa de Giovanni y estudiar las diferencias entre el `RX5Day` oficial mensual y el índice anual derivado de POWER antes de presentar comparaciones de extremos.
- Revisar sensibilidad a rezagos, años influyentes, controles ENSO/PDO y pruebas múltiples antes de etiquetar hallazgos como robustos. Un intervalo que incluye cero no demuestra ausencia de cambio.
- Si se quiere un chat con preguntas abiertas, conectar un servicio de IA mediante una API que reciba únicamente la selección, las estadísticas y la procedencia de la variable visible, y verifique que cada respuesta cite esos datos. El chat actual sólo da explicaciones locales predefinidas.

Los scripts Python en `scripts/` y los archivos originales en `data/raw/` se conservan para reproducibilidad. La cartografía local y sus atribuciones están en `public/assets/`.
