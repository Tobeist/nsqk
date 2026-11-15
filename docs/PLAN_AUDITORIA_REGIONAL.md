# Plan de extensión de la auditoría a tres cajas

**Fijado antes de calcular los resultados de Chihuahua y sur.** La auditoría del noreste ya se conocía al escribir este plan: esta extensión es exploratoria y no convierte los hallazgos previos en confirmatorios.

## Preguntas y datos

- Ventana fija: enero de 1992 a diciembre de 2024. Cajas: noreste `[-101,25,-99,27]`, Chihuahua interior `[-107,28,-105,30]` y sur `[-94,16,-92,18]`.
- Series primarias, en la misma definición y producto para las tres cajas: T2M mensual de POWER, GPCP mensual y RX5Day mensual de Giovanni, y Rx5day anual derivado de POWER diario UTC. El último índice no es intercambiable con RX5Day mensual.
- El CSV anual usado por la app redondea a cuatro decimales. El p e IC ya publicados para el noreste proceden de la serie diaria con más precisión; se conserva esa inferencia previa y se admite una diferencia numérica de hasta `1e-6` mm/década al verificar la pendiente contra el CSV procesado.
- Verificar `region_id`, caja, cobertura consecutiva, unidades, valores finitos y procedencia de cada entrada antes de estimar. Registrar SHA-256 de archivos procesados y del plan.

## Modelos e incertidumbre

- Series mensuales: M0 = tiempo lineal + once indicadores de mes; M1 = M0 + Niño 3.4 contemporáneo, como la auditoría del noreste. Pendiente por década, HAC(12). M0 se informa para comparar con la app; M1 es el modelo primario de la extensión.
- Rx5day anual: intercepto + tiempo lineal, HAC(2), como la auditoría previa. La app emplea HAC(3); ambas estimaciones de pendiente deben coincidir, pero los intervalos pueden diferir.
- Para los p e intervalos primarios: bootstrap-t de criba AR bajo la nula sin tendencia, orden 0–12 mensual u 0–3 anual elegido por AIC, innovaciones remuestreadas y escaladas por mes para las series mensuales; 4 999 réplicas y semilla 20261114. Conservar la cobertura estimada del IC HAC nominal. Repetir con AR(1) y con innovaciones gaussianas como sensibilidad, 999 réplicas cada una.
- Corregir con Holm la familia **F2-regional** de nueve p M1 (tres variables × tres cajas) y la familia **B-regional** de tres p del Rx5day anual. Los p del noreste proceden de la auditoría publicada; la ampliación de las familias se decidió después de conocerlos y se etiqueta exploratoria.

## Comparación directa entre cajas

Para cada una de las cuatro series, calcular las tres diferencias mensuales o anuales emparejadas: Chihuahua − noreste, sur − noreste y sur − Chihuahua. Ajustar la misma regresión a la **serie de diferencias** y probar si su pendiente es cero con el mismo bootstrap-t de criba AR. Así se conserva la covariación temporal entre cajas. Corregir los doce p con Holm como familia **D-regional**. Un p de una caja y otro p de otra caja no son una prueba de diferencia.

## Sensibilidad y lectura

- Informar la pendiente en ventanas predefinidas W1 = 1992–2010, W2 = 2006–2024 y W3 = 2000–2024, sin elegir la ventana más favorable. Informar HAC mensual con 6, 12 y 24 rezagos, y anual con 1, 2 y 3.
- Comparar, de forma exploratoria, línea frente a escalones en 2001 y 2011 (inicio documentado de corrientes de MERRA-2) mediante AIC descriptivo y prueba HAC del escalón. Un escalón con p individual < 0.05 y ΔAIC ≤ 0 deja el hallazgo **pendiente**, sin atribuir el salto al procesamiento.
- Estado por caja/serie: **inconcluso** si el p Holm de su familia no es < 0.05; **pendiente** si lo es pero aparece el escalón anterior; **sensible** si lo es pero cambia de signo entre ventanas o alguna variante de bootstrap pierde el umbral; **sustentado dentro de este protocolo** si pasa esas comprobaciones. Estos estados no implican atribución causal ni representatividad estatal.
- Las diferencias regionales se describen por su estimación, IC, p corregido y límites espaciales; no se infieren de signos, intervalos separados ni categorías de las cajas.

Salidas separadas en `analysis/regions/`. No modificar `analysis/results/final_status.*` ni habilitar conclusiones auditadas nuevas en la interfaz hasta revisar esta extensión.
