#!/usr/bin/env python3
"""OnePlus 6 BakaSU v0.2: release with a user-boot-tested Boot image.

Repackages private source images without publishing them in Git. Installer
checks exact current Boot against two allowed hashes before raw binary flash.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import shutil
import struct
import zipfile
from pathlib import Path

EXPECTED_AK3 = '5c27a50dbf838f0935082d4d9d159b2d47e5448d774b6e50ff76d387622e7118'
EXPECTED_ROM_BOOT = '6b305cace01270c797c7ad44a1457154ec91667227ce1e4b35be49156d940a0e'
EXPECTED_TESTED_BOOT = 'c763d08e6b686ffbcac3f3730fdf98e0a290c39662fef366369d2cb8255ee432'
EXPECTED_RAMDISK = '76d6462b5873d34a8908a679cdcac964d28c96dc4b28c53dba9db0a411ebb279'
EXPECTED_KERNEL = 'c25575de7214f81d8904c2d6249c851436f2837ed6192c1904f51ef7e0963a4a'
EXPECTED_FDT = (
    '341e34eb0dae79a33a4b2a5cb89cb1f2fb2209d9d17d98f2d04d2551f46c9b11',
    'da668c914c0db8d8a52917070bfa370dd3208846f731aead4d72b3324b846298',
    '86638511847918077c2647a125991c03d46e2ecac66f65605c4ddb449774013c',
)
SIZE = 64 * 1024 * 1024
AK3_NAME = 'OnePlus6_A17_BakaSU_4.19.325_v0.2_AK3_GUARDED_UNTESTED.zip'
BOOT_NAME = 'OnePlus6_A17_BakaSU_4.19.325_v0.2_BOOT_USER_TESTED.img'
ROLLBACK_NAME = 'OnePlus6_A17_ORIGINAL_BOOT_ROLLBACK.img'


def digest(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def blob_info(data: bytes) -> dict:
    if len(data) != SIZE or data[:8] != b'ANDROID!':
        raise ValueError('Not the pinned 64MiB Android boot image')
    kernel_sz, _, ramdisk_sz, _, second_sz, _, _, page, header, _ = struct.unpack_from('<10I', data, 8)
    if header != 1 or page != 4096 or second_sz != 0:
        raise ValueError('Unexpected boot header (must be Boot v1 / 4096-page)')
    if not (20_000_000 < kernel_sz < 25_000_000 and 10_000_000 < ramdisk_sz < 20_000_000):
        raise ValueError('Unexpected boot kernel or Ramdisk size')
    roff = page + ((kernel_sz + page - 1) // page * page)
    if roff + ramdisk_sz >= SIZE:
        raise ValueError('Boot segment exceeds partition')
    header_recovery_size, header_recovery_off, header_len = struct.unpack_from('<IQI', data, 1632)
    if (header_recovery_size, header_recovery_off, header_len) != (0, 0, 1648):
        raise ValueError('Wrong recovery DTBO / header size')
    kernel = data[page:page + kernel_sz]
    ramdisk = data[roff:roff + ramdisk_sz]
    if ramdisk[:3] != b'\x1f\x8b\x08':
        raise ValueError('Non-gzip Ramdisk, unsupported')
    expected_id = hashlib.sha1(kernel + struct.pack('<I',kernel_sz) + ramdisk + struct.pack('<I',ramdisk_sz) + struct.pack('<II',0,0)).digest()
    if data[576:596] != expected_id:
        raise ValueError('Boot SHA-1 header-ID incorrect')
    footer = data[-64:]
    magic, major, minor, boot_payload_sz, vboff, vblen, _ = struct.unpack('>4sIIQQQ28s',footer)
    if magic != b'AVBf' or (major,minor) != (1,0) or vboff != boot_payload_sz or not 256 <= vblen < 4096:
        raise ValueError('Unsupported AVB footer')
    if not (roff + ((ramdisk_sz + page - 1)//page*page) == vboff and vboff + vblen <= SIZE-64):
        raise ValueError('Boot v1 / AVB inconsistent offsets')
    vbmeta = data[vboff:vboff+vblen]
    if vbmeta[:4] != b'AVB0':
        raise ValueError('Not AVB0')
    _, _, auth_sz, aux_sz, algorithm = struct.unpack_from('>IIQQI',vbmeta,4)
    if auth_sz != 0 or algorithm != 0 or vblen != 256+auth_sz+aux_sz:
        raise ValueError('Unexpected AVB signing algorithm; refusing unsigned repack')
    d_off,d_sz = struct.unpack_from('>QQ',vbmeta,96)
    if d_off != 0 or d_sz != 416:
        raise ValueError('Unexpected AVB descriptor table')
    base = 256
    p = base
    hits=[]
    while p < base+d_sz:
        tag, n = struct.unpack_from('>QQ',vbmeta,p)
        if n == 0 or n%8 or p+16+n > base+d_sz:
            raise ValueError('Malformed AVB descriptor')
        if tag == 2:
            image_size = struct.unpack_from('>Q',vbmeta,p+16)[0]
            algorithm_label = vbmeta[p+24:p+56].split(b'\0',1)[0]
            namelen,saltlen,digestlen,flags = struct.unpack_from('>4I',vbmeta,p+56)
            name_off=p+16+8+32+16+60
            name=vbmeta[name_off:name_off+namelen]
            salt=vbmeta[name_off+namelen:name_off+namelen+saltlen]
            sh=vbmeta[name_off+namelen+saltlen:name_off+namelen+saltlen+digestlen]
            if image_size != vboff or algorithm_label != b'sha256' or name != b'boot' or (namelen,saltlen,digestlen,flags)!=(4,32,32,0):
                raise ValueError('Unsupported AVB hash descriptor')
            if hashlib.sha256(salt+data[:image_size]).digest()!=sh:
                raise ValueError('AVB hash mismatch')
            hits.append(1)
        p += 16+n
    if p != base+d_sz or len(hits)!=1:
        raise ValueError('AVB descriptor layout mismatch')
    return dict(kernel=kernel,ramdisk=ramdisk,ramdisk_sha=digest(ramdisk),kernel_sha=digest(kernel),avb='NONE / SHA256 hash descriptor',header=header)


def dtbs(kernel: bytes) -> tuple[str,...]:
    import zlib
    g=zlib.decompressobj(16+zlib.MAX_WBITS)
    _=g.decompress(kernel)
    _+=g.flush()
    if not g.eof:
        raise ValueError('Truncated kernel gzip')
    remain=g.unused_data
    offsets=[]
    while remain:
        if len(remain)<40:
            raise ValueError('Truncated FDT')
        magic,length=struct.unpack_from('>II',remain,0)
        if magic!=0xd00dfeed or not 64 < length <= len(remain):
            raise ValueError('Invalid appended FDT')
        offsets.append(digest(remain[:length]));remain=remain[length:]
    return tuple(offsets)


def guard_script(orig: str) -> str:
    """Single A/B Boot read, two allowed exact preimages, binary-identical write.

    Do not rely on magiskboot unpacked ramdisk: it can be DECOMPRESSED, and
    hashing that against a compressed boot ramdisk rejects valid inputs.
    """
    start='dump_boot;\nwrite_boot;'
    if orig.count(start)!=1 or 'do.devicecheck=1' not in orig:
        raise ValueError('Unrecognized pinned AnyKernel3 installer')
    script=orig.replace('kernel.string=OnePlus6 Android17 ReSukiSU/BakaSU 4.19.325 EXPERIMENTAL',
      'kernel.string=OnePlus6 Android17 BakaSU 4.19.325 v0.2 boot-image-guard')
    script=script.replace('PATCH_VBMETA_FLAG=auto;', 'PATCH_VBMETA_FLAG=0;')
    guard=f'''ui_print " ";
ui_print "OnePlus 6 BakaSU v0.2: byte-exact tested Boot installer";
ui_print "Stock AOSP Recovery cannot install unsigned AK3 (Error 21).";
# setup_ak (called by ak3-core) verifies enchilada and resolves the active slot.
# Never write when A/B slot is ambiguous or the target isn't a boot partition.
case "$SLOT" in _a|_b) ;; *) abort "Unknown active A/B slot";; esac;
# Refuse updater/postinstall contexts that switch to the inactive slot.
[ "$SLOT_SELECT" != "inactive" ] || abort "Inactive-slot install is forbidden for this ROM-specific Boot";
# Confirm that AK3 resolved the same slot as the bootloader, not just a valid suffix.
boot_slot=$(getprop ro.boot.slot_suffix 2>/dev/null);
if [ ! "$boot_slot" ]; then
 boot_slot=$(getprop ro.boot.slot 2>/dev/null);
 case "$boot_slot" in a|b) boot_slot=_$boot_slot;; esac;
fi;
if [ ! "$boot_slot" ]; then
 boot_slot=$(sed -n 's/.*androidboot.slot_suffix=\\(_[ab]\\).*/\\1/p' /proc/cmdline | head -n1);
fi;
case "$boot_slot" in _a|_b) ;; *) abort "Cannot verify bootloader current slot";; esac;
[ "$SLOT" = "$boot_slot" ] || abort "AK3 target slot differs from bootloader slot";
case "$BLOCK" in */boot_a|*/boot_b) ;; *) abort "Unexpected Boot target: $BLOCK";; esac;
case "$BLOCK" in *"$SLOT") ;; *) abort "Boot target partition disagrees with active slot";; esac;
[ -b "$BLOCK" ] || abort "Boot target is not a block device";
[ -f "$AKHOME/boot-tested.img" ] || abort "Tested Boot payload missing";
# Validate target size, source and current Boot before a single byte is written.
bsz=$(blockdev --getsize64 "$BLOCK" 2>/dev/null) || abort "Unable to read Boot partition size";
[ "$bsz" = "67108864" ] || abort "Unexpected Boot partition size: $bsz";
[ "$(wc -c < "$AKHOME/boot-tested.img")" = "67108864" ] || abort "Tested Boot size mismatch";
newsha=$(sha256sum "$AKHOME/boot-tested.img" | cut -d ' ' -f1);
[ "$newsha" = "{EXPECTED_TESTED_BOOT}" ] || abort "Bundled Boot SHA256 mismatch";
[ -f "$AKHOME/KERNEL_SHA256SUMS" ] || abort "Kernel SHA256 file missing";
newkernelsha=$(sha256sum "$AKHOME/Image.gz-dtb" | cut -d ' ' -f1);
[ "$newkernelsha" = "{EXPECTED_KERNEL}" ] || abort "Bundled kernel SHA256 mismatch";
# Read ONLY the selected active Boot; no unpacking, re-compression or AVB changes.
# Prevent flashing an unknown ROM, damaged Boot, patched ramdisk or the wrong slot.
dd if="$BLOCK" of="$AKHOME/boot.img" bs=1048576 count=64 2>/dev/null || abort "Cannot read current Boot";
[ "$(wc -c < "$AKHOME/boot.img")" = "67108864" ] || abort "Current Boot image truncated";
oldsha=$(sha256sum "$AKHOME/boot.img" | cut -d ' ' -f1);
case "$oldsha" in
 {EXPECTED_ROM_BOOT}|{EXPECTED_TESTED_BOOT}) ;;
 *) abort "Unrecognized installed Boot: refusing any write";;
esac;
if [ "$oldsha" = "$newsha" ]; then
 ui_print "Already on verified BakaSU Boot; no writes needed.";
else
 ui_print "Source and active Boot matched. Writing tested Boot to active slot only.";
 blockdev --setrw "$BLOCK" 2>/dev/null || abort "Boot partition is read-only";
 dd if="$AKHOME/boot-tested.img" of="$BLOCK" bs=1048576 count=64 conv=fsync 2>/dev/null || abort "Boot write failed; restore original via Fastboot";
 sync;
 # Verify the actual bytes stored in the target partition.
 dd if="$BLOCK" of="$AKHOME/boot-verify.img" bs=1048576 count=64 2>/dev/null || abort "Boot readback failed; restore via Fastboot";
 [ "$(sha256sum "$AKHOME/boot-verify.img" | cut -d ' ' -f1)" = "$newsha" ] || abort "Boot readback hash failed; restore via Fastboot";
 ui_print "Active Boot write verified byte for byte.";
fi;
'''
    return script.replace(start,guard)


def make_ak3(source: Path, output: Path, tested: bytes) -> tuple[str,str]:
    raw=source.read_bytes()
    if digest(raw)!=EXPECTED_AK3:
        raise ValueError('Unknown AnyKernel3 source ZIP; refuse to modify')
    with zipfile.ZipFile(source) as src:
        names=src.namelist()
        if len(names)!=len(set(names)) or any(x.startswith('/') or '..' in Path(x).parts for x in names):
            raise ValueError('Unsafe archive paths')
        for required in ('anykernel.sh','Image.gz-dtb','tools/ak3-core.sh','META-INF/com/google/android/update-binary','KERNEL_SHA256SUMS'):
            if required not in names:
                raise ValueError(f'Missing AK3 entry {required}')
        kernel=src.read('Image.gz-dtb')
        if digest(kernel)!=EXPECTED_KERNEL or dtbs(kernel)!=EXPECTED_FDT:
            raise ValueError('Kernel or DTBs do not match user-boot-tested baseline')
        original=src.read('anykernel.sh').decode('utf-8')
        new_script=guard_script(original)
        info=f'''OnePlus 6 / enchilada / Android 17 — BakaSU 4.19.325 v0.2
Kernel/Boot is byte-identical to the user's successfully booted 2026-10-10 image.
The AK3 installer has NOT been device-tested, though its guard passes host tests.
Stock AOSP Recovery rejects unsigned AK3 (error 21) — do NOT use its sideload.

This is an EXACT-IMAGE installer (not generic kernel replacement):
- Device check: OnePlus6, A/B slot must be _a or _b and block device boot_[ab]
- Target Boot partition must be exactly 64MiB
- Pin both source ZIP kernel and bundled tested Boot SHA-256
- Current active Boot must exactly match the uploaded ROM Boot or user's tested Boot
- New Boot is copied as whole 64MiB; no magiskboot repack or changed AVB
- Current Boot is read/verified before write, new bytes verified by readback
- Must verify active slot against bootloader properties and refuse inactive-slot/postinstall contexts
- Abort before writing for different ROM, changed partition size, or other root
- Only active boot slot is written; no vendor, dtbo, recovery, data or system writes

Tested Boot sha256: {EXPECTED_TESTED_BOOT}
ROM baseline sha256: {EXPECTED_ROM_BOOT}
Kernel sha256: {EXPECTED_KERNEL}

Unlocked Bootloader without root: install companion tested Boot.img via fastboot;
custom recovery: may run AK3 ZIP ONLY if its own signature policies allow it.
Retain ORIGINAL_BOOT_ROLLBACK.img before experimenting.
'''
        with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as dest:
            for meta in src.infolist():
                data=src.read(meta.filename)
                if meta.filename=='anykernel.sh': data=new_script.encode('utf-8')
                elif meta.filename=='README-EXPERIMENTAL.txt': data=info.encode('utf-8')
                dest.writestr(meta,data)
            meta=zipfile.ZipInfo('boot-tested.img',date_time=(2026,10,10,12,0,0))
            meta.compress_type=zipfile.ZIP_DEFLATED
            meta.create_system=3
            meta.external_attr=(0o100644<<16)
            dest.writestr(meta,tested)
            meta=zipfile.ZipInfo('RELEASE-v0.2.txt',date_time=(2026,10,10,12,0,0))
            meta.compress_type=zipfile.ZIP_DEFLATED
            meta.create_system=3
            meta.external_attr=(0o100644<<16)
            dest.writestr(meta,info.encode('utf-8'))
    with zipfile.ZipFile(output) as z, zipfile.ZipFile(source) as original_zip:
        if z.testzip() is not None or z.read('Image.gz-dtb')!=kernel or z.read('boot-tested.img') != tested:
            raise ValueError('Final ZIP archive corruption')
        new_installer=z.read('anykernel.sh').decode()
        if 'dump_boot;' in new_installer or 'write_boot;' in new_installer or 'flash_boot;' in new_installer:
            raise ValueError('Installer must not use generic magiskboot repack/write')
        if 'dd if="$AKHOME/boot-tested.img" of="$BLOCK"' not in new_installer:
            raise ValueError('Installer missing exact-image write')
        for path in ('META-INF/com/google/android/update-binary','tools/busybox','tools/magiskboot'):
            a=original_zip.getinfo(path)
            b=z.getinfo(path)
            if (a.external_attr, a.create_system)!=(b.external_attr, b.create_system):
                raise ValueError('ZIP permission metadata was damaged: '+path)
    return digest(output.read_bytes()),digest(kernel)


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--ak3',type=Path,required=True)
    p.add_argument('--outdir',type=Path,required=True)
    p.add_argument('--original-boot',type=Path,required=True)
    p.add_argument('--tested-boot',type=Path,required=True)
    a=p.parse_args()
    original=a.original_boot.read_bytes(); tested=a.tested_boot.read_bytes()
    if digest(original)!=EXPECTED_ROM_BOOT or digest(tested)!=EXPECTED_TESTED_BOOT:
        raise ValueError('Unrecognized ROM baseline/Boot, refusing release')
    ob=blob_info(original); tb=blob_info(tested)
    if ob['ramdisk_sha']!=EXPECTED_RAMDISK or tb['ramdisk_sha']!=EXPECTED_RAMDISK:
        raise ValueError('Ramdisk changed (no longer exact tested ROM)')
    if tb['kernel_sha']!=EXPECTED_KERNEL or dtbs(tb['kernel'])!=EXPECTED_FDT:
        raise ValueError('Tested Boot Kernel/DTB mismatch')
    a.outdir.mkdir(parents=True,exist_ok=True)
    ak_path=a.outdir/AK3_NAME
    zip_hash,kernel_hash=make_ak3(a.ak3,ak_path,tested)
    with zipfile.ZipFile(ak_path) as zipped:
        if zipped.read('Image.gz-dtb')!=tb['kernel']:
            raise ValueError('AK3 kernel not identical to tested Boot')
    shutil.copyfile(a.tested_boot,a.outdir/BOOT_NAME)
    shutil.copyfile(a.original_boot,a.outdir/ROLLBACK_NAME)
    output={AK3_NAME:zip_hash,BOOT_NAME:EXPECTED_TESTED_BOOT,ROLLBACK_NAME:EXPECTED_ROM_BOOT}
    manifest={
      'release':'v0.2-safety','device':'enchilada','boot_header':1,
      'kernel':'Linux 4.19.325-cip136 / BakaSU 5b76b884c75f729a220bb317aa4a4fc78f0e0e9c',
      'kernel_sha256':kernel_hash,'rom_ramdisk_sha256':EXPECTED_RAMDISK,
      'fdt_sha256_in_rom_order':EXPECTED_FDT,
      'previous_user_reported_boot_success':True,'ak3_v02_phone_flashing_verified':False,
      'do_not_use_stock_recovery_sideload':True,'build_inputs_private':True,
      'ak3_mode':'flashes user-boot-tested 64MiB boot image byte-for-byte only on exact allowed ROM baseline',
      'artifacts_sha256':output
    }
    (a.outdir/'RELEASE_MANIFEST_v0.2.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    (a.outdir/'SHA256SUMS').write_text(''.join(f'{sha}  {name}\n' for name,sha in output.items()),encoding='ascii')
    print('PASS: original/tested Boot v1 + AVB hash descriptor + kernel/DTB fingerprints')
    print('PASS: ROM and tested Ramdisk exactly identical; no source modifications')
    print('PASS: AK3 contains exact tested Boot, preserves executable mode, has fixed allowlist')
    print('Release outputs:')
    for name,sha in output.items(): print(f'  {name}: {sha}')

if __name__=='__main__':main()