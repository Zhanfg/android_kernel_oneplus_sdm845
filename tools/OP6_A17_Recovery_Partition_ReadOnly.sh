#!/system/bin/sh
# OnePlus 6 (enchilada) / Android 17 recovery partition and filesystem probe.
# Strictly READ ONLY on the device; writes only one diagnostic report.
# Run: sh OP6_A17_Recovery_Partition_ReadOnly.sh    (no arguments)
set -u
umask 077
exec 3>&1 4>&2
TS=$(date '+%Y%m%d_%H%M%S' 2>/dev/null || echo unknown)
OUTDIR=/sdcard/Download
if [ ! -d "$OUTDIR" ] || [ ! -w "$OUTDIR" ]; then OUTDIR=/data/local/tmp; fi
OUT="$OUTDIR/OP6_A17_REC_ReadOnly_${TS}.txt"
if ! : > "$OUT" 2>/dev/null; then
  echo 'ERROR: Cannot write report; no device settings changed.'
  exit 1
fi
exec >> "$OUT" 2>&1
printf '%s\n' 'OP6 / Android 17 RECOVERY READ-ONLY REPORT' '================================================'
printf 'Collected: %s\n' "$(date '+%Y-%m-%d %H:%M:%S %z' 2>/dev/null || echo unavailable)"
printf '%s\n' 'No raw boot image, serial number, IMEI, logs, private data or encryption keys are collected.'
printf '\n[System identity, limited to non-sensitive properties]\n'
for key in ro.product.device ro.build.version.release ro.build.version.sdk ro.boot.slot_suffix ro.boot.bootmode ro.boot.dynamic_partitions ro.boot.super_partition; do
  val=$(getprop "$key" 2>/dev/null || :)
  printf '%s=%s\n' "$key" "${val:-<not exposed>}"
done
printf 'kernel='; uname -r 2>/dev/null || echo unavailable
printf 'selinux='; getenforce 2>/dev/null || echo unavailable
printf '\n[Physical A/B partition link existence: NO modifications]\n'
for root in /dev/block/by-name /dev/block/bootdevice/by-name /dev/block/platform/soc/1d84000.ufshc/by-name; do
  if [ -d "$root" ]; then
    printf 'Partition directory: %s\n' "$root"
    for p in boot boot_a boot_b recovery recovery_a recovery_b vendor_boot vendor_boot_a vendor_boot_b init_boot init_boot_a init_boot_b dtbo dtbo_a dtbo_b vbmeta vbmeta_a vbmeta_b super super_a super_b system system_a system_b vendor vendor_a vendor_b odm odm_a odm_b userdata metadata logdump misc; do
      if [ -e "$root/$p" ] || [ -L "$root/$p" ]; then
        printf '  %-16s -> ' "$p"
        readlink "$root/$p" 2>/dev/null || echo '(device exists; link not readable)'
      fi
    done
  fi
done
printf '\n[Logical partitions: mapper names only]\n'
if [ -d /dev/block/mapper ]; then
  ls -1 /dev/block/mapper 2>/dev/null | sed -n '1,60p'
else
  echo 'No /dev/block/mapper directory exposed.'
fi
printf '\n[Kernel filesystem features]\n'
for fs in erofs ext4 f2fs squashfs overlay; do
  if grep -qw "$fs" /proc/filesystems 2>/dev/null; then printf '%s: yes\n' "$fs"; else printf '%s: no/unavailable\n' "$fs"; fi
done
printf '\n[Read-only fstab lines relevant to Recovery]\n'
for f in /vendor/etc/fstab.qcom /odm/etc/fstab.qcom /system/etc/recovery.fstab /first_stage_ramdisk/system/etc/fstab.qcom /etc/recovery.fstab /vendor/etc/fstab.default; do
  if [ -r "$f" ]; then
    printf 'file: %s\n' "$f"
    grep -E '(^[[:space:]]*[^#[:space:]]+|logical|fileencryption|metadata)' "$f" 2>/dev/null | grep -E '[[:space:]]/(system|vendor|odm|data|metadata)([[:space:]]|/)|logical|fileencryption' | sed -n '1,25p'
  fi
done
printf '\n[Installed recovery tooling presence; NOT executed]\n'
for x in /system/bin/recovery /system/bin/fastbootd /system/bin/lpdump /system/bin/snapuserd /sbin/recovery /sbin/twrp; do
  if [ -e "$x" ]; then echo "$x: present"; else echo "$x: not visible in Android user space"; fi
done
printf '\n[Available bootctl slot info; read-only]\n'
if command -v bootctl >/dev/null 2>&1; then
  bootctl get-current-slot 2>/dev/null || echo 'bootctl unreadable'
else
  echo 'bootctl unavailable'
fi
printf '\n[Interpretation cautions]\n'
printf '%s\n' '- A/B and retrofit dynamic partitions are separate design choices.' '- The presence of logical partitions does not create a physical recovery partition.' '- A TWRP image must match Android 17 EROFS, retrofit mapping and file encryption.' '- DO NOT run fastboot flash recovery on devices without that physical partition.' '- Do not change GPT, AVB, or boot slot as part of this probe.'
printf '\nEND\n'
printf 'Report saved to: %s\n' "$OUT" >&3
exec 1>&3 2>&4
exec 3>&- 4>&-