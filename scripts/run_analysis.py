"""Run the full reproducible analysis in order. Usage: python scripts/run_analysis.py"""

import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
STEPS = ["trend_audit.py", "grouping_audit.py", "uncertainty_validation.py", "rain_reconciliation.py", "form_of_change.py",
         "simulation_study.py", "forecast_experiment.py"]

if __name__ == "__main__":
    for step in STEPS:
        print(f"== {step}", flush=True)
        subprocess.run([sys.executable, str(SCRIPTS / step)], check=True)
    subprocess.run([sys.executable, "-m", "unittest", "tests/test_trend_lib.py", "tests/test_v2_procedures.py"],
                   check=True, cwd=SCRIPTS.parent)
    import hashlib
    import json
    import platform
    from importlib.metadata import version
    root = SCRIPTS.parent
    info = {"command": "python scripts/run_analysis.py", "seed": 20261114, "python": platform.python_version(),
            "packages": {p: version(p) for p in ("numpy", "scipy", "pandas", "statsmodels", "matplotlib", "shapely", "prophet", "optuna", "scikit-learn")},
            "plan_sha256": {p: hashlib.sha256((root / "docs" / p).read_bytes()).hexdigest() for p in ("ANALISIS_TENDENCIAS_PLAN.md", "ANALISIS_TENDENCIAS_PLAN_V2.md", "ANALISIS_TENDENCIAS_PLAN_V3.md")},
            "daily_inputs_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((root / "data/external/power_daily_t2m/raw").glob("*.csv"))}}
    (root / "analysis/results/run_info_v2.json").write_text(json.dumps(info, indent=1) + "\n", encoding="utf-8")
