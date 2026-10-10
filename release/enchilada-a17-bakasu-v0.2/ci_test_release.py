#!/usr/bin/env python3
"""Static v0.2 release checks without requiring copyrighted/vendor boot blobs.

The binary, private fixture tests are run separately by test_release.py locally.
"""
import json
import re
import subprocess
from pathlib import Path
from build_release import (AK3_NAME, BOOT_NAME, ROLLBACK_NAME, EXPECTED_AK3,
                           EXPECTED_TESTED_BOOT, EXPECTED_ROM_BOOT,
                           EXPECTED_KERNEL, EXPECTED_FDT, guard_script)


def main():
    template = '''### AnyKernel3 Ramdisk Mod Script
properties() { '\''do.devicecheck=1\\n'\''; }
kernel.string=OnePlus6 Android17 ReSukiSU/BakaSU 4.19.325 EXPERIMENTAL
BLOCK=boot;
IS_SLOT_DEVICE=auto;
PATCH_VBMETA_FLAG=auto;
. tools/ak3-core.sh;
dump_boot;
write_boot;
'''
    script = guard_script(template)
    expected = [
        'do.devicecheck=1', 'Unknown active A/B slot',
        'AK3 target slot differs from bootloader slot',
        'Inactive-slot install is forbidden',
        'Boot target partition disagrees with active slot',
        'Unrecognized installed Boot: refusing any write',
        'Boot readback hash failed',
        EXPECTED_TESTED_BOOT, EXPECTED_ROM_BOOT, EXPECTED_KERNEL,
    ]
    for name in expected:
        assert name in script, f'Missing release contract: {name}'
    for dangerous in ('dump_boot;', 'write_boot;', 'flash_boot;', 'setenforce 0', 'dd if= /dev/zero'):
        assert dangerous not in script, dangerous
    result=subprocess.run(['sh','-n'],input=script,text=True,capture_output=True)
    assert result.returncode == 0, result.stderr
    for field in (EXPECTED_AK3, EXPECTED_TESTED_BOOT, EXPECTED_ROM_BOOT, EXPECTED_KERNEL, *EXPECTED_FDT):
        assert re.fullmatch('[0-9a-f]{64}',field),field
    assert AK3_NAME.endswith('AK3_GUARDED_UNTESTED.zip')
    assert BOOT_NAME.endswith('BOOT_USER_TESTED.img')
    assert ROLLBACK_NAME.endswith('ORIGINAL_BOOT_ROLLBACK.img')
    print('PASS: AK3 guards, current slot verification, SHA pins, shell syntax')
    print('PASS: no generic repack or unbounded/unauthenticated writes')
    print('BOUNDARY: host static source test only; no vendor Boot blobs or hardware touched')

if __name__=='__main__':
    main()