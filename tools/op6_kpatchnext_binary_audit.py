#!/usr/bin/env python3
"""Read-only forensic comparison for boot-tested clean v0.3 and KPatch-patched Image."""
import sys
import hashlib
import struct
from pathlib import Path

def run():
    if len(sys.argv) != 4:
        raise SystemExit("usage: audit.py clean Image.kpatched Image.recovered")
    images=[Path(p).read_bytes() for p in sys.argv[1:]]
    names=["clean","kpatched","recovered"]
    for name, image in zip(names, images):
        if len(image)<64 or image[56:60] != b"ARMd":
            raise RuntimeError(f"{name} is not an uncompressed ARM64 Image")
        offset=struct.unpack_from("<Q",image,8)[0]
        ksize=struct.unpack_from("<Q",image,16)[0]
        flags=struct.unpack_from("<Q",image,24)[0]
        entry=struct.unpack_from("<I",image,0)[0]
        print(f"{name}: bytes={len(image)} sha256={hashlib.sha256(image).hexdigest()}")
        print(f"{name}: header kernel_size={ksize} load_offset={offset} flags=0x{flags:x} entry=0x{entry:08x}")
        if ksize < len(image):
            raise RuntimeError(f"{name}: Image exceeds kernel header memory reservation")
    original,patched,recovered=images
    # KPatch changes entry and (potentially) PAC instructions, so recovered may
    # legitimately retain NOPs. Report changes instead of inventing a pass.
    for name, b in (("patched",patched),("recovered",recovered)):
        n=min(len(original),len(b))
        changes=[i for i in range(n) if original[i]!=b[i]]
        print(f"delta(clean,{name}): changed_bytes={len(changes)} size_delta={len(b)-len(original)}")
        if changes:
            print("first_64_changed_offsets:",",".join(hex(x) for x in changes[:64]))
        if name=="recovered" and len(b)==len(original) and not changes:
            print("PASS: exact unpatch roundtrip")
        elif name=="recovered":
            print("NOTE: non-identical unpatch output; inspect PAC/NOP and entry differences before interpreting")
    if patched==original:
        raise RuntimeError("KPatch patch made no changes")
    print("PASS: output ARM64 images parseable; no flash/boot compatibility asserted")
if __name__ == "__main__":
    run()
