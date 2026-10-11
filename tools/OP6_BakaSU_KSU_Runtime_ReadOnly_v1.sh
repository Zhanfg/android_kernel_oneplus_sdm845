#!/system/bin/sh
# OnePlus 6 / Android 17 / BakaSU 4.19: safe runtime probe, no arguments.
# No system-state changes. Only writes a text report in Download or fallback directory.
set -u
umask 077
STAMP=$(date '+%Y%m%d_%H%M%S' 2>/dev/null || echo unknown)
DIR=/sdcard/Download
if [ ! -d "$DIR" ] || [ ! -w "$DIR" ]; then
    DIR=/data/local/tmp
fi
if [ ! -d "$DIR" ] || [ ! -w "$DIR" ]; then
    DIR=.
fi
OUT="$DIR/OP6_BakaSU_KSU_Runtime_${STAMP}.txt"
: > "$OUT" || { echo 'ERROR: cannot create diagnostic report'; exit 1; }
info() { printf '%s\n' "$*" >> "$OUT"; }
cmd() { "$@" >> "$OUT" 2>&1 || info "INFO: unavailable or permission denied"; }
section() { info ''; info "===== $* ====="; }
read_status() {
    TAG=$1; PID=$2
    section "Seccomp in $TAG (PID $PID)"
    if [ -r "/proc/$PID/status" ]; then
        sed -n '/^Name:/p;/^Uid:/p;/^NoNewPrivs:/p;/^Seccomp:/p;/^Seccomp_filters:/p' "/proc/$PID/status" >> "$OUT" 2>&1
    else
        info 'UNAVAILABLE (procfs restricted; not proof that seccomp is disabled)'
    fi
}
info 'BakaSU / KernelSU runtime compatibility, read-only probe v1'
info "Time: $(date 2>/dev/null)"
info "Run UID: $(id -u 2>/dev/null)"
info "Output: $OUT"
section 'ROM and boot'
for KEY in ro.product.device ro.boot.hardware ro.build.version.release ro.build.version.sdk ro.build.fingerprint ro.boot.slot_suffix sys.boot_completed ro.boot.verifiedbootstate; do
    info "$KEY=$(getprop "$KEY" 2>/dev/null)"
done
cmd uname -a
section 'Kernel Seccomp flags and runtime support'
if [ -r /proc/config.gz ]; then
    if command -v zcat >/dev/null 2>&1; then
       zcat /proc/config.gz 2>/dev/null | grep -E '^(CONFIG_(SECCOMP|SECCOMP_FILTER|KSU|KSU_MULTI_MANAGER_SUPPORT|KSU_DISABLE_MANAGER|KSU_DISABLE_POLICY|KSU_MANUAL_HOOK|KSU_SUSFS|SECURITY_SELINUX|BPF_SYSCALL)=|# CONFIG_(SECCOMP_FILTER|KSU_DISABLE_MANAGER|KSU_DISABLE_POLICY|KSU_SUSFS) is not set)' >> "$OUT" 2>&1
    else
       info 'zcat unavailable'
    fi
else
    info '/proc/config.gz unavailable (not a proof of disabled functionality)'
fi
read_status shell_self $$
read_status init 1
if command -v pidof >/dev/null 2>&1; then
    for NAME in zygote zygote64 system_server; do
        set -- $(pidof "$NAME" 2>/dev/null)
        [ "$#" -gt 0 ] && read_status "$NAME" "$1"
    done
fi
section 'SELinux status'
if [ -r /sys/fs/selinux/enforce ]; then
    info "SELinux enforcing=$(cat /sys/fs/selinux/enforce 2>/dev/null)"
else
    info 'SELinux node unavailable'
fi
section 'Installed manager package names and APK versions'
# No complete package database or private APK paths are dumped.
if command -v pm >/dev/null 2>&1; then
    pm list packages 2>/dev/null | grep -iE 'kernelsu|bakasu|resukisu|kowksu|sukisu' >> "$OUT" || info 'No packages matched or PackageManager denied access'
    for PKG in org.bakasu.bakasu me.weishu.kernelsu com.rifsxd.ksunext; do
        info "--- package metadata for $PKG ---"
        dumpsys package "$PKG" 2>/dev/null | grep -m 4 -E 'versionCode=|versionName=|userId=' >> "$OUT" || info 'Not installed or details unavailable'
    done
else
    info 'pm unavailable'
fi
section 'Userspace ksud and su command presence'
for BIN in /data/adb/ksud /data/adb/ksu/bin/ksud /system/bin/su /system/xbin/su /debug_ramdisk/su; do
    if [ -e "$BIN" ]; then
        ls -ld "$BIN" >> "$OUT" 2>&1
    else
        info "$BIN: absent or hidden"
    fi
done
if command -v su >/dev/null 2>&1; then
    info "su=$(command -v su)"
else
    info 'su not in PATH (not definitive for BakaSU)'
fi
section 'Root data directories (if running from authorized root shell)'
for D in /data/adb /data/adb/modules /data/adb/metamodule /data/adb/ksud; do
    if [ -r "$D" ]; then
        ls -ld "$D" >> "$OUT" 2>&1
    else
        info "$D: not readable or absent"
    fi
done
section 'Kernel log (KSU-only, optional)'
if [ "$(id -u 2>/dev/null)" = 0 ] && command -v dmesg >/dev/null 2>&1; then
    dmesg 2>/dev/null | grep -iE 'kernelsu|bakasu|ksu:|searching for manager|scanning manager|manager search|post-fs-data triggered|on_boot_completed' | tail -n 75 >> "$OUT" || info 'No matching lines or kernel log restricted'
else
    info 'Skipped; run as authorized root to include filtered KernelSU startup logs.'
fi
section 'Interpretation'
info 'CONFIG_SECCOMP_FILTER=y means the kernel CAN filter syscalls; Seccomp: 0 in a particular process only means that process has no filter.'
info 'A blank active-manager list may reflect APK scan, signature, UAPI, or early-userspace failures. Do not force app trust or enable seccomp globally.'
info 'This script did not flash, remount, restart, set properties, manipulate kernel, grant root, or change SELinux.'
printf 'Report saved: %s\n' "$OUT"