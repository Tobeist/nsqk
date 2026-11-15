# Informe: RX5Day mensual (MERRA-2, Giovanni)

**Clasificación según las reglas del plan:** C — Evidencia insuficiente.

## Qué se estimó

Cambio lineal por década en la caja `[-101, 25, -99, 27]`, enero de 1992 a diciembre de 2024 (396 meses, 33 años), con efectos fijos por mes y covarianza HAC (Bartlett). Unidad: mm/5 días por década. Los intervalos son del 95 % **individuales**.

| Análisis | Pendiente [IC 95 %] | p original | p Holm |
| --- | --- | ---: | ---: |
| M0 base, HAC12 (familia F1) | +0.778 [-2.58, +4.14] | 0.65 | 0.65 |
| M1 con Niño 3.4 (L = 0), HAC12 (familia F2) | +0.855 [-2.43, +4.14] | 0.61 | 0.61 |

Intervalo simultáneo de Bonferroni para M0 (F1): [-3.33, +4.88].

## Sensibilidad (exploratoria, sin ajuste de p)

| Variante | Pendiente [IC 95 %] |
| --- | --- |
| M0 HAC6 | +0.778 [-2.6, +4.15] |
| M0 HAC24 | +0.778 [-2.59, +4.14] |
| M0 HAC12 con t | +0.778 [-2.59, +4.15] |
| M0 bootstrap bloque 12 | +0.778 [-2.81, +4.16] |
| M0 bootstrap bloque 24 | +0.778 [-3.16, +4.64] |
| M0 bootstrap bloque 36 | +0.778 [-3.06, +4.66] |
| Theil–Sen estacional | +0.324 [-1.38, +2.02] |
| M1 ENSO L = 3 | +0.908 [-2.26, +4.08] |
| M1 ENSO L = 6 | +0.986 [-2.11, +4.08] |
| M1S ENSO por estación | +0.935 [-2.33, +4.2] |
| M0 1992–2010 | +4.93 [-1.77, +11.6] |
| M0 2006–2024 | +3.24 [-5.37, +11.9] |
| M0 2000–2024 | -2.33 [-9.05, +4.39] |
| M1 L0 1992–2010 | +6.52 [-0.173, +13.2] |
| M1 L0 2006–2024 | +2.16 [-6.1, +10.4] |
| M1 L0 2000–2024 | -2.92 [-9.19, +3.35] |
| M0 en % de la media mensual (unidad: %/década) | +0.859 [-7.45, +9.17] |

## Validez de p e intervalos

Los p de esta tabla usan la aproximación normal del HAC, que en simulaciones cubre alrededor del 90 % en lugar del 95 %. Los valores p válidos (bootstrap-t con criba AR estimada de los residuos), sus correcciones de Holm y la cobertura real están en `uncertainty_validation.csv` (plan v3).

## ENSO

β cambia de +0.778 a +0.855 mm/5 días/década al incluir Niño 3.4 (diferencia +0.0772); el error estándar HAC se multiplica por 0.98. Coeficiente de Niño 3.4: +4.5 [+1.21, +7.8] mm/5 días/°C (p = 0.00739). Correlación del tiempo con Niño 3.4: -0.02; VIF del tiempo: 1.00.

Por estación (L = 0): DJF +3.18 [+0.977, +5.38]; MAM +10 [+2.79, +17.3]; JJA -11.5 [-21.3, -1.72]; SON +10.3 [+2.76, +17.9]. Prueba de igualdad entre estaciones: p = 0.000665.

## Diagnósticos

Ljung–Box p (12/24 rezagos) en M0: 0.0142 / 0.0325; Breusch–Pagan p = 0.00651; varianza por mes (Levene) p = 9.4e-07; Jarque–Bera p = 0 (asimetría 2.11); Cook máximo 0.136 en 2003-09 (21 meses > 4/n); CUSUM p = 0.846. Al omitir un año completo la pendiente va de +0.0257 (sin 2024) a +1.73 (sin 2022); el resultado completo se conserva como principal.

Rupturas y linealidad (Wald HAC12): término cuadrático  p = 0.588; cambio de nivel y pendiente en 2001-01 p = 0.361 (Holm 1); cambio de nivel y pendiente en 2008-01 p = 0.628 (Holm 1); cambio de nivel y pendiente en 2011-01 p = 0.341 (Holm 1).

Razón de errores estándar bootstrap(12)/HAC(12): 1.05.

## Qué se puede concluir

- La estimación central es un aumento de 0.778 mm/5 días por década, pero el intervalo y los ajustes por Holm no establecen el signo con estos datos.
- Un intervalo que contiene cero indica evidencia insuficiente bajo este análisis; no prueba que no haya cambio.

Criterios del plan (verdadero = se cumple): F1_holm_lt_0.05: False; F2_holm_lt_0.05: False; M1_L0_ci_excludes_0: False; boot12_ci_excludes_0: False; hac6_hac12_hac24_exclude_0: False; same_sign_W1_W2_W3: False; ruptura (Holm < 0.01): False; razón SE en [0.67, 1.5]: True.

## Qué no se puede concluir

- No se puede atribuir el cambio a causas antropogénicas: no se hizo detección y atribución.
- La pendiente con ENSO es una asociación condicionada a un índice y a un rezago; no elimina otras fuentes de variabilidad ni prueba causalidad.
- La caja es un área de 2°×2°; no representa un estado completo ni la región Norte-Noreste (ver `spatial_audit.json`).
- Treinta y tres años no separan por completo una tendencia de la variabilidad de varias décadas (ver `ventanas_moviles.png`).
- Los valores p no son probabilidades de que la tendencia sea real; las ventanas, los rezagos y los HAC alternativos son exploratorios sin ajuste de multiplicidad.
