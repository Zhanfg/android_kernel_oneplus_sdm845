import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location('check_port',ROOT/'tools/check_port.py')
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class TWRPPortTests(unittest.TestCase):
    def test_board(self):
        module.check_board(ROOT/'device/oneplus/enchilada/BoardConfig.mk')

    def test_explicit_layouts(self):
        dr=ROOT/'device/oneplus/enchilada/recovery/root/system/etc'
        physical=module.check_fstab(dr/'recovery-legacy.fstab','legacy')
        logical=module.check_fstab(dr/'recovery.fstab','retrofit')
        self.assertNotEqual(physical,logical)

    def test_reject_unsafe_fstab(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'fstab'
            f.write_text('/dev/block/by-name/userdata /data ext4 rw wait,formattable\n'
                         '/dev/block/by-name/misc /misc emmc defaults defaults\n')
            with self.assertRaises(AssertionError):
                module.check_fstab(f,'legacy')

    def test_bad_boot_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'fake-boot.img'
            f.write_bytes(b'ANDROID!'+b'\0'*65500)
            with self.assertRaises(AssertionError):
                module.check_bootimg(f,b'badkernel')

    def test_true_kernel_fdt_order_is_pinned(self):
        self.assertEqual(len(module.ROM_DTB_HASHES),3)
        self.assertEqual(len(set(module.ROM_DTB_HASHES)),3)

if __name__=='__main__':unittest.main()