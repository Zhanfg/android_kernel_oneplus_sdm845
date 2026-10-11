#!/usr/bin/env python3
import tempfile
import unittest
from pathlib import Path
from OP6_Residency_Analyze_v03 import parse


def sample(neg=False, missing=False):
    s=["META|format|op6-v03-residency-1","META|device|OnePlus6","META|kernel|4.19.325"]
    for phase in ("IDLE", "ACTIVE", "RECOVERY"):
        s += [f"PHASE_START|{phase}|100", f"TIS|{phase}|START|0|576000|1000", f"TIS|{phase}|START|0|1766400|2000",
              f"TIS|{phase}|START|4|825600|1500", f"TIS|{phase}|START|4|2803200|2500",
              f"PSI|{phase}|START|cpu|some|1000000", f"PSI|{phase}|START|io|some|40000",
              f"PSI|{phase}|START|memory|some|10", f"SAMPLE|{phase}|1|110|576000|825600|257000000|0_%|55500|378|10000|2500000"]
        if not missing:
            s += [f"TIS|{phase}|END|0|576000|{900 if neg else 1100}", f"TIS|{phase}|END|0|1766400|2050",
                  f"TIS|{phase}|END|4|825600|1650", f"TIS|{phase}|END|4|2803200|2550"]
        s += [f"PSI|{phase}|END|cpu|some|1200000", f"PSI|{phase}|END|io|some|40040",
              f"PSI|{phase}|END|memory|some|11", f"PHASE_END|{phase}|120"]
    return "\n".join(s+["GFX|START|12345|200|20","GFX|END|12345|300|25","COMPLETE|120",""])


class TestParser(unittest.TestCase):
    def parse_one(self, text):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"op6.txt";p.write_text(text)
            return parse(p)

    def test_summary(self):
        x=self.parse_one(sample())["phases"][0]
        self.assertEqual(x["little_high_residency_pct"], 33.33)
        self.assertEqual(x["big_high_residency_pct"], 25.0)
        self.assertEqual(x["cpu_some_psi_pct"], 1.0)
        self.assertEqual(x["io_some_psi_pct"], 0.0)
        self.assertEqual(x["cpu_thermal_max_raw"], 55500)
        self.assertEqual(self.parse_one(sample())["phases"][1]["gfx_jank_pct"], 5.0)

    def test_reject_truncated(self):
        with self.assertRaises(ValueError):
            self.parse_one(sample().replace("COMPLETE|120", ""))

    def test_counter_reset_is_invalid(self):
        x=self.parse_one(sample(neg=True))["phases"][0]
        self.assertIsNone(x["little_high_residency_pct"])
        self.assertIn("counters went backward", "; ".join(x["warnings"]))

    def test_missing_residency_is_invalid(self):
        x=self.parse_one(sample(missing=True))["phases"][0]
        self.assertIsNone(x["big_high_residency_pct"])

    def test_gfx_app_change_invalid(self):
        x=self.parse_one(sample().replace("GFX|END|12345", "GFX|END|98765"))["phases"][1]
        self.assertIsNone(x["gfx_jank_pct"])
        self.assertIn("app changed", "; ".join(x["warnings"]))

    def test_invalid_format(self):
        with self.assertRaises(ValueError):
            self.parse_one(sample().replace("op6-v03-residency-1","unknown"))


if __name__ == "__main__":
    unittest.main()