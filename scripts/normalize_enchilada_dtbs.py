#!/usr/bin/env python3
"""Normalize SDM845 appended DTB order to a SHA-pinned user-booted OP6 image.

No kernel recompilation, no device writes. CLI checks EXACT pinned DTB hashes;
unknown, duplicate, corrupted or missing DTBs abort before any overwrite.
"""
from __future__ import annotations
import argparse
import hashlib
import struct
import zlib
from pathlib import Path

DTB_ORDER = (
    '341e34eb0dae79a33a4b2a5cb89cb1f2fb2209d9d17d98f2d04d2551f46c9b11',
    'da668c914c0db8d8a52917070bfa370dd3208846f731aead4d72b3324b846298',
    '86638511847918077c2647a125991c03d46e2ecac66f65605c4ddb449774013c',
)

def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def normalize(blob: bytes, expected: tuple[str, ...] = DTB_ORDER) -> bytes:
    if len(blob) < 100 or blob[:3] != b'\x1f\x8b\x08':
        raise ValueError('Expected gzip ARM64 kernel with 3 appended DTBs')
    stream = zlib.decompressobj(16 + zlib.MAX_WBITS)
    stream.decompress(blob)
    stream.flush()
    if not stream.eof or not stream.unused_data:
        raise ValueError('Missing complete gzip kernel or appended device trees')
    gzlen = len(blob) - len(stream.unused_data)
    payload = stream.unused_data
    blocks: dict[str, bytes] = {}
    pos = 0
    while pos < len(payload):
        if len(payload) - pos < 40:
            raise ValueError('Trailing data following appended DTBs')
        magic, size = struct.unpack_from('>II', payload, pos)
        if magic != 0xd00dfeed or size < 64 or size > len(payload) - pos:
            raise ValueError('Invalid/truncated FDT')
        chunk = payload[pos:pos+size]
        digest = sha(chunk)
        if digest in blocks:
            raise ValueError('Duplicate DTB')
        blocks[digest] = chunk
        pos += size
    if len(blocks) != len(expected) or set(blocks) != set(expected):
        raise ValueError('DTB fingerprint or count differs from user-booted OnePlus 6')
    result = blob[:gzlen] + b''.join(blocks[d] for d in expected)
    if len(result) != len(blob):
        raise ValueError('Unexpected output length change')
    assert sha(result[:gzlen]) == sha(blob[:gzlen]), 'gzip kernel changed'
    return result

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image', type=Path, help='Image.gz-dtb input')
    parser.add_argument('--in-place', action='store_true')
    args = parser.parse_args()
    old = args.image.read_bytes()
    new = normalize(old)
    order = 'unchanged' if old == new else 'normalized'
    if args.in_place:
        # input has already passed all validation; atomic replace avoids truncation
        import os, tempfile
        with tempfile.NamedTemporaryFile(prefix='dtb-',dir=args.image.parent,delete=False) as handle:
            tempname = Path(handle.name)
            try:
                handle.write(new)
                handle.flush()
                os.fsync(handle.fileno())
            except BaseException:
                tempname.unlink(missing_ok=True)
                raise
        tempname.replace(args.image)
    print(f'PASS: {order}; byte exact gzip kernel; 3 pinned SDM845 DTBs; SHA256={sha(new)}')
    if not args.in_place and old != new:
        print('NOT WRITTEN: run --in-place to normalize the validated file')

if __name__ == '__main__':
    main()