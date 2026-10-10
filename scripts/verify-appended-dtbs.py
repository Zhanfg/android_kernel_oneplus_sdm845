#!/usr/bin/env python3
"""Validate Android SDM845 Image.gz-dtb layout before making a flashable AK3 ZIP."""
import gzip
import struct
import sys
import zlib
from pathlib import Path

if len(sys.argv) != 2:
    raise SystemExit("Usage: verify-appended-dtbs.py Image.gz-dtb")
blob = Path(sys.argv[1]).read_bytes()
if not blob.startswith(b"\x1f\x8b"):
    raise SystemExit("FAIL: expected gzip-compressed ARM64 kernel")
stream = zlib.decompressobj(16 + zlib.MAX_WBITS)
kernel = stream.decompress(blob)
kernel += stream.flush()
if not stream.eof:
    raise SystemExit("FAIL: truncated compressed kernel")
appended = stream.unused_data
expected = (("sdm845-v2.1", b"\x00\x00\x02\x41\x00\x00\x02\x01"),
            ("sdm845", b"\x00\x00\x02\x41\x00\x00\x01\x00"),
            ("sdm845-v2", b"\x00\x00\x02\x41\x00\x00\x02\x00"))
offset = 0
dtbs = []
while offset < len(appended):
    if len(appended) - offset < 40:
        raise SystemExit(f"FAIL: trailing garbage at offset {offset}")
    magic, length = struct.unpack_from(">II", appended, offset)
    if magic != 0xD00DFEED or length < 64 or offset + length > len(appended):
        raise SystemExit(f"FAIL: bad FDT at offset {offset}")
    dtb = appended[offset:offset + length]
    if b"qcom,sdm845" not in dtb:
        raise SystemExit("FAIL: appended FDT does not identify SDM845")
    dtbs.append(length)
    offset += length
if len(dtbs) != 3:
    raise SystemExit(f"FAIL: expected 3 SDM845 base DTBs as in stock boot.img; got {len(dtbs)}")
print(f"PASS: decompressed kernel {len(kernel):,} bytes; 3 appended DTBs: {dtbs}; total {len(blob):,} bytes")
