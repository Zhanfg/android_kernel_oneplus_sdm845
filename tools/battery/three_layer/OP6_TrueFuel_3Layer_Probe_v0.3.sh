#!/system/bin/sh
# OnePlus 6 / A17 / BakaSU / BQ27411 - tri-layer READ-ONLY audit.
# NO-ARGS. NO writes to kernel, partitions, DataFlash, sysfs, settings.
umask 077
export PATH=/system/bin:/system/xbin:/vendor/bin:/product/bin:/sbin:/bin:/usr/bin:$PATH

TS="$(date +%Y%m%d_%H%M%S 2>/dev/null)"
[ -n "$TS" ] || TS=unknown
OUTDIR=/sdcard/Download
[ -d "$OUTDIR" ] || mkdir -p "$OUTDIR" 2>/dev/null
if [ ! -w "$OUTDIR" ]; then
  OUTDIR=/data/local/tmp
  [ -d "$OUTDIR" ] || mkdir -p "$OUTDIR" 2>/dev/null
fi
OUT="$OUTDIR/OP6_TrueFuel_3Layer_${TS}.txt"
exec > "$OUT" 2>&1 || exit 1

section() { printf '\n======== %s ========\n' "$1"; }
value() {
  p="$1"
  if [ -r "$p" ]; then
    v="$(cat "$p" 2>/dev/null | head -c 250)"
    printf '%s=%s\n' "$p" "$v"
  else
    printf '%s=<unavailable>\n' "$p"
  fi
}
property() {
  v="$(getprop "$1" 2>/dev/null)"
  printf '%s=%s\n' "$1" "${v:-<unavailable>}"
}

printf 'OP6 TrueFuel 3-Layer Audit v0.3 - STRICTLY READ-ONLY\n'
printf 'Generated: %s\n' "$(date 2>/dev/null)"
printf 'Script: no arguments, no dynamic loading, no sysfs/firmware writes.\n'
section 'Identity and active kernel'
for p in ro.product.device ro.product.model ro.build.version.release ro.uwu.release ro.boot.slot_suffix ro.boot.dynamic_partitions ro.boot.dynamic_partitions_retrofit; do property "$p"; done
printf 'kernel='; uname -r 2>/dev/null
printf 'uid='; id -u 2>/dev/null
printf 'selinux='; getenforce 2>/dev/null

section 'Kernel capability and built-in gauge'
if [ -r /proc/config.gz ]; then
  (zcat /proc/config.gz 2>/dev/null || gzip -dc /proc/config.gz 2>/dev/null) |
  grep -E '^(# )?CONFIG_(MODULES|MODVERSIONS|MODULE_SIG|KPROBES|FUNCTION_TRACER|FG_BQ27541|ONEPLUS_FASTCHG|QPNP_FG_GEN3|I2C_CHARDEV)' | head -n 45
else
  printf 'kernel_config=unavailable\n'
fi
for p in /proc/op6_truefuel /sys/bus/i2c/devices/0-0055/op6_truefuel_hw; do
  value "$p"
done

section 'Kernel power_supply: explicit units'
for n in bms battery usb main dc; do
  d="/sys/class/power_supply/$n"
  [ -d "$d" ] || continue
  printf '\n[%s]\n' "$n"
  for a in type status present online health capacity bq_soc real_capacity fg_capacity \
    charge_full charge_full_design remaining_capacity charge_counter \
    voltage_now current_now current_avg current_max input_current_limit \
    constant_charge_current constant_charge_current_max temp cycle_count \
    charging_enabled charge_control_limit op_disable_charge; do
    [ -r "$d/$a" ] && value "$d/$a"
  done
done
printf '\nUnit note: BMS charge_full/design generally uAh, OEM remaining_capacity mAh; voltage_now uV, current_now uA; temperature 0.1C. Verify driver implementation.\n'

section 'Consistency and safety checks'
bms=/sys/class/power_supply/bms
soc="$(cat "$bms/bq_soc" 2>/dev/null)"
rm="$(cat "$bms/remaining_capacity" 2>/dev/null)"
dcap="$(cat "$bms/charge_full_design" 2>/dev/null)"
fcc="$(cat "$bms/charge_full" 2>/dev/null)"
temp="$(cat /sys/class/power_supply/battery/temp 2>/dev/null)"
case "$soc:$rm" in
  *[!0-9:]*|:*|*:) echo "soc_remaining_consistency=unavailable";;
  *) if [ "$soc" -gt 0 ] && [ "$rm" -eq 0 ]; then
       echo "WARNING: SOC>0 while RM=0; possible transient read suppression, not proof of empty cell"
     else
       echo "soc_remaining_consistency=not_flagged"
     fi;;
esac
case "$dcap" in
  *[!0-9]*|'') echo "design_capacity_class=unavailable";;
  *) if [ "$dcap" -ge 4400000 ] && [ "$dcap" -le 4600000 ]; then
       echo "design_capacity_class=about_4500mAh"
     else
       echo "design_capacity_class=not_verified_4500mAh"
     fi;;
esac
case "$temp" in
  *[!0-9-]*|'') :;;
  *) if [ "$temp" -ge 400 ]; then echo "NOTE: Battery temperature >=40C. Do not use this snapshot to authorize higher charging current."; fi;;
esac
printf 'bq_soc=%s, remaining_capacity=%s, fcc_uAh=%s, design_uAh=%s, temp_deciC=%s\n' "$soc" "$rm" "$fcc" "$dcap" "$temp"

section 'Hardware device-tree and 3300mAh profile identity'
DT=/sys/firmware/devicetree/base
[ -d "$DT" ] || DT=/proc/device-tree
if [ -d "$DT" ]; then
  for p in model compatible; do
    f="$DT/$p"
    if [ -r "$f" ]; then
      printf '%s=' "$p"
      tr '\000' '\n' < "$f" 2>/dev/null | head -n 7
    fi
  done
  # Device tree contains many strings; names only, no binary calibration blobs.
  find "$DT" -maxdepth 7 -type d 2>/dev/null |
    grep -Ei 'bq27541|pmi8998|batterydata|fg|charger' | head -n 55
else
  echo 'device_tree=unavailable'
fi

section 'Vendor/ODM HAL inventory (paths and process names only)'
for d in /vendor/bin/hw /odm/bin/hw /vendor/etc/init /odm/etc/init \
         /vendor/etc/vintf /odm/etc/vintf /vendor/lib/modules /vendor_dlkm/lib/modules \
         /odm/lib/modules /odm_dlkm/lib/modules; do
  if [ -d "$d" ]; then
    printf '\n[%s]\n' "$d"
    find "$d" -maxdepth 2 -type f 2>/dev/null |
      grep -Ei 'health|charg|power|batter|fuel|\\.ko$' | head -n 65
  fi
done
if command -v service >/dev/null 2>&1; then
  printf '\n[Registered health / charger services]\n'
  service list 2>/dev/null | grep -Ei 'health|charger' | head -n 35
fi
if command -v lshal >/dev/null 2>&1; then
  printf '\n[HIDL health services]\n'
  lshal 2>/dev/null | grep -iE 'android.hardware.health|charger' | head -n 25
fi
for vf in /vendor/etc/vintf/manifest.xml /odm/etc/vintf/manifest.xml; do
  [ -r "$vf" ] || continue
  printf '\n[VINTF health declarations: %s]\n' "$vf"
  grep -iEn -B2 -A5 'android.hardware.health|health@2\.' "$vf" 2>/dev/null | head -n 55
done
printf '\n[Running health / charging processes]\n'
ps -A 2>/dev/null | grep -Ei 'health|charg|dashd' | grep -v 'grep -Ei' | head -n 35
for d in /vendor/etc/init /odm/etc/init; do
  [ -d "$d" ] || continue
  printf '\n[Vendor init service declarations: %s]\n' "$d"
  grep -iEh '^[[:space:]]*service[[:space:]]+[^[:space:]]*(health|charg)[^[:space:]]*|[[:space:]]/(bin|bin/hw)/[^[:space:]]*(health|charg)' \
    "$d"/*.rc 2>/dev/null | head -n 40
done

section 'A/B partition names - never written'
for p in boot dtbo vendor odm system vbmeta vendor_boot init_boot vendor_dlkm odm_dlkm \
  modem dsp bluetooth persist tz hyp devcfg abl xbl keymaster; do
  for suf in _a _b ''; do
    x="/dev/block/by-name/${p}${suf}"
    if [ -e "$x" ] || [ -L "$x" ]; then
      printf '%s => %s\n' "${p}${suf}" "$(readlink "$x" 2>/dev/null)"
    fi
  done
done
section 'Live mounting'
mount 2>/dev/null | grep -E ' on /(vendor|odm|system|metadata|vendor_dlkm|odm_dlkm)( |/)' | head -n 30

section 'Summary and interpretation'
echo "Do not assume BQ SOC is Unfiltered SOC: chip register 0x30 is the independent unfiltered source."
echo "Do not assume charge_full_design proves learned 4500mAh FCC or correct ChemID."
echo "BQ internal DataFlash is NOT a disk partition; do not write to persist."
echo "Boot-tested kernel, actual vendor image and upstream device tree are distinct evidence sets."
echo "No I2C direct probe attempted, and no kernel module was loaded."
echo "Recommended comparison: native /sys/bus/i2c/devices/0-0055/op6_truefuel_hw vs bms/bq_soc vs Android battery/capacity."
echo "DONE; report: $OUT"