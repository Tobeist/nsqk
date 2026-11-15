"""Check the regional audit inputs, family correction, and paired contrasts."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
from statsmodels.stats.multitest import multipletests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
# The full historical audit needs requirements.txt (matplotlib, shapely, ...), not the API's requirements-analysis.txt.
try:
    import audit_regions as audit  # noqa: E402
    MISSING = None
except ModuleNotFoundError as error:
    MISSING = error.name



@unittest.skipIf(MISSING, f"requiere requirements.txt (falta {MISSING})")
class RegionalAuditTest(unittest.TestCase):
    def test_input_scope_and_provenance(self):
        data, hashes = audit.load_inputs()
        self.assertEqual(set(data), set(audit.REGIONS))
        self.assertEqual(len(hashes), 24)  # four series and four metadata files per box
        for region in audit.REGIONS:
            self.assertEqual(set(data[region]), {"t2m", "gpcp", "rx5d", "Rx5day"})
            for key, values in data[region].items():
                self.assertEqual(len(values), 33 if key == "Rx5day" else 396)
                self.assertTrue(np.isfinite(values).all())
        info = json.loads((audit.OUT / "run_info.json").read_text(encoding="utf-8"))
        self.assertEqual(info["hash_policy"], audit.HASH_POLICY)
        self.assertEqual(info["plan_sha256"], audit.sha256(audit.PLAN))
        self.assertEqual(info["script_sha256"], audit.sha256(Path(audit.__file__)))
        for name, digest in info["input_sha256"].items():
            self.assertEqual(digest, audit.sha256(ROOT / name))

    def test_provenance_hash_ignores_only_checkout_line_endings(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "series.csv"
            path.write_bytes(b"date,value\n1992-01-01,1.25\n")
            expected = audit.sha256(path)
            path.write_bytes(b"date,value\r\n1992-01-01,1.25\r\n")
            self.assertEqual(audit.sha256(path), expected)
            path.write_bytes(b"date,value\r\n1992-01-01,1.26\r\n")
            self.assertNotEqual(audit.sha256(path), expected)
            path.write_bytes(b"date,value\r\n1992-01-01,1.25 \r\n")
            self.assertNotEqual(audit.sha256(path), expected)

    def test_family_corrections_and_direct_slope_identity(self):
        trends = pd.read_csv(audit.OUT / "trends.csv")
        pairs = pd.read_csv(audit.OUT / "pairwise_differences.csv")
        self.assertEqual(len(trends), 12)
        self.assertEqual(len(pairs), 12)
        for frame, mask in ((trends, trends.variable != "Rx5day"),
                            (trends, trends.variable == "Rx5day"),
                            (pairs, np.ones(len(pairs), dtype=bool))):
            expected = multipletests(frame.loc[mask, "p_bootstrap"], method="holm")[1]
            np.testing.assert_allclose(frame.loc[mask, "p_holm"], expected, atol=1e-12)
        slopes = trends.set_index(["region_id", "variable"]).slope_per_decade
        for row in pairs.itertuples():
            expected = slopes.loc[row.region_a, row.variable] - slopes.loc[row.region_b, row.variable]
            self.assertAlmostEqual(row.slope_per_decade, expected, places=9)
            self.assertEqual(row.status == "diferencia detectada", row.p_holm < 0.05)


if __name__ == "__main__":
    unittest.main()
