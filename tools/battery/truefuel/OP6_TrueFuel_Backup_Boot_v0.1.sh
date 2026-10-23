#!/system/bin/sh
# OnePlus 6 / TrueFuel preflash BOOT backup: READ partition, SAVE to Download.
# Run: sh OP6_TrueFuel_Backup_Boot_v0.1.sh (no arguments)
# No flash, partition writes, current or temperature changes.
set -u
umask 077
PATH=/system/bin:/system/xbin:/vendor/bin:/sbin:/bin:/usr/bin:$PATH
export PATH
abort() { printf 'ERROR: %s\n' "$1" >&2; exit 1; }
[ "$(id -u 2>/dev/null)" = 0 ] || abort 'Root shell required (su).'
DEVICE=$(getprop ro.product.device 2>/dev/null)
MODEL=$(getprop ro.product.model 2>/dev/null)
case "$DEVICE:$MODEL" in
  *[Oo]ne[Pp]lus6*|*enchilada*|*A6000*|*A6003*) : ;;
  *) abort "Not verified OnePlus 6: device=$DEVICE model=$MODEL" ;;
esac
SLOT=$(getprop ro.boot.slot_suffix 2>/dev/null)
case "$SLOT" in
  _a|_b) : ;;
  *)
    BARE_SLOT=$(getprop ro.boot.slot 2>/dev/null)
    case "$BARE_SLOT" in
      a|b) SLOT="_$BARE_SLOT" ;;
      *) abort 'Unknown active A/B slot; refuse to guess.' ;;
    esac ;;
esac
SOURCE=''
for p in "/dev/block/by-name/boot$SLOT" "/dev/block/bootdevice/by-name/boot$SLOT"; do
  if [ -b "$p" ]; then SOURCE="$p"; break; fi
done
[ -n "$SOURCE" ] || abort "Cannot locate boot$SLOT block device."
DOWNLOAD=/sdcard/Download
[ -d "$DOWNLOAD" ] && [ -w "$DOWNLOAD" ] || abort 'Cannot write to Download.'
STAMP=$(date +%Y%m%d_%H%M%S 2>/dev/null)
[ -n "$STAMP" ] || abort 'Clock unavailable.'
OUTDIR="$DOWNLOAD/OP6_TrueFuel_BOOT_Backup_${STAMP}_$$"
mkdir "$OUTDIR" || abort 'Cannot make private backup folder.'
IMG="$OUTDIR/boot${SLOT}_original.img"
INFO="$OUTDIR/DEVICE_INFO.txt"
{
  printf 'OP6 TrueFuel READ-ONLY preflash backup\n'
  printf 'Timestamp: %s\n' "$(date 2>/dev/null)"
  printf 'Device: %s | %s\n' "$DEVICE" "$MODEL"
  printf 'Kernel: %s\n' "$(uname -r 2>/dev/null)"
  printf 'Active slot: %s\nSource: %s\nBackup: %s\n' "$SLOT" "$SOURCE" "$IMG"
  printf 'Verified boot: %s\n' "$(getprop ro.boot.verifiedbootstate 2>/dev/null)"
  printf 'Original boot image can contain private data; do not publish it.\n'
  printf 'This script NEVER writes system partitions or flashes a kernel.\n'
} > "$INFO"
printf 'Reading BOOT %s -> %s\n' "$SOURCE" "$IMG"
if ! dd if="$SOURCE" of="$IMG" bs=1048576 2> "$OUTDIR/dd.log"; then
  rm -f "$IMG"
  abort "Read failed; see $OUTDIR/dd.log"
fi
[ -s "$IMG" ] || { rm -f "$IMG"; abort 'Boot backup is empty.'; }
sha256sum "$IMG" > "$OUTDIR/SHA256SUMS.txt" || abort 'Hash failed.'
cat "$OUTDIR/SHA256SUMS.txt"
printf 'BACKUP COMPLETED: %s\n' "$OUTDIR"
printf 'Copy original boot image to another device before any flash.\n'