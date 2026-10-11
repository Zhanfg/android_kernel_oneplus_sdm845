#!/system/bin/sh
# OnePlus 6: read-only power/display diagnostics; no arguments.
# Usage: sh op6-power-display-probe.sh
set -u
umask 077
OUTDIR=/sdcard/Download
[ -d "$OUTDIR" ] || OUTDIR=/data/local/tmp
[ -d "$OUTDIR" ] || { echo "No report directory"; exit 1; }
TS=$(date +%Y%m%d_%H%M%S 2>/dev/null || echo unknown)
OUT="$OUTDIR/OP6_Power_Display_$TS.txt"
TMP="$OUT.tmp"
trap 'rm -f "$TMP" 2>/dev/null' EXIT HUP INT TERM
readval() {
  if [ -r "$2" ]; then
    printf '%s: ' "$1"
    head -c 150 "$2" 2>/dev/null
    printf '\n'
  else
    printf '%s: unavailable\n' "$1"
  fi
}
section() { printf '\n[%s]\n' "$1"; }
{
  echo "OnePlus 6 power / display read-only audit"
  echo "date: $(date 2>/dev/null)"
  echo "device: $(getprop ro.product.device 2>/dev/null)"
  echo "kernel: $(uname -r 2>/dev/null)"
  echo "uid: $(id -u 2>/dev/null)"
  echo "Cumulative counters: use at least two captures to compare deltas."
  echo "Review source names before sharing this local report."
  section suspend
  readval state /sys/power/state
  readval wakeup_count /sys/power/wakeup_count
  for n in success fail failed_freeze failed_prepare failed_suspend failed_suspend_late failed_suspend_noirq; do
    [ -r "/sys/kernel/debug/suspend_stats/$n" ] &&
      readval "suspend/$n" "/sys/kernel/debug/suspend_stats/$n"
    [ -r "/sys/power/suspend_stats/$n" ] &&
      readval "suspend_sysfs/$n" "/sys/power/suspend_stats/$n"
  done
  if [ -r /sys/kernel/debug/wakeup_sources ]; then
    echo "Top cumulative wake sources (total_time, name, events, wakes)"
    awk 'NR>1 && NF>=7 {print $7, $1, $3, $4}' /sys/kernel/debug/wakeup_sources 2>/dev/null |
      sort -nr | head -n 15
  else
    echo "Kernel wakeup_sources unavailable or restricted"
  fi
  section cpu
  for p in /sys/devices/system/cpu/cpufreq/policy*; do
    [ -d "$p" ] || continue
    echo "CPU policy $p"
    for n in scaling_governor scaling_cur_freq scaling_min_freq scaling_max_freq; do
      readval "$n" "$p/$n"
    done
  done
  for c in /sys/devices/system/cpu/cpu[0-9]*; do
    [ -d "$c/cpuidle" ] || continue
    echo "cpu idle: $c"
    for st in "$c"/cpuidle/state*; do
      [ -d "$st" ] || continue
      readval "$st/name" "$st/name"
      readval "$st/usage" "$st/usage"
      readval "$st/time" "$st/time"
    done
  done
  # cpu-boost.c registers a kobject under the CPU subsystem.
  # /sys/module/cpu_boost/parameters is not its primary interface.
  for n in input_boost_ms input_boost_freq sched_boost_on_input; do
    f="/sys/devices/system/cpu/cpu_boost/$n"
    [ -r "$f" ] || f="/sys/module/cpu_boost/parameters/$n"
    readval "cpu_boost/$n" "$f"
  done
  section gpu
  for n in gpuclk max_gpuclk idle_timer gpu_busy_percentage; do
    readval "kgsl/$n" "/sys/class/kgsl/kgsl-3d0/$n"
  done
  for n in governor cur_freq min_freq max_freq; do
    readval "kgsl/devfreq/$n" "/sys/class/kgsl/kgsl-3d0/devfreq/$n"
  done
  section "UFS link power"
  found_ufs=0
  for u in /sys/bus/platform/devices/*ufshc*; do
    [ -e "$u" ] || continue
    found_ufs=1
    echo "ufs controller: ${u##*/}"
    for n in clkgate_enable clkgate_delay_ms_perf clkgate_delay_ms_pwr_save \
        hibern8_on_idle_enable hibern8_on_idle_delay_ms runtime_status; do
      if [ "$n" = runtime_status ]; then
        readval "ufs/$n" "$u/power/$n"
      else
        readval "ufs/$n" "$u/$n"
      fi
    done
  done
  [ "$found_ufs" -eq 1 ] || echo "UFS sysfs nodes not present at platform-device path"
  echo "Do not force auto-Hibern8: controller may advertise a hardware quirk."
  section display
  readval drm_status /sys/class/drm/card0-DSI-1/status
  for d in /sys/kernel/debug/dri/*; do
    [ -d "$d" ] || continue
    echo "DRM debug node $d: display-related entry names"
    ls "$d" 2>/dev/null | grep -E '^(dsi|sde|panel|kms)' | head -n 20 || true
  done
  echo "Do not force DSI ULPS/brightness/debug values during measurement."
  section battery
  for n in status current_now voltage_now temp charge_counter cycle_count; do
    readval "battery/$n" "/sys/class/power_supply/battery/$n"
  done
  echo "Battery counter units and polarity are driver-dependent."
  echo "Zero writes to sysfs, debugfs, sysctl, governor, backlight, or SELinux."
} > "$TMP" 2>&1
[ -s "$TMP" ] || { echo "Probe produced no report"; exit 1; }
mv "$TMP" "$OUT" || { echo "Cannot write report"; exit 1; }
trap - EXIT HUP INT TERM
echo "Saved: $OUT"
