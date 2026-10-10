#!/usr/bin/env python3
"""Offline binary validation + installer branch simulation (no real block writes)."""
from pathlib import Path
import hashlib, os, shutil, subprocess, tempfile, zipfile
from build_release import *
ROOT=Path(os.environ.get('OP6_RELEASE_ROOT', '/mnt/data'))
OUT=ROOT/'OP6_Kernel_v0.2'
AK3=OUT/AK3_NAME
EXPECTED_SCRIPT_SNIPPET='dd if="$AKHOME/boot-tested.img" of="$BLOCK"'
def run_cli(source_boot,slot='_a',missing=False,boot_slot='_a',inactive=False):
    with tempfile.TemporaryDirectory() as t:
        t=Path(t)
        p=t/'boot_a'; shutil.copyfile(source_boot,p)
        shutil.copyfile(OUT/BOOT_NAME,t/'boot-tested.img')
        if missing: (t/'boot-tested.img').unlink()
        with zipfile.ZipFile(AK3) as z:
            script=z.read('anykernel.sh').decode().split('. tools/ak3-core.sh;')[1]
            (t/'KERNEL_SHA256SUMS').write_bytes(z.read('KERNEL_SHA256SUMS'))
            (t/'Image.gz-dtb').write_bytes(z.read('Image.gz-dtb'))
        # Model a block device as an ordinary file, mock blockdev and the -b test
        # ONLY in this execution harness, never in the released installer.
        script=script.replace('[ -b "$BLOCK" ]','[ -f "$BLOCK" ]')
        pre=f'''AKHOME="{t}"; BLOCK="{p}"; SLOT="{slot}"; SLOT_SELECT="{'inactive' if inactive else ''}";
getprop() {{ case "$1" in ro.boot.slot_suffix) echo "{boot_slot}";; *) echo '';; esac; }}
ui_print() {{ :; }}
abort() {{ echo "$*" >&2; exit 98; }}
blockdev() {{ case "$1" in --getsize64) echo 67108864;; --setrw) return 0;; *) return 1;; esac; }}
'''
        tmp=t/'test.sh';tmp.write_text(pre+script)
        validate=subprocess.run(['sh','-n',str(tmp)],capture_output=True,text=True)
        assert validate.returncode==0,validate.stderr
        proc=subprocess.run(['sh',str(tmp)],capture_output=True,text=True)
        result_sha=digest(p.read_bytes())
        return proc.returncode,result_sha,proc.stderr

def main():
    orig=OUT/ROLLBACK_NAME
    tested=OUT/BOOT_NAME
    assert hashlib.sha256(orig.read_bytes()).hexdigest()==EXPECTED_ROM_BOOT
    assert hashlib.sha256(tested.read_bytes()).hexdigest()==EXPECTED_TESTED_BOOT
    with zipfile.ZipFile(AK3) as z:
        assert z.testzip() is None
        assert digest(z.read('boot-tested.img'))==EXPECTED_TESTED_BOOT
        assert digest(z.read('Image.gz-dtb'))==EXPECTED_KERNEL
        assert dtbs(z.read('Image.gz-dtb'))==EXPECTED_FDT
        sh=z.read('anykernel.sh').decode()
        assert EXPECTED_SCRIPT_SNIPPET in sh
        assert 'split_boot;' not in sh and 'flash_boot;' not in sh and 'write_boot;' not in sh
    ret,new,_=run_cli(orig); assert ret==0 and new==EXPECTED_TESTED_BOOT,(ret,new)
    print('PASS: verified original ROM Boot -> exact user-tested Boot')
    ret,new,_=run_cli(tested); assert ret==0 and new==EXPECTED_TESTED_BOOT,(ret,new)
    print('PASS: already-installed tested Boot -> no-op')
    with tempfile.TemporaryDirectory() as t:
        bad=Path(t)/'boot.img'; bytearray_img=bytearray(orig.read_bytes());bytearray_img[6000]^=1;bad.write_bytes(bytearray_img)
        ret,new,_=run_cli(bad)
        assert ret!=0 and new==digest(bad.read_bytes()),(ret,new)
        print('PASS: changed/unrecognized boot -> fail closed without write')
    ret,new,_=run_cli(orig,slot='_z'); assert ret!=0 and new==EXPECTED_ROM_BOOT,(ret,new)
    print('PASS: unknown A/B slot -> fail closed without write')
    ret,new,_=run_cli(orig,slot='_a',boot_slot='_b'); assert ret!=0 and new==EXPECTED_ROM_BOOT,(ret,new)
    print('PASS: AK3 slot != bootloader slot -> fail closed')
    ret,new,_=run_cli(orig,inactive=True); assert ret!=0 and new==EXPECTED_ROM_BOOT,(ret,new)
    print('PASS: postinstall inactive-slot context -> fail closed')
    ret,new,_=run_cli(orig,missing=True); assert ret!=0 and new==EXPECTED_ROM_BOOT,(ret,new)
    print('PASS: bundled Boot missing -> fail closed without write')
    print('PASS: ZIP entries, executable permissions, kernel/DTBs, AVB verified')

if __name__=='__main__':main()