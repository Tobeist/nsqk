# Informe: Temperatura media a 2 m (NASA POWER, MERRA-2)

**Clasificación según las reglas del plan:** C — Evidencia insuficiente.

## Qué se estimó

Cambio lineal por década en la caja `[-101, 25, -99, 27]`, enero de 1992 a diciembre de 2024 (396 meses, 33 años), con efectos fijos por mes y covarianza HAC (Bartlett). Unidad: °C por década. Los intervalos son del 95 % **individuales**.

| Análisis | Pendiente [IC 95 % HAC normal] | IC 95 % bootstrap-t | p normal | p bootstrap-t | p Holm (bootstrap-t) |
| --- | --- | --- | ---: | ---: | ---: |
| M0 base, HAC12 (familia F1) | +0.271 [+0.0607, +0.48] | [+0.0239, +0.517] | 0.0115 | 0.0328 | 0.0984 |
| M1 con Niño 3.4 (L = 0), HAC12 (familia F2) | +0.267 [+0.0531, +0.481] | [+0.0112, +0.523] | 0.0144 | 0.044 | 0.132 |

Intervalo simultáneo de Bonferroni para M0 (F1): [+0.0143, +0.527].

## Sensibilidad (exploratoria, sin ajuste de p)

| Variante | Pendiente [IC 95 %] |
| --- | --- |
| M0 HAC6 | +0.271 [+0.0829, +0.458] |
| M0 HAC24 | +0.271 [+0.0423, +0.499] |
| M0 HAC12 con t | +0.271 [+0.0601, +0.481] |
| M0 bootstrap bloque 12 | +0.271 [+0.0541, +0.495] |
| M0 bootstrap bloque 24 | +0.271 [+0.0458, +0.5] |
| M0 bootstrap bloque 36 | +0.271 [+0.0702, +0.474] |
| Theil–Sen estacional | +0.299 [+0.144, +0.446] |
| M1 ENSO L = 3 | +0.265 [+0.0473, +0.484] |
| M1 ENSO L = 6 | +0.267 [+0.0524, +0.482] |
| M1S ENSO por estación | +0.256 [+0.0327, +0.479] |
| M0 1992–2010 | -0.0604 [-0.601, +0.48] |
| M0 2006–2024 | +0.65 [+0.199, +1.1] |
| M0 2000–2024 | +0.375 [+0.0834, +0.667] |
| M1 L0 1992–2010 | -0.162 [-0.678, +0.354] |
| M1 L0 2006–2024 | +0.69 [+0.217, +1.16] |
| M1 L0 2000–2024 | +0.395 [+0.103, +0.688] |

## Validez de p e intervalos

El IC HAC nominal del 95 % cubre en realidad 90.0% bajo el AR estimado de los residuos de M1. Holm y la clasificación usan los p del bootstrap-t con criba AR (plan v3); las sensibilidades están en `uncertainty_validation.csv`.

## ENSO

β cambia de +0.271 a +0.267 °C/década al incluir Niño 3.4 (diferencia -0.00329); el error estándar HAC se multiplica por 1.02. Coeficiente de Niño 3.4: -0.192 [-0.398, +0.0139] °C/°C (p = 0.0676). Correlación del tiempo con Niño 3.4: -0.02; VIF del tiempo: 1.00.

Por estación (L = 0): DJF -0.308 [-0.616, -0.000452]; MAM -0.9 [-1.37, -0.433]; JJA +0.325 [-0.0922, +0.743]; SON +0.00538 [-0.26, +0.271]. Prueba de igualdad entre estaciones: p = 0.00096.

## Diagnósticos

Ljung–Box p (12/24 rezagos) en M0: 5.58e-14 / 4.13e-13; Breusch–Pagan p = 0.00196; varianza por mes (Levene) p = 0.00109; Jarque–Bera p = 0.583 (asimetría 0.09); Cook máximo 0.0279 en 2021-12 (24 meses > 4/n); CUSUM p = 0.329. Al omitir un año completo la pendiente va de +0.219 (sin 2024) a +0.313 (sin 1994); el resultado completo se conserva como principal.

Rupturas y linealidad (Wald HAC12): término cuadrático  p = 0.139; cambio de nivel y pendiente en 2001-01 p = 0.0425 (Holm 0.128); cambio de nivel y pendiente en 2008-01 p = 0.146 (Holm 0.293); cambio de nivel y pendiente en 2011-01 p = 0.188 (Holm 0.293).

Razón de errores estándar bootstrap(12)/HAC(12): 1.05.

## Qué se puede concluir

- La estimación central es un aumento de 0.271 °C por década, pero la corrección de Holm sobre las tres variables no establece el signo (el IC bootstrap-t individual de M1 sí excluye cero).
- Un intervalo que contiene cero indica evidencia insuficiente bajo este análisis; no prueba que no haya cambio.

Criterios del plan (verdadero = se cumple): F1_holm_lt_0.05: False; F2_holm_lt_0.05: False; M1_L0_boot_t_ci_excludes_0: True; boot12_ci_excludes_0: True; hac6_hac12_hac24_exclude_0: True; same_sign_W1_W2_W3: False; ruptura (Holm < 0.01): False; razón SE en [0.67, 1.5]: True.

## Qué no se puede concluir

- No se puede atribuir el cambio a causas antropogénicas: no se hizo detección y atribución.
- La pendiente con ENSO es una asociación condicionada a un índice y a un rezago; no elimina otras fuentes de variabilidad ni prueba causalidad.
- La caja es un área de 2°×2°; no representa un estado completo ni la región Norte-Noreste (ver `spatial_audit.json`).
- Treinta y tres años no separan por completo una tendencia de la variabilidad de varias décadas (ver `ventanas_moviles.png`).
- Los valores p no son probabilidades de que la tendencia sea real; las ventanas, los rezagos y los HAC alternativos son exploratorios sin ajuste de multiplicidad.
