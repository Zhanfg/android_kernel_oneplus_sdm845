#!/usr/bin/env python3
"""Guarded injection into the pinned BakaSU init, preserving manual-hook mode."""
from pathlib import Path
import sys
p = Path(sys.argv[1])
s = p.read_text()
inc = '#ifdef CONFIG_SUSFS_NATIVE_419\n#include <linux/susfs.h>\n#endif\n'
anchor = '#ifdef CONFIG_KSU_SUSFS\n#include <linux/susfs.h>\n#endif'
if anchor not in s:
    raise SystemExit("Pinned BakaSU init header changed: refuse automatic patch")
s = s.replace(anchor, anchor + '\n' + inc, 1)
old = '        ksu_hook_init();\n'
new = old + '\n#ifdef CONFIG_SUSFS_NATIVE_419\n        /* After ksu_cred is prepared; this does not replace manual hooks. */\n        susfs_init();\n#endif\n'
if s.count(old) != 1:
    raise SystemExit("Pinned BakaSU ksu_hook_init site changed: refuse patch")
s = s.replace(old, new, 1)
p.write_text(s)
