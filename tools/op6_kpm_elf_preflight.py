#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Offline ARM64 KPM ELF preflight. NEVER loads code or implies run-time safety."""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import struct
import sys
from pathlib import Path

MAX_FILE = 8 * 1024 * 1024
SH = struct.Struct("<IIQQQQIIQQ")
EH = struct.Struct("<16sHHIQQQIHHHHHH")
SHT_NOBITS = 8
SHT_DYNAMIC = 6
SHT_RELA = 4
SHT_REL = 9
SHT_SYMTAB = 2
REQUIRED = {".kpm.info", ".kpm.init"}
META_LIMITS = {"name": 31, "version": 11, "license": 31,
               "author": 31, "description": 511}


def verify(data: bytes) -> dict:
    if len(data) < EH.size or len(data) > MAX_FILE:
        raise ValueError("KPM file size out of bounds")
    (ident, etype, machine, version, entry, phoff, shoff, flags,
     ehsize, phentsize, phnum, shentsize, shnum, shstrndx) = EH.unpack_from(data)
    if (ident[:4], ident[4], ident[5], ident[6]) != (b"\x7fELF", 2, 1, 1):
        raise ValueError("Not ELF64 little-endian")
    if etype != 1 or machine != 183 or version != 1 or entry != 0:
        raise ValueError("Expected ARM64 ET_REL")
    if phnum != 0 or phoff:
        raise ValueError("KPM must not have program headers")
    if ehsize != EH.size or shentsize != SH.size or not 2 <= shnum <= 512:
        raise ValueError("Invalid ELF header / section count")
    if not 0 < shstrndx < shnum or shoff < EH.size or shoff + shnum * SH.size > len(data):
        raise ValueError("Section table bounds invalid")
    sections = [SH.unpack_from(data, shoff + i * SH.size) for i in range(shnum)]
    namesec = sections[shstrndx]
    if namesec[1] != 3 or namesec[4] + namesec[5] > len(data):
        raise ValueError("Missing or malformed shstrtab")
    names_blob = data[namesec[4]:namesec[4] + namesec[5]]
    selected = {}
    for i, sec in enumerate(sections):
        namelen, typ, flg, addr, off, size, link, info, align, entsize = sec
        if typ == SHT_DYNAMIC:
            raise ValueError("Dynamic ELF objects unsupported")
        if typ != SHT_NOBITS and (off > len(data) or size > len(data) - off):
            raise ValueError("Section out of file bounds")
        if namelen >= len(names_blob) or b"\0" not in names_blob[namelen:]:
            raise ValueError("Section name out of bounds")
        name = names_blob[namelen:names_blob.find(b"\0", namelen)].decode("utf-8", "strict")
        if align and (align & (align - 1)):
            raise ValueError("Non-power-of-two section alignment")
        if name.startswith(".kpm."):
            if name in selected:
                raise ValueError("Duplicated KPM section")
            if not flg & 2 or typ == SHT_NOBITS:
                raise ValueError("KPM sections must be allocated and present")
            selected[name] = data[off:off + size]
        if typ in (SHT_RELA, SHT_REL, SHT_SYMTAB) and link >= shnum:
            raise ValueError("Invalid symbol/relocation section link")
    if not REQUIRED <= selected.keys():
        raise ValueError("Missing KPM metadata or init section")
    if len(selected[".kpm.init"]) < 8 or len(selected[".kpm.init"]) % 8:
        raise ValueError("Invalid KPM init pointer section")
    meta = {}
    for part in selected[".kpm.info"].split(b"\0"):
        if not part:
            continue
        key, sep, val = part.partition(b"=")
        if not sep:
            raise ValueError("Malformed KPM metadata")
        try:
            name = key.decode("ascii")
            value = val.decode("utf-8", "strict")
        except UnicodeError as exc:
            raise ValueError("Invalid metadata encoding") from exc
        if name in meta:
            raise ValueError("Duplicate KPM metadata field")
        meta[name] = value
    if not meta.get("name") or not re.fullmatch(r"[A-Za-z0-9_.-]{1,31}", meta["name"]):
        raise ValueError("Invalid or missing module name")
    for key, limit in META_LIMITS.items():
        if key in meta and len(meta[key].encode()) > limit:
            raise ValueError(f"Metadata {key} too long")
    return {"format": "KPM/ELF64-AArch64", "size": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "name": meta["name"], "metadata": meta,
            "sections": sorted(selected), "runtime_safe": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kpm_file", type=Path)
    args = parser.parse_args()
    try:
        if args.kpm_file.stat().st_size > MAX_FILE:
            raise ValueError("KPM exceeds 8 MiB limit")
        result = verify(args.kpm_file.read_bytes())
    except (OSError, ValueError, struct.error) as err:
        print(f"KPM PREFLIGHT REJECT: {err}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
