#!/usr/bin/env python3
"""Fast host QA: no root, no HWC build, no boot/vbmeta/DTBO writes."""
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import zipfile

SCRIPT = Path(__file__).with_name("package-op6-hdr-addon.sh")
ELF_PATH = "system/vendor/bin/hw/vendor.qti.hardware.display.composer-service"


def fake_test_elf():
    # Intentionally INVALID executable other than the AArch64 ELF header; never
    # shipped to users. Tests only the ZIP integrity gate.
    b = bytearray(64)
    b[:6] = b"\x7fELF\x02\x01"
    b[18:20] = (183).to_bytes(2, "little")
    return bytes(b)


class HdrAk3Contract(unittest.TestCase):
    def run_bundler(self, folder, archive=None, archive_sha="", elf_sha=""):
        env = dict(os.environ)
        env.update(OP6_HDR_AK3_OUT=str(folder / "out"),
                   OP6_HDR_COMPANION_ZIP=str(archive) if archive else "",
                   OP6_HDR_COMPANION_SHA256=archive_sha,
                   OP6_HDR_COMPANION_ELF_SHA256=elf_sha)
        return subprocess.run(["sh", str(SCRIPT)], env=env,
                              capture_output=True, text=True)

    def test_default_passive(self):
        with tempfile.TemporaryDirectory() as root:
            dir = Path(root)
            result = self.run_bundler(dir)
            self.assertEqual(result.returncode, 0, result.stderr)
            output = dir / "out"
            self.assertTrue((output / "README.zh-CN.txt").is_file())
            self.assertIn("automatic_install=no",
                          (output / "COMPONENT_INFO.txt").read_text())
            self.assertEqual({f.name for f in output.iterdir()},
                             {"README.zh-CN.txt", "COMPONENT_INFO.txt"})

    def test_fail_closed_on_partial_or_mismatch(self):
        with tempfile.TemporaryDirectory() as root:
            dir = Path(root)
            self.assertNotEqual(self.run_bundler(dir, archive_sha="a" * 64).returncode, 0)
            archive = dir / "test.zip"
            elf = fake_test_elf()
            with zipfile.ZipFile(archive, "w") as z:
                z.writestr("module.prop", "id=op6-native-hdr\nname=Test Only\n")
                z.writestr(ELF_PATH, elf)
            result = self.run_bundler(dir, archive,
                                      archive_sha="0" * 64,
                                      elf_sha=hashlib.sha256(elf).hexdigest())
            self.assertNotEqual(result.returncode, 0)

    def test_fingerprint_contract_accepts_synthetic_fixture_only(self):
        with tempfile.TemporaryDirectory() as root:
            dir = Path(root)
            elf = fake_test_elf()
            archive = dir / "test.zip"
            with zipfile.ZipFile(archive, "w") as z:
                z.writestr("module.prop", "id=op6-native-hdr\nname=Test Only\n")
                z.writestr(ELF_PATH, elf)
            result = self.run_bundler(dir, archive,
                                      hashlib.sha256(archive.read_bytes()).hexdigest(),
                                      hashlib.sha256(elf).hexdigest())
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((dir / "out" /
                             "Op6NativeHDR-KSU-COMPANION-UNVERIFIED.zip").is_file())
            self.assertIn("NOT automatically", result.stdout)

    def test_boot_installer_unchanged(self):
        pack = SCRIPT.with_name("package-ak3.sh").read_text()
        self.assertIn("dump_boot;", pack)
        self.assertIn("write_boot;", pack)
        self.assertIn("do.systemless=0", pack)
        self.assertIn("op6-hdr/COMPONENT_INFO.txt", pack)
        # No implicit vendor partition flash or blind kernel module insertion.
        for forbidden in ("dd if=", "insmod ", "flash dtbo", "setprop "):
            self.assertNotIn(forbidden, pack)


if __name__ == "__main__":
    unittest.main()
