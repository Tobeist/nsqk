"""Single final output: analysis/results/final_status.csv and SUMMARY.md, built only from the files the other steps wrote.

Usage: python scripts/final_summary.py (run last; scripts/run_analysis.py does it).
"""

import json

import pandas as pd

import trend_audit as ta

MONTHLY_STATUS = {"A": "sustentado", "B": "sensible", "C": "inconcluso", "D": "no evaluable"}
EXTREME_STATUS = {"consistente": "sustentado", "sensible a decisiones": "sensible", "inconcluso": "inconcluso"}


def step_flag(form, series):
    """A documented-date step that fits at least as well as the line (ΔAIC <= 0) with p < 0.05 (plan v3, section 3)."""
    steps = form[(form.series == series) & form.model.str.startswith("HS(") & (form.delta_aic_vs_HL <= 0) & (form.step_p < 0.05)]
    return ", ".join(f"{m[3:-1]} ({s:+.3g})" for m, s in zip(steps.model, steps.step))


def main():
    r = ta.OUT
    trends = pd.read_csv(r / "trend_results.csv")
    classes = json.loads((r / "classification.json").read_text())
    extremes = pd.read_csv(r / "extremes_trends.csv")
    form = pd.read_csv(r / "form_of_change.csv")
    forecast = pd.read_csv(r / "forecast_summary.csv")
    rows = []
    for key, spec in ta.VARS.items():
        m1 = trends[(trends.variable == key) & (trends.window == "W0") & (trends.model == "M1_L0") & (trends.method == "HAC12")].iloc[0]
        m0 = trends[(trends.variable == key) & (trends.window == "W0") & (trends.model == "M0") & (trends.method == "HAC12")].iloc[0]
        flag = step_flag(form, key)
        rows.append({"result": f"Tendencia mensual: {spec['name']}", "unit": spec["unit"] + "/década",
                     "estimate": m1.slope_per_decade, "ci_low": m1.ci_boot_t_low, "ci_high": m1.ci_boot_t_high, "ci_method": "bootstrap-t (criba AR)",
                     "p_bootstrap": m1.p_value_bootstrap, "p_holm": m1.p_holm, "family": "F2 (M1)", "p_holm_M0": m0.p_holm,
                     "rule_class": classes[key]["class"], "status": MONTHLY_STATUS[classes[key]["class"]],
                     "note": "; ".join(x for x in (f"IC individual {'sin' if m1.ci_boot_t_low > 0 or m1.ci_boot_t_high < 0 else 'con'} cero",
                                                     f"escalón documentado que ajusta igual: {flag}" if flag else "") if x)})
    for _, e in extremes.iterrows():
        flag = step_flag(form, e["index"])
        status = EXTREME_STATUS[e["class"]]
        if flag and status == "sustentado":
            status = "pendiente"
        rows.append({"result": f"Extremo anual {e['index']} (POWER diario)", "unit": {"TX90p": "% de días", "CDD": "días", "Rx5day": "mm"}[e["index"]] + "/década",
                     "estimate": e.slope_per_decade, "ci_low": e.ci_boot_t_low, "ci_high": e.ci_boot_t_high, "ci_method": "bootstrap-t (criba AR)",
                     "p_bootstrap": e.p_bootstrap_t, "p_holm": e.p_holm_family_B, "family": "B", "rule_class": e["class"], "status": status,
                     "note": f"escalón documentado que ajusta igual: {flag}; falta un producto diario independiente de MERRA-2" if flag else ""})
    for key in ta.VARS:
        f = forecast[forecast.variable == key]
        winners = f[f.operational & f.model.str.contains("PROPHET|MLP") & f.consistent_vs_clim & f.consistent_vs_ols_trend]
        rows.append({"result": f"Predicción mensual a 12 meses: {key}", "unit": "MAE",
                     "estimate": None, "status": "pendiente" if len(winners) else "sustentado",
                     "note": ("mejora pequeña de " + ", ".join(f"{m} (habilidad {s:+.1%} externa, {h:+.1%} reservado)" for m, s, h in
                                                             zip(winners.model, winners.skill_vs_clim_outer, winners.skill_vs_clim_holdout))
                              + "; no se adopta") if len(winners) else "ningún modelo complejo mejora de forma consistente; se mantiene el más simple"})
    out = pd.DataFrame(rows)
    out.to_csv(r / "final_status.csv", index=False)
    lines = ["# Resumen final", "",
             "Salida única generada por `scripts/final_summary.py` a partir de las tablas de esta carpeta. Valores p de Holm sobre bootstrap-t con criba AR "
             "(plan v3); intervalos bootstrap-t del 95 % individuales. Estados: sustentado, sensible, inconcluso (evidencia insuficiente, no ausencia de cambio), "
             "pendiente (pasa las pruebas, pero un escalón en una fecha de cambio de procesamiento documentada lo explica igual) y no evaluable.", "",
             "| Resultado | Estimación [IC 95 %] | p Holm | Estado | Nota |", "| --- | --- | ---: | --- | --- |"]
    for x in rows:
        est = f"{x['estimate']:+.3g} [{x['ci_low']:+.3g}, {x['ci_high']:+.3g}] {x['unit']}" if x["estimate"] is not None else "—"
        ph = f"{x['p_holm']:.3g}" if x.get("p_holm") is not None else "—"
        lines.append(f"| {x['result']} | {est} | {ph} | **{x['status']}** | {x['note']} |")
    lines += ["", "Informe metodológico: `docs/INFORME_TENDENCIAS.md`. Informes por variable: " + ", ".join(f"[{k}](informe_{k}.md)" for k in ta.VARS) + "."]
    (r / "SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
