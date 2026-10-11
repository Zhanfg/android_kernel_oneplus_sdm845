#!/usr/bin/env python3
"""Restore exactly the three DTBs and their order from the provided stock enchilada boot.img.

The FDT blobs are the same byte-for-byte; only their concatenation order differs
between build toolchains. This fails closed if any blobs change. No kernel decompression
or new image construction: preserves gzip bytes intact.
"""
import argparse
import hashlib
import struct
import sys
import zlib
from collections import Counter
from pathlib import Path

# From user-supplied uwuAOSP Android 17 boot.img (2026-10-10); not generic SDM845 hashes.
ROM_DTB_SHA256_ORDER = (
    "341e34eb0dae79a33a4b2a5cb89cb1f2fb2209d9d17d98f2d04d2551f46c9b11",
    "da668c914c0db8d8a52917070bfa370dd3208846f731aead4d72b3324b846298",
    "86638511847918077c2647a125991c03d46e2ecac66f65605c4ddb449774013c",
)


def process(inp: Path, out: Path) -> None:
    img = inp.read_bytes()
    if len(img) < 1024 or not img.startswith(b"\x1f\x8b"):
        raise ValueError("Input is not Image.gz-dtb")
    stream = zlib.decompressobj(16 + zlib.MAX_WBITS)
    stream.decompress(img)
    stream.flush()
    if not stream.eof or not stream.unused_data:
        raise ValueError("Missing gzip EOF or appended device trees")
    gzip_end = len(img) - len(stream.unused_data)
    fdt_data = stream.unused_data
    dtbs = {}
    off = 0
    while off < len(fdt_data):
        if len(fdt_data) - off < 40:
            raise ValueError("Truncated FDT header")
        magic, size = struct.unpack_from(">II", fdt_data, off)
        if magic != 0xd00dfeed or size < 64 or off + size > len(fdt_data):
            raise ValueError(f"Invalid appended FDT at {off}")
        blob = fdt_data[off:off + size]
        digest = hashlib.sha256(blob).hexdigest()
        if digest in dtbs:
            raise ValueError(f"Duplicate DTB {digest}")
        dtbs[digest] = blob
        off += size
    if len(dtbs) != 3 or set(dtbs) != set(ROM_DTB_SHA256_ORDER):
        raise ValueError("DTB hashes differ from ROM boot.img; refusing to rewrite any device tree")
    result = img[:gzip_end] + b"".join(dtbs[d] for d in ROM_DTB_SHA256_ORDER)
    if len(result) != len(img):
        raise ValueError("Unexpected image size change")
    if inp != out:
        out.write_bytes(result)
    elif result != img:
        tmp = out.with_name(out.name + ".order_tmp")
        try:
            tmp.write_bytes(result)
            tmp.replace(out)
        finally:
            tmp.unlink(missing_ok=True)
    print("PASS: three byte-identical ROM DTBs, original order restored", file=sys.stderr)
    print("DTB SHA-256 order: " + ", ".join(ROM_DTB_SHA256_ORDER), file=sys.stderr)
    print("Kernel gzip payload unchanged: " + hashlib.sha256(result[:gzip_end]).hexdigest(), file=sys.stderr)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("input", type=Path)
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    try:
        process(args.input, args.output or args.input)
    except (OSError, ValueError, zlib.error) as e:
        sys.exit("FAIL: " + str(e))


if __name__ == "__main__":
    main()