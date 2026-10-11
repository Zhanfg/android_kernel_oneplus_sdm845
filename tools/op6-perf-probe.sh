#!/system/bin/sh
# Read-only OnePlus 6 kernel I/O, networking, and EP capability probe.
# Run with: sh op6-perf-probe.sh (no arguments)
set -u
OUTDIR=/sdcard/Download
if [ ! -d "$OUTDIR" ]; then OUTDIR=/data/local/tmp; fi
TS=$(date +%Y%m%d_%H%M%S 2>/dev/null || echo unknown)
OUT="$OUTDIR/OP6_Kernel_PerfProbe_$TS.txt"
umask 077

{
  echo "OnePlus 6 I/O + Network + EP capability probe"
  echo "date: $(date 2>/dev/null)"
  echo "kernel: $(uname -r 2>/dev/null)"
  echo "device: $(getprop ro.product.device 2>/dev/null)"
  echo "android: $(getprop ro.build.version.release 2>/dev/null)"
  echo "uid: $(id -u 2>/dev/null)"
  echo "mode: read-only; no sysctl, qdisc, iptables or block writes"
  echo
  echo "[block]"
  for b in /sys/block/*; do
    [ -d "$b" ] || continue
    case "${b##*/}" in loop*|ram*|zram*) continue ;; esac
    echo "device: ${b##*/}"
    for f in queue/scheduler queue/rotational queue/nr_requests queue/read_ahead_kb device/queue_depth; do
      [ -r "$b/$f" ] && { printf '%s: ' "$f"; cat "$b/$f"; }
    done
  done
  echo
  echo "[tcp]"
  for f in /proc/sys/net/ipv4/tcp_congestion_control /proc/sys/net/ipv4/tcp_available_congestion_control /proc/sys/net/core/default_qdisc; do
    [ -r "$f" ] && { printf '%s: ' "$f"; cat "$f"; }
  done
  echo
  echo "[ipset]"
  if command -v ipset >/dev/null 2>&1; then
    echo "ipset userspace: available"
    ipset -v 2>&1 | head -n 2
  else
    echo "ipset userspace: unavailable (kernel support may still be present)"
  fi
  if [ -r /proc/net/ip_set_names ]; then
    echo "ipset proc interface: available"
  else
    echo "ipset proc interface: not exposed"
  fi
  echo
  echo "[ep / bpf]"
  [ -e /sys/fs/bpf ] && echo "bpffs path: present" || echo "bpffs path: absent"
  [ -e /sys/kernel/btf/vmlinux ] && echo "kernel BTF: present" || echo "kernel BTF: absent"
  for f in /sys/kernel/tracing/events/binder /sys/kernel/debug/tracing/events/binder; do
    [ -d "$f" ] && echo "binder trace events: $f"
  done
  if command -v bpftool >/dev/null 2>&1; then
    echo "bpftool: present"
    bpftool feature probe kernel 2>&1 | grep -E 'bpf\(\)|BTF|kprobe|tracepoint|available' | head -n 35
  else
    echo "bpftool: unavailable; no eBPF capability claim"
  fi
  if [ -r /proc/config.gz ] && command -v gzip >/dev/null 2>&1; then
    echo
    echo "[compiled config]"
    gzip -dc /proc/config.gz 2>/dev/null | grep -E '^(CONFIG_(IP_SET|NETFILTER_XT_SET|NET_SCH_FQ_CODEL|NET_SCH_FQ|TCP_CONG_BBR|MQ_IOSCHED_KYBER|BPF_SYSCALL|BPF_EVENTS|DEBUG_INFO_BTF)=|# CONFIG_(IP_SET|BPF_EVENTS|DEBUG_INFO_BTF) is not set)' || true
  fi
  echo
  echo "Note: presence of config != runtime compatibility or performance gain."
} > "$OUT" 2>&1

if [ -f "$OUT" ]; then
  echo "Report: $OUT"
else
  echo "Failed to write report (check Download permissions)." >&2
  exit 1
fi
