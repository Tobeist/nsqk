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

La interfaz permite analizar **una caja de estudio** en el noreste de México (`[-101, 25, -99, 27]`). Se pueden elegir años completos entre **1992 y 2024**, con un mínimo de diez años. Las variables habilitadas son temperatura media a 2 m de NASA POWER, precipitación media GPCP y el índice mensual `RX5Day` de Giovanni. Los resultados JSON en `data/results/` contienen 396 meses por variable. Al pulsar **Analizar selección**, la app filtra esos meses y recalcula las medias anuales, la pendiente y el intervalo del 95 % con el modelo mensual de estacionalidad y HAC(12). La gráfica muestra los resúmenes anuales del periodo elegido.

Otras regiones y las variables sin archivos procesados están deshabilitadas. La caja no equivale a toda la región Norte-Noreste ni a los cinco polígonos regionales propuestos. Las diferencias de malla y procesamiento entre POWER, GPCP y MERRA-2 se explican en la metodología. Comparar muchos periodos y elegir el más llamativo aumenta el riesgo de interpretar una señal casual como robusta.

La sección de preguntas ofrece respuestas locales deterministas basadas en el resultado visible; **no consulta un modelo de IA**. Las fixtures sintéticas y la ruta `/demo` fueron retiradas del MVP.

## Qué falta para ampliar el producto

- Agregar nuevas regiones con polígonos, máscara y pesos espaciales definidos, y descargar o procesar las mismas variables para cada una. No reutilizar la serie de esta caja en otra región.
- Descargar y validar los índices de calor, `R95P` y FLDAS. Habilitar una variable únicamente cuando existan su serie, unidades, procedencia y análisis reproducible.
- Cotejar T2M de POWER con la extracción directa de Giovanni y estudiar las diferencias entre el `RX5Day` oficial mensual y el índice anual derivado de POWER antes de presentar comparaciones de extremos.
- Revisar sensibilidad a rezagos, años influyentes, controles ENSO/PDO y pruebas múltiples antes de etiquetar hallazgos como robustos. Un intervalo que incluye cero no demuestra ausencia de cambio.
- Si se quiere un chat con preguntas abiertas, conectar un servicio de IA mediante una API que reciba únicamente la selección, las estadísticas y la procedencia de la variable visible, y verifique que cada respuesta cite esos datos. El chat actual sólo da explicaciones locales predefinidas.

Los scripts Python en `scripts/` y los archivos originales en `data/raw/` se conservan para reproducibilidad. La cartografía local y sus atribuciones están en `public/assets/`.
