#!/system/bin/sh
# OnePlus 6 Android 17 Kernel v0.2 basic smoke checks, no arguments, read-only.
set -u
PATH=/system/bin:/system/xbin:/vendor/bin:/product/bin:/sbin:/bin:$PATH
STAMP=$(date +%Y%m%d_%H%M%S 2>/dev/null || echo undated)
OUTDIR=/sdcard/Download
[ -d "$OUTDIR" ] && [ -w "$OUTDIR" ] || OUTDIR=/data/local/tmp
[ -d "$OUTDIR" ] && [ -w "$OUTDIR" ] || OUTDIR=.
OUT="$OUTDIR/OP6_Kernel_v02_Smoke_${STAMP}.txt"
exec > "$OUT" 2>&1 || exit 1
printf 'OnePlus 6 BakaSU v0.2 — READ ONLY startup checks\n%s\n' "$(date 2>/dev/null)"
printf '====================\n'
section(){ printf '\n-- %s --\n' "$1"; }
show_prop(){ k=$1; v=$(getprop "$k" 2>/dev/null); printf '%s=%s\n' "$k" "${v:-UNKNOWN}"; }
section 'DEVICE / ROM / SLOT'
for key in ro.product.device ro.product.board ro.build.version.release ro.build.version.sdk ro.boot.slot_suffix ro.boot.slot ro.boot.verifiedbootstate ro.boot.vbmeta.device_state sys.boot_completed; do show_prop "$key"; done
section 'KERNEL'
uname -a 2>/dev/null
for f in /proc/version /proc/cmdline /sys/kernel/security/lsm; do
  if [ -r "$f" ]; then printf '[%s]\n' "$f"; if [ "$f" = /proc/cmdline ]; then sed -E 's/(androidboot.serialno|androidboot.wifimacaddr|androidboot.bluetoothmacaddr)=[^ ]+/\1=[redacted]/g' "$f"; else head -c 4096 "$f"; printf '\n'; fi; fi
done
section 'ANDROID INIT / BOOT'
ps -A 2>/dev/null | grep -E '(^|[ /])(init|zygote|system_server|ksud)( |$)' || true
section 'KSU MANAGER / SU'
for pkg in org.bakasu.bakasu me.weishu.kernelsu com.rifsxd.ksunext; do
  result=$(pm path "$pkg" 2>/dev/null); [ -z "$result" ] || printf '%s: installed\n' "$pkg"
done
if command -v su >/dev/null 2>&1; then printf 'su executable: %s\n' "$(command -v su)"; else echo 'su executable: not found in this shell'; fi
for f in /data/adb/ksud /data/adb/modules; do
  if [ -e "$f" ]; then printf '%s: exists\n' "$f"; else printf '%s: not accessible / absent\n' "$f"; fi
done
section 'SECCOMP (PROCESS-SPECIFIC)'
for f in /proc/self/status /proc/1/status; do
  if [ -r "$f" ]; then printf '[%s]\n' "$f"; grep -E '^(Name|Seccomp|Seccomp_filters|NoNewPrivs):' "$f"; fi
done
if [ -r /proc/config.gz ]; then
 if command -v zcat >/dev/null 2>&1; then zcat /proc/config.gz 2>/dev/null | grep -E '^CONFIG_(KSU|KSU_MULTI_MANAGER_SUPPORT|SECCOMP|SECCOMP_FILTER|CFI_CLANG|LTO_CLANG)=' || true; fi
fi
section 'FILESYSTEM / PRESSURE'
grep -E 'erofs|overlay|f2fs|ext4' /proc/filesystems 2>/dev/null || true
for f in /proc/pressure/cpu /proc/pressure/memory /proc/pressure/io; do [ ! -r "$f" ] || { printf '[%s]\n' "$f"; cat "$f"; }; done
section 'CPU / POWER / THERMAL'
for f in /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor /sys/devices/system/cpu/cpu4/cpufreq/scaling_governor /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq /sys/devices/system/cpu/cpu4/cpufreq/scaling_cur_freq /sys/class/thermal/thermal_zone0/temp; do [ ! -r "$f" ] || printf '%s=%s\n' "$f" "$(cat "$f" 2>/dev/null)"; done
section 'RESULT'
echo 'Read-only snapshot complete. No kernel tuning or flash was performed.'
# Some terminal apps do not show text after exec redirection. Output path is predictable.