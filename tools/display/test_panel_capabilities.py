"""OnePlus 6 panel invariants; do not transplant a 6T timing or invent VRR."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
DTS = ROOT / "arch/arm64/boot/dts/qcom"
PANEL = DTS / "dsi-panel-samsung_sofef00_m_cmd.dtsi"


class PanelCapabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.panel = PANEL.read_text()
        cls.device = (DTS / "enchilada.dtsi").read_text()

    def test_default_enchilada_panel_is_2280(self):
        self.assertIn("qcom,dsi-default-panel = <&dsi_samsung_sofef00_m_cmd>;", self.device)
        self.assertRegex(self.panel, r"qcom,mdss-dsi-panel-width\s*=\s*<1080>")
        self.assertRegex(self.panel, r"qcom,mdss-dsi-panel-height\s*=\s*<2280>")

    def test_only_validated_single_60hz_timing(self):
        rates = re.findall(r"qcom,mdss-dsi-panel-framerate\s*=\s*<(\d+)>", self.panel)
        self.assertEqual(rates, ["60"])
        self.assertIn("qcom,mdss-dsi-bpp = <24>;", self.panel)

    def test_hdr_metadata_and_p3_commands_exist(self):
        for token in (
            "qcom,mdss-dsi-panel-hdr-enabled;",
            "qcom,mdss-dsi-panel-hdr-color-primaries",
            "qcom,mdss-dsi-panel-peak-brightness",
            "qcom,mdss-dsi-panel-display-srgb-color-mode-on-command",
            "qcom,mdss-dsi-panel-display-p3-mode-on-command",
        ):
            self.assertIn(token, self.panel)

    def test_device_probe_has_no_mutations(self):
        script = (ROOT / "tools/display/enchilada_display_probe.sh").read_text()
        for mutation in ("settings put ", "setprop ", "wm density ", "wm size ",
                         "mount -o ", "echo 90 > ", "adb sideload"):
            self.assertNotIn(mutation, script)
        self.assertIn("dumpsys SurfaceFlinger", script)
        self.assertIn("dumpsys display", script)


if __name__ == "__main__":
    unittest.main()
