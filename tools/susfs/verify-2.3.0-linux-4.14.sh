#!/bin/sh
# SUSFS 2.3.0 / non-GKI 4.14 source preflight.
# Read-only. No arguments, no flashing, no host/device changes.
set -eu
ROOT="${KERNEL_TREE:-$(pwd)}"
FAIL=0
WARN=0
ok()   { printf '[ OK ] %s\n' "$1"; }
bad()  { printf '[FAIL] %s\n' "$1"; FAIL=$((FAIL+1)); }
warn() { printf '[WARN] %s\n' "$1"; WARN=$((WARN+1)); }
has()  { grep -Eq "$2" "$ROOT/$1" 2>/dev/null; }
needs() {
    if [ -f "$ROOT/$1" ]; then ok "$1 exists"; else bad "$1 missing"; fi
}
printf 'SUSFS 2.3.0 non-GKI Linux 4.14 readiness audit (read-only)\n'
printf 'Target kernel tree: %s\n' "$ROOT"
if [ ! -f "$ROOT/Makefile" ]; then
    bad 'kernel Makefile not found (set KERNEL_TREE or cd to source root)'
    exit 1
fi
vers=$(sed -n 's/^VERSION[[:space:]]*=[[:space:]]*//p' "$ROOT/Makefile" | head -n 1)
patch=$(sed -n 's/^PATCHLEVEL[[:space:]]*=[[:space:]]*//p' "$ROOT/Makefile" | head -n 1)
sub=$(sed -n 's/^SUBLEVEL[[:space:]]*=[[:space:]]*//p' "$ROOT/Makefile" | head -n 1)
printf 'Detected kernel: %s.%s.%s\n' "$vers" "$patch" "$sub"
if [ "$vers" != 4 ] || [ "$patch" != 14 ]; then
    bad 'This is not a Linux 4.14 source tree; never treat 4.19 as 4.14 or apply 4.14 VFS patches blindly'
    printf 'RESULT: NOT APPLICABLE (wrong kernel baseline)\n'
    exit 2
fi
ok 'Linux 4.14 baseline'
for f in fs/susfs.c include/linux/susfs.h include/linux/susfs_def.h fs/Makefile fs/namei.c fs/namespace.c fs/stat.c fs/open.c; do
    needs "$f"
done
if has include/linux/susfs.h '^#[[:space:]]*define[[:space:]]+SUSFS_VERSION[[:space:]]+"v2[.]3[.]0"'; then
    ok 'kernel SUSFS version string is v2.3.0'
else
    bad 'kernel SUSFS version is missing or not v2.3.0; header change alone is NOT a valid upgrade'
fi
if has include/linux/susfs_def.h 'CMD_SUSFS_ADD_SUS_PATH_LOOP'; then
    ok 'SUSFS v2 path-loop command appears in ABI'
else
    bad 'SUSFS v2 path-loop command absent; userspace ABI likely mismatched'
fi
if has include/linux/susfs_def.h 'CMD_SUSFS_HIDE_SUS_MNTS_FOR_NON_SU_PROCS'; then
    ok 'SUSFS v2 mount hiding command appears in ABI'
else
    bad 'SUSFS v2 mount hiding ABI absent'
fi
if has fs/Makefile 'obj-\$\(CONFIG_KSU_SUSFS\).*susfs[.]o'; then
    ok 'fs/susfs.o gated by CONFIG_KSU_SUSFS'
else
    bad 'fs/Makefile does not wire SUSFS through CONFIG_KSU_SUSFS'
fi
kconfig=''
for c in KernelSU/kernel/Kconfig drivers/kernelsu/Kconfig KernelSU/Kconfig; do
    if [ -f "$ROOT/$c" ]; then kconfig=$c; break; fi
done
if [ -n "$kconfig" ] && has "$kconfig" 'config[[:space:]]+KSU_SUSFS'; then
    ok 'KernelSU SUSFS Kconfig symbol exists'
else
    bad 'KernelSU/KSU_SUSFS config not in this tree (a future setup script is not a validated integrated binary)'
fi
for file in fs/namei.c fs/namespace.c fs/stat.c fs/open.c; do
    if has "$file" 'susfs|SUSFS'; then
        ok "$file contains SUSFS integration references"
    else
        bad "$file has no SUSFS integration references"
    fi
done
if [ -f "$ROOT/.config" ]; then
    if has .config '^CONFIG_KSU_SUSFS=y$'; then
        ok 'compiled config enables SUSFS'
    else
        bad '.config does not enable SUSFS'
    fi
    if has .config '^CONFIG_KSU_SUSFS_ENABLE_LOG=y$'; then
        warn 'SUSFS logging enabled: disable for release performance/energy measurements after debug'
    fi
else
    warn 'No .config present; verify final defconfig and generated .config after make olddefconfig'
fi
if [ -f "$ROOT/include/linux/susfs_def.h" ]; then
    if has include/linux/susfs_def.h 'AS_FLAGS_|TIF_PROC_|VFSMOUNT_MNT_FLAGS_'; then
        warn 'v2.3 state bit storage detected: audit 4.14 inode mapping, thread-info and vfsmount bit collisions manually'
    fi
fi
warn 'Manual sign-off still required: VFS/RCU lifetime, mount namespace locking, SELinux, KernelSU manual-hook overlap, Android 17 userspace ABI'
warn 'Manual power/performance tests still required: suspend cycles, idle drain, mount storm, path lookup/stat/open latency, memory leaks'
warn 'Read-only source audit cannot establish a bootable or stable kernel'
printf 'RESULT: %s failure(s), %s warning(s)\n' "$FAIL" "$WARN"
[ "$FAIL" -eq 0 ]
