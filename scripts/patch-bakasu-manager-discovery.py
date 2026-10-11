#!/usr/bin/env python3
"""Small fail-closed BakaSU 4.19 boot-complete manager rescan compatibility patch.

This does NOT bypass APK signing, grant manager privileges or change root policy.
It retries official upstream's own signature-validated discovery if the manager
list was empty by the time ksud signals boot-completed. No boot/SELinux bypasses.
"""
from pathlib import Path
import sys

SRC = Path('KernelSU/kernel/runtime/boot_event.c')
INCLUDE_ANCHOR = '#include "manager/manager_observer.h"\n'
INCLUDE_NEW = INCLUDE_ANCHOR + '#include "manager/manager_identity.h"\n'
ANCHOR = '''    pr_info("on_boot_completed!\\n");
    track_throne(TRACK_THRONE_PRUNE_ONLY);
    ksu_selinux_hide_drop_backup_if_unused();'''
REPLACEMENT = '''    pr_info("on_boot_completed!\\n");
#ifndef CONFIG_KSU_DISABLE_MANAGER
    /* Android 17 may defer package metadata/APK scans until late in boot.
     * A missing manager at post-fs-data must not become a permanent state.
     * Retry once at boot-completed; the normal upstream APK signature
     * verifier still authenticates candidates before registration.
     */
    if (!ksu_has_manager()) {
        pr_info("BakaSU: no registered manager at boot-completed; retry scan\\n");
        track_throne(TRACK_THRONE_FORCE_SYNCHRONOUS);
    } else {
        track_throne(TRACK_THRONE_PRUNE_ONLY);
    }
#else
    track_throne(TRACK_THRONE_PRUNE_ONLY);
#endif
    ksu_selinux_hide_drop_backup_if_unused();'''

def patch(text: str) -> str:
    if 'BakaSU: no registered manager at boot-completed; retry scan' in text:
        if INCLUDE_NEW not in text:
            raise ValueError('Prior patch in unexpected state')
        return text
    if text.count(ANCHOR) != 1 or text.count(INCLUDE_ANCHOR) != 1:
        raise ValueError('Pinned upstream changed! Refusing unsafe automatic patch')
    return text.replace(INCLUDE_ANCHOR, INCLUDE_NEW, 1).replace(ANCHOR, REPLACEMENT, 1)

def main() -> None:
    if len(sys.argv) > 2:
        raise SystemExit('Usage: python3 scripts/patch-bakasu-manager-discovery.py [optional-source-path]')
    path = Path(sys.argv[1]) if len(sys.argv) == 2 else SRC
    old = path.read_text(encoding='utf-8')
    new = patch(old)
    if old != new:
        path.write_text(new, encoding='utf-8')
        print('PASS: added signature-verified late manager discovery fallback')
    else:
        print('PASS: fallback already present (idempotent)')

if __name__ == '__main__':
    main()