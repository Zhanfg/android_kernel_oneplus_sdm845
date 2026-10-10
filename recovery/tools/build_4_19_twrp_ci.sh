#!/usr/bin/env bash
# CI-side only; not for use as phone SH. Does NOT flash or mount anything.
set -euo pipefail
: "${TWRP_ROOT:?set full repo-sync root}"
: "${TWRP_LAYOUT:=legacy}"
: "${DEVICE_TREE_DIR:?set target device tree path}"
case "$TWRP_LAYOUT" in
  legacy|retrofit) ;;
  *) echo "Unsupported layout '$TWRP_LAYOUT'" >&2; exit 2;;
esac
mkdir -p "$TWRP_ROOT/device/oneplus/enchilada"
cp -a "$DEVICE_TREE_DIR"/. "$TWRP_ROOT/device/oneplus/enchilada"/
if [[ "$TWRP_LAYOUT" == retrofit ]]; then
  echo "Opt-in experimental retrofit: selected at build time, NOT inferred from 4.9 boot.img"
  cp "$TWRP_ROOT/device/oneplus/enchilada/recovery/root/system/etc/recovery-retrofit.fstab" \
     "$TWRP_ROOT/device/oneplus/enchilada/recovery/root/system/etc/recovery.fstab"
fi
cd "$TWRP_ROOT"
export ALLOW_MISSING_DEPENDENCIES=false
source build/envsetup.sh
lunch twrp_enchilada-eng
m -j"$(nproc)" bootimage