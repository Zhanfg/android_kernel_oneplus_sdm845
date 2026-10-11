#!/bin/sh
# BakaSU / former ReSukiSU: pinned non-GKI integration for enchilada.
set -eu
ROOT=$(CDPATH= cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"
SHA=5b76b884c75f729a220bb317aa4a4fc78f0e0e9c
if [ ! -d KernelSU/.git ]; then
    mkdir -p KernelSU
    git -C KernelSU init -q
    git -C KernelSU remote add origin https://github.com/Baka-SU/BakaSU.git
fi
git -C KernelSU fetch --depth=1 origin "$SHA"
git -C KernelSU checkout --detach -f "$SHA"
[ "$(git -C KernelSU rev-parse HEAD)" = "$SHA" ]
if [ ! -e drivers/kernelsu ]; then
    ln -s ../KernelSU/kernel drivers/kernelsu
fi
[ -f drivers/kernelsu/Kconfig ] || { echo "BakaSU Kconfig missing" >&2; exit 1; }
grep -qxF 'obj-$(CONFIG_KSU) += kernelsu/' drivers/Makefile ||
    printf '\nobj-$(CONFIG_KSU) += kernelsu/\n' >> drivers/Makefile
grep -qxF 'source "drivers/kernelsu/Kconfig"' drivers/Kconfig ||
    printf '\nsource "drivers/kernelsu/Kconfig"\n' >> drivers/Kconfig
python3 "$ROOT/scripts/susfs-419/patch-bakasu-native.py" "$ROOT/KernelSU/kernel/core/init.c"
printf 'BakaSU pinned at %s\n' "$SHA"
