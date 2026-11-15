# Extensión de la auditoría a tres cajas

Plan fijado antes de calcular Chihuahua y sur: [protocolo](../../docs/PLAN_AUDITORIA_REGIONAL.md). El noreste ya se conocía: esta ampliación es exploratoria. Datos y métodos no implican causalidad ni cobertura de estados completos.

Las pendientes mensuales primarias usan calendario + Niño 3.4 (M1), HAC(12), p e IC bootstrap-t de criba AR. Rx5day anual usa HAC(2). Holm se aplica a las nueve pruebas mensuales y a las tres anuales por separado. La app integra seis variables mensuales por caja (18 pruebas) y el índice anual (tres pruebas), con HAC(12) mensual y HAC(2) anual. Esta auditoría regional tiene un alcance mensual menor (nueve pruebas); sus p de Holm no son intercambiables con los de la app ni con la auditoría original de tres pruebas mensuales.

| Caja | Serie | Pendiente [IC bootstrap-t 95 %] por década | p Holm | Estado |
| --- | --- | --- | ---: | --- |
| mx-northeast | t2m | +0.267 [+0.011, +0.523] °C | 0.264 | inconcluso |
| mx-northeast | gpcp | +0.101 [-0.032, +0.233] mm/día | 0.615 | inconcluso |
| mx-northeast | rx5d | +0.855 [-2.825, +4.535] mm/5 días | 1.000 | inconcluso |
| mx-northeast | Rx5day | +15.964 [+5.091, +26.837] mm | 0.020 | pendiente |
| mx-chihuahua-interior | t2m | +0.493 [+0.226, +0.759] °C | 0.011 | pendiente |
| mx-chihuahua-interior | gpcp | +0.014 [-0.097, +0.126] mm/día | 1.000 | inconcluso |
| mx-chihuahua-interior | rx5d | +2.952 [+0.278, +5.626] mm/5 días | 0.224 | inconcluso |
| mx-chihuahua-interior | Rx5day | +0.438 [-5.032, +5.909] mm | 0.871 | inconcluso |
| mx-south-humid | t2m | +0.324 [+0.074, +0.575] °C | 0.106 | inconcluso |
| mx-south-humid | gpcp | -0.127 [-0.321, +0.068] mm/día | 0.776 | inconcluso |
| mx-south-humid | rx5d | -3.586 [-10.163, +2.990] mm/5 días | 0.821 | inconcluso |
| mx-south-humid | Rx5day | +7.238 [-9.650, +24.126] mm | 0.774 | inconcluso |

## Diferencias directas de pendientes

Se ajustó la serie emparejada de diferencias con el mismo modelo. Los doce p se corrigieron juntos con Holm; no se compararon valores p de cajas aisladas.

| Serie | Diferencia | Pendiente [IC bootstrap-t 95 %] por década | p Holm | Estado |
| --- | --- | --- | ---: | --- |
| t2m | mx-chihuahua-interior − mx-northeast | +0.225 [+0.060, +0.390] °C | 0.112 | inconcluso |
| t2m | mx-south-humid − mx-northeast | +0.057 [-0.082, +0.197] °C | 1.000 | inconcluso |
| t2m | mx-south-humid − mx-chihuahua-interior | -0.168 [-0.326, -0.011] °C | 0.344 | inconcluso |
| gpcp | mx-chihuahua-interior − mx-northeast | -0.087 [-0.229, +0.055] mm/día | 1.000 | inconcluso |
| gpcp | mx-south-humid − mx-northeast | -0.228 [-0.394, -0.061] mm/día | 0.106 | inconcluso |
| gpcp | mx-south-humid − mx-chihuahua-interior | -0.141 [-0.340, +0.058] mm/día | 1.000 | inconcluso |
| rx5d | mx-chihuahua-interior − mx-northeast | +2.097 [-2.731, +6.925] mm/5 días | 1.000 | inconcluso |
| rx5d | mx-south-humid − mx-northeast | -4.441 [-11.262, +2.380] mm/5 días | 1.000 | inconcluso |
| rx5d | mx-south-humid − mx-chihuahua-interior | -6.538 [-13.950, +0.874] mm/5 días | 0.670 | inconcluso |
| Rx5day | mx-chihuahua-interior − mx-northeast | -15.526 [-28.307, -2.745] mm | 0.212 | inconcluso |
| Rx5day | mx-south-humid − mx-northeast | -8.726 [-27.365, +9.913] mm | 1.000 | inconcluso |
| Rx5day | mx-south-humid − mx-chihuahua-interior | +6.800 [-11.600, +25.199] mm | 1.000 | inconcluso |

## Lectura de las comprobaciones

- **mx-northeast, Rx5day: pendiente.** p Holm 0.020; escalón candidato HS(2001-01) que ajusta igual o mejor.
- **mx-chihuahua-interior, t2m: pendiente.** p Holm 0.011; escalón candidato HS(2011-01) que ajusta igual o mejor; la pendiente cambia de signo entre ventanas predefinidas.
- Diferencias directas entre cajas que superan Holm: **0 de 12**. Esto no demuestra que todas las pendientes sean iguales.

## Límites

Los IC de la tabla son individuales; el p Holm evalúa la familia completa. Un IC individual que excluye cero puede coexistir con p Holm ≥ 0.05. Las pruebas de escalón en 2001 y 2011 son exploratorias y su p no se corrigió. Las cajas, celdas y máscaras efectivas de POWER y Giovanni difieren. El índice anual derivado de POWER no es el RX5Day mensual de Giovanni.

Archivos detallados: `trends.csv`, `pairwise_differences.csv`, `sensitivities.csv`, `windows.csv`, `hac_lags.csv`, `step_models.csv` y `run_info.json`.
