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
if s.count(old) != 2:
    raise SystemExit("Pinned BakaSU ksu_hook_init site changed: refuse patch")
s = s.replace(old, new)

p.write_text(s)
root = p.parent.parent
for relative in ("supercall/supercall.c", "supercall/dispatch.c"):
    f = root / relative
    text = f.read_text()
    guard = "#ifdef CONFIG_KSU_SUSFS\n"
    # Match an ENTIRE preprocessor line. Substring replacement would corrupt
    # CONFIG_KSU_SUSFS_* leaf-feature names.
    expected = 3 if relative == "supercall/supercall.c" else 3
    if text.count(guard) != expected:
        raise SystemExit(f"Pinned BakaSU {relative} exact SUSFS guards changed")
    if relative == "supercall/supercall.c":
        text = text.replace(guard,
           "#if defined(CONFIG_KSU_SUSFS) || defined(CONFIG_SUSFS_NATIVE_419)\n")
        key = "#if !defined(CONFIG_KSU_TOOLKIT_SUPPORT) && !defined(CONFIG_KSU_SUSFS)"
        if text.count(key) != 1:
            raise SystemExit("Pinned BakaSU supercall early-return changed")
        text = text.replace(key,
           "#if !defined(CONFIG_KSU_TOOLKIT_SUPPORT) && !defined(CONFIG_KSU_SUSFS) && !defined(CONFIG_SUSFS_NATIVE_419)")
    else:
        inc = "#ifdef CONFIG_KSU_SUSFS\n#include <linux/susfs_def.h>\n"
        cmd = "#ifdef CONFIG_KSU_SUSFS\nint ksu_handle_susfs_cmd("
        if text.count(inc) != 1 or text.count(cmd) != 1:
            raise SystemExit("Pinned BakaSU dispatch SUSFS layout changed")
        # Keep the unrelated sdcard monitoring start in its original hook mode.
        text = text.replace(inc,
           "#if defined(CONFIG_KSU_SUSFS) || defined(CONFIG_SUSFS_NATIVE_419)\n#include <linux/susfs_def.h>\n#include <linux/susfs.h>\n", 1)
        text = text.replace(cmd,
           "#if defined(CONFIG_KSU_SUSFS) || defined(CONFIG_SUSFS_NATIVE_419)\nint ksu_handle_susfs_cmd(", 1)
    # Header is local: no Kconfig selector or other root hook is changed.
    text = "#include <linux/susfs_native_419.h>\n" + text
    f.write_text(text)
