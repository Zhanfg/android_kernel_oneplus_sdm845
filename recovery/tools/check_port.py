#!/usr/bin/env python3
"""Fail-closed recovery-as-boot TWRP 14 port source / payload checker.

This is a host-only audit, NOT a runtime security attestation or a flash test.
"""
import argparse
import hashlib
import re
import struct
import zlib
from pathlib import Path

BOOT_LIMIT = 67108864
ROM_DTB_HASHES = [
    '341e34eb0dae79a33a4b2a5cb89cb1f2fb2209d9d17d98f2d04d2551f46c9b11',
    'da668c914c0db8d8a52917070bfa370dd3208846f731aead4d72b3324b846298',
    '86638511847918077c2647a125991c03d46e2ecac66f65605c4ddb449774013c',
]


def parse_kernel(blob):
    assert blob.startswith(b'\x1f\x8b\x08'), 'Expected gzip compressed arm64 kernel'
    dec = zlib.decompressobj(zlib.MAX_WBITS | 16)
    kernel = dec.decompress(blob) + dec.flush()
    assert dec.eof, 'Truncated gzip stream'
    tail = dec.unused_data
    hashes = []
    while tail:
        assert len(tail) >= 40, 'Trailing bytes too short for an FDT'
        magic, length = struct.unpack_from('>II', tail)
        assert magic == 0xD00DFEED and 64 <= length <= len(tail), 'Invalid appended DTB'
        dtb = tail[:length]
        assert b'qcom,sdm845' in dtb, 'FDT is not SDM845'
        hashes.append(hashlib.sha256(dtb).hexdigest())
        tail = tail[length:]
    assert hashes == ROM_DTB_HASHES, ('Kernel FDTs do not match pinned 4.19 baseline! ' + str(hashes))
    return len(kernel), hashes


def check_fstab(path, expected):
    s = path.read_text()
    rows = [l.split() for l in s.splitlines() if l.strip() and not l.lstrip().startswith('#')]
    assert rows and all(len(r) >= 5 for r in rows), f'bad fstab {path}'
    assert all('formattable' not in ' '.join(r) for r in rows), 'dangerous: formattable flag'
    assert all('forceencrypt' not in ' '.join(r) for r in rows), 'dangerous: forceencrypt flag'
    srcs = [(r[0],r[1],r[2]) for r in rows]
    mounts = [r[1] for r in rows]
    assert len(mounts) == len(set(mounts)), f'duplicate mount point {path}'
    assert expected == 'legacy' and not any('logical' in r[4] for r in rows) or expected == 'retrofit' and all('logical' in r[4] for r in rows if r[1] in ('/system','/vendor','/odm'))
    if expected == 'retrofit':
        assert {'/system','/vendor','/odm'}.issubset(set(mounts))
        assert all(r[2]=='erofs' for r in rows if r[1] in ('/system','/vendor','/odm'))
    else:
        assert not any(r[1] in ('/system','/vendor','/odm') for r in rows)
    assert '/data' in mounts and '/misc' in mounts
    print(f'PASS {path.name}: {len(rows)} safe fstab entries [{expected}]')
    return srcs


def check_board(board):
    s = board.read_text()
    required = [
        'TARGET_ARCH := arm64', 'TARGET_BOARD_PLATFORM := sdm845',
        'BOARD_BOOT_HEADER_VERSION := 1','BOARD_BOOTIMAGE_PARTITION_SIZE := 67108864',
        'BOARD_USES_RECOVERY_AS_BOOT := true','TARGET_NO_RECOVERY := true',
        'TARGET_PREBUILT_KERNEL := $(DEVICE_PATH)/prebuilt/Image.gz-dtb',
        'TW_INCLUDE_CRYPTO := false','TW_INCLUDE_CRYPTO_FBE := false',
        'BOARD_AVB_ENABLE := false',
    ]
    for line in required:
        assert line in s, f'missing safety setting {line}'
    assert 'androidboot.super_partition=system' in s, 'Lost retrofit dynamic boot hint'
    print('PASS BoardConfig: 64MiB v1 A/B recovery-as-boot, crypto off, 4.19 prebuilt kernel pinned')


def check_bootimg(path, kernel_blob):
    boot = path.read_bytes()
    assert boot.startswith(b'ANDROID!'), 'Not an Android boot image'
    kernel_size = struct.unpack_from('<I',boot,8)[0]
    ramdisk_size = struct.unpack_from('<I',boot,16)[0]
    page_size = struct.unpack_from('<I',boot,36)[0]
    version = struct.unpack_from('<I',boot,40)[0]
    assert len(boot) <= BOOT_LIMIT, 'boot image exceeds 64MiB partition'
    assert version == 1 and page_size == 4096, f'wrong boot ABI {version}/{page_size}'
    assert ramdisk_size >= 1048576, 'TWRP recovery ramdisk missing/small'
    assert kernel_size == len(kernel_blob), 'boot image kernel size mismatch'
    image = boot[page_size:page_size+kernel_size]
    assert image == kernel_blob, 'Result was built with a DIFFERENT kernel'
    assert b'AVBf' not in boot[-64:], 'Test-only boot image unexpectedly includes an AVB footer'
    print(f'PASS boot.img: header=v{version}, kernel={kernel_size}, ramdisk={ramdisk_size}, full={len(boot)}')
    print('BOOT NOTE: this is ONLY a host-built fastboot-boot test candidate, NOT signed or flashed')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, default=Path(__file__).resolve().parent.parent)
    p.add_argument('--kernel', type=Path)
    p.add_argument('--boot', type=Path)
    args = p.parse_args()
    d = args.root/'device/oneplus/enchilada'
    check_board(d/'BoardConfig.mk')
    check_fstab(d/'recovery/root/system/etc/recovery.fstab','legacy')
    check_fstab(d/'recovery/root/system/etc/recovery-retrofit.fstab','retrofit')
    if args.kernel:
        b=args.kernel.read_bytes()
        n,sha=parse_kernel(b)
        print(f'PASS compiled Linux 4.19 compressed kernel: {len(b)} B, decompressed {n} B, DTBs [{", ".join(x[:12] for x in sha)}]')
        if args.boot:
            check_bootimg(args.boot,b)
    elif args.boot:
        p.error('--boot requires --kernel')
    print('NO DEVICE/ROM VALIDATION DONE. 4.9 boot image is not a 4.19 donor.')

if __name__=='__main__':
    main()