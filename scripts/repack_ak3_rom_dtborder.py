#!/usr/bin/env python3
"""Safely repack pinned successful AK3 artifact, preserving ZIP Unix file modes.

Changes *only* Image.gz-dtb's appended DTB order, hashes, and release text.
This is a post-build packaging adjustment, not a compilation or flash test.
"""
import argparse
import hashlib
import os
import shutil
import tempfile
from pathlib import Path
from zipfile import ZipFile
from normalize_enchilada_dtbs import process

PINNED_IMAGE_SHA256 = '7b772eaa585d80e502ca24b4c28f382864cebb01a5f95a4f8aa18bd5a5426a87'
ORIGINAL_KERNEL_COMMIT = '9ad0027fcccb'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def repack(indir: Path, outdir: Path):
    orig = sorted(indir.glob('*_AK3_EXPERIMENTAL_9ad0027fcccb.zip'))
    if len(orig) != 1:
        raise ValueError('Expected exactly one pinned successful experimental ZIP')
    old = orig[0]
    outdir.mkdir(parents=True, exist_ok=True)
    new = outdir / old.name.replace('_AK3_EXPERIMENTAL_', '_AK3_ROM_DTBORDER_')
    with ZipFile(old) as zi:
        assert zi.testzip() is None, 'Original zip corrupted'
        original_names = zi.namelist()
        original_kernel = zi.read('Image.gz-dtb')
        if sha(original_kernel) != PINNED_IMAGE_SHA256:
            raise ValueError('Source artifact kernel SHA has changed unexpectedly')
        info_old = {e.filename: e.external_attr for e in zi.infolist()}
        with tempfile.TemporaryDirectory() as tmp:
            a = Path(tmp)/'Image.gz-dtb'
            a.write_bytes(original_kernel)
            process(a, a)
            patched = a.read_bytes()
        with ZipFile(new, 'w') as zo:
            for entry in zi.infolist():
                data = zi.read(entry)
                if entry.filename == 'Image.gz-dtb':
                    data = patched
                elif entry.filename == 'KERNEL_SHA256SUMS':
                    data = (sha(patched) + '  Image.gz-dtb\n').encode()
                elif entry.filename == 'README-EXPERIMENTAL.txt':
                    data += (b'\nROM-ORDER CORRECTION: three identical SDM845 DTBs reordered to match\n'
                             b'the original user-supplied uwuAOSP17 OnePlus6 boot.img.\n'
                             b'Kernel gzip bytes and all installer executable modes retained.\n'
                             b'Experimental: real-device boot/stability untested.\n')
                zo.writestr(entry, data)
    with ZipFile(new) as z:
        assert z.testzip() is None, 'Corrected ZIP corrupt'
        assert z.namelist() == original_names, 'Entry names changed'
        assert {e.filename:e.external_attr for e in z.infolist()} == info_old, 'Executable ZIP permissions changed'
        assert z.read('KERNEL_SHA256SUMS').decode().split()[0] == sha(z.read('Image.gz-dtb'))
        assert z.read('Image.gz-dtb') != original_kernel
        # Confirm all shipped scripts retain executable mode from upstream.
        assert (z.getinfo('tools/busybox').external_attr >> 16) & 0o111
        assert (z.getinfo('META-INF/com/google/android/update-binary').external_attr >> 16) & 0o111
    (outdir / (new.name + '.sha256')).write_text(sha(new.read_bytes()) + '  ' + new.name + '\n')
    if (indir/'kernel.config').exists():
        shutil.copy2(indir/'kernel.config', outdir/'kernel.config')
    if (indir/'BUILD_INFO.txt').exists():
        raw = (indir/'BUILD_INFO.txt').read_text()
        (outdir/'BUILD_INFO.txt').write_text(raw + '\nROM DTB ORDER: preserved original uwuAOSP17 order.\n'
                                           'ZIP Unix permissions: identical to the successful CI artifact.\n'
                                           'Not a real-device boot or runtime test.\n')
    print(f'PASS: {new}, size={new.stat().st_size}, sha256={sha(new.read_bytes())}')

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('input_dir', type=Path)
    p.add_argument('output_dir', type=Path)
    a = p.parse_args()
    repack(a.input_dir, a.output_dir)