# Informe: Precipitación media (GPCP satélite + pluviómetros, Giovanni)

**Clasificación según las reglas del plan:** C — Evidencia insuficiente.

## Qué se estimó

Cambio lineal por década en la caja `[-101, 25, -99, 27]`, enero de 1992 a diciembre de 2024 (396 meses, 33 años), con efectos fijos por mes y covarianza HAC (Bartlett). Unidad: mm/día por década. Los intervalos son del 95 % **individuales**.

| Análisis | Pendiente [IC 95 %] | p original | p Holm |
| --- | --- | ---: | ---: |
| M0 base, HAC12 (familia F1) | +0.0985 [-0.0258, +0.223] | 0.121 | 0.241 |
| M1 con Niño 3.4 (L = 0), HAC12 (familia F2) | +0.101 [-0.0164, +0.218] | 0.0917 | 0.183 |

Intervalo simultáneo de Bonferroni para M0 (F1): [-0.0534, +0.25].

## Sensibilidad (exploratoria, sin ajuste de p)

| Variante | Pendiente [IC 95 %] |
| --- | --- |
| M0 HAC6 | +0.0985 [-0.0267, +0.224] |
| M0 HAC24 | +0.0985 [-0.0358, +0.233] |
| M0 HAC12 con t | +0.0985 [-0.0262, +0.223] |
| M0 bootstrap bloque 12 | +0.0985 [-0.0343, +0.229] |
| M0 bootstrap bloque 24 | +0.0985 [-0.0358, +0.235] |
| M0 bootstrap bloque 36 | +0.0985 [-0.0406, +0.237] |
| Theil–Sen estacional | +0.0761 [+0.0111, +0.142] |
| M1 ENSO L = 3 | +0.103 [-0.0109, +0.218] |
| M1 ENSO L = 6 | +0.106 [-0.00715, +0.219] |
| M1S ENSO por estación | +0.107 [-0.0105, +0.224] |
| M0 1992–2010 | +0.396 [+0.0965, +0.695] |
| M0 2006–2024 | -0.0572 [-0.372, +0.257] |
| M0 2000–2024 | -0.0525 [-0.253, +0.148] |
| M1 L0 1992–2010 | +0.454 [+0.163, +0.745] |
| M1 L0 2006–2024 | -0.0916 [-0.384, +0.201] |
| M1 L0 2000–2024 | -0.0694 [-0.245, +0.106] |
| M0 en % de la media mensual (unidad: %/década) | +6.15 [-3.12, +15.4] |

## Validez de p e intervalos

Los p de esta tabla usan la aproximación normal del HAC, que en simulaciones cubre alrededor del 90 % en lugar del 95 %. Los valores p válidos (bootstrap-t con criba AR estimada de los residuos), sus correcciones de Holm y la cobertura real están en `uncertainty_validation.csv` (plan v3).

## ENSO

β cambia de +0.0985 a +0.101 mm/día/década al incluir Niño 3.4 (diferencia +0.00248); el error estándar HAC se multiplica por 0.94. Coeficiente de Niño 3.4: +0.144 [-0.00433, +0.293] mm/día/°C (p = 0.0571). Correlación del tiempo con Niño 3.4: -0.02; VIF del tiempo: 1.00.

Por estación (L = 0): DJF +0.178 [+0.0189, +0.338]; MAM +0.466 [+0.201, +0.731]; JJA -0.581 [-0.949, -0.214]; SON +0.273 [+0.00546, +0.54]. Prueba de igualdad entre estaciones: p = 1.72e-05.

## Diagnósticos

Ljung–Box p (12/24 rezagos) en M0: 0.677 / 0.755; Breusch–Pagan p = 1.07e-11; varianza por mes (Levene) p = 1.5e-13; Jarque–Bera p = 2.21e-82 (asimetría 1.39); Cook máximo 0.0596 en 2010-07 (25 meses > 4/n); CUSUM p = 0.541. Al omitir un año completo la pendiente va de +0.0799 (sin 2024) a +0.132 (sin 2022); el resultado completo se conserva como principal.

Rupturas y linealidad (Wald HAC12): término cuadrático  p = 0.173; cambio de nivel y pendiente en 2001-01 p = 0.00544 (Holm 0.0163); cambio de nivel y pendiente en 2008-01 p = 0.18 (Holm 0.254); cambio de nivel y pendiente en 2011-01 p = 0.127 (Holm 0.254).

Razón de errores estándar bootstrap(12)/HAC(12): 1.08.

## Qué se puede concluir

- La estimación central es un aumento de 0.0985 mm/día por década, pero el intervalo y los ajustes por Holm no establecen el signo con estos datos.
- Un intervalo que contiene cero indica evidencia insuficiente bajo este análisis; no prueba que no haya cambio.

Criterios del plan (verdadero = se cumple): F1_holm_lt_0.05: False; F2_holm_lt_0.05: False; M1_L0_ci_excludes_0: False; boot12_ci_excludes_0: False; hac6_hac12_hac24_exclude_0: False; same_sign_W1_W2_W3: False; ruptura (Holm < 0.01): False; razón SE en [0.67, 1.5]: True.

## Qué no se puede concluir

- No se puede atribuir el cambio a causas antropogénicas: no se hizo detección y atribución.
- La pendiente con ENSO es una asociación condicionada a un índice y a un rezago; no elimina otras fuentes de variabilidad ni prueba causalidad.
- La caja es un área de 2°×2°; no representa un estado completo ni la región Norte-Noreste (ver `spatial_audit.json`).
- Treinta y tres años no separan por completo una tendencia de la variabilidad de varias décadas (ver `ventanas_moviles.png`).
- Los valores p no son probabilidades de que la tendencia sea real; las ventanas, los rezagos y los HAC alternativos son exploratorios sin ajuste de multiplicidad.
