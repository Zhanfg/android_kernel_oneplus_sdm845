#!/system/bin/sh
# OnePlus 6 | Android 16/17 | Linux 4.19 | RealPerf A/B sampler v1
# POSIX sh, user supplies NO arguments. READ-ONLY hardware; writes just a TXT log.
# Never changes frequency, scheduler, SELinux, thermal, sysctl or module state.
set -u
umask 077

find_output_dir() {
    for d in /sdcard/Download /storage/emulated/0/Download /data/local/tmp "${TMPDIR:-/tmp}"; do
        [ -d "$d" ] && [ -w "$d" ] && { printf '%s' "$d"; return 0; }
    done
    return 1
}
OUTDIR=$(find_output_dir) || { echo 'ERROR: no writable Download or tmp directory'; exit 1; }
STAMP=$(date '+%Y%m%d_%H%M%S' 2>/dev/null || echo unknown)
OUT="$OUTDIR/OP6_RealPerf_AB_${STAMP}.txt"
: > "$OUT" || { echo 'ERROR: cannot create output'; exit 1; }

rd() {
    if [ -r "$1" ]; then
        IFS= read -r val < "$1" || :
        printf '%s' "${val:-NA}"
    else
        printf 'NA'
    fi
}
prop() {
    if command -v getprop >/dev/null 2>&1; then
        getprop "$1" 2>/dev/null || printf 'NA'
    else
        printf 'NA'
    fi
}
kv() { printf 'META|%s|%s\n' "$1" "$2" >> "$OUT"; }
psi10() {
    [ -r "$1" ] || { printf NA; return; }
    awk '$1=="some"{for(i=2;i<=NF;i++)if($i~/^avg10=/){split($i,a,"=");print a[2];exit}}' "$1" 2>/dev/null
}
iofull10() {
    [ -r /proc/pressure/io ] || { printf NA; return; }
    awk '$1=="full"{for(i=2;i<=NF;i++)if($i~/^avg10=/){split($i,a,"=");print a[2];exit}}' /proc/pressure/io 2>/dev/null
}
memstat() {
    awk '$1=="MemAvailable:"{a=$2}$1=="SwapFree:"{b=$2}END{printf "%s|%s",a+0,b+0}' /proc/meminfo 2>/dev/null
}
cpujiffies() {
    awk '$1=="cpu" {t=0;for(i=2;i<=NF;i++)t+=$i; printf "%.0f|%.0f",t,$5+$6;exit}' /proc/stat 2>/dev/null
}
vmcounters() {
    [ -r /proc/vmstat ] || { printf 'NA|NA|NA|NA'; return; }
    awk '$1=="pswpin"{i=$2}$1=="pswpout"{o=$2}$1=="pgmajfault"{f=$2}$1=="workingset_refault"{r=$2}END{printf "%.0f|%.0f|%.0f|%.0f",i+0,o+0,f+0,r+0}' /proc/vmstat 2>/dev/null
}

# Thermal selection happens once. Sysfs naming varies by ROM.
CPU_THERM=''; GPU_THERM=''; SKIN_THERM=''
for t in /sys/class/thermal/thermal_zone*/type; do
    [ -r "$t" ] || continue
    v=$(rd "$t")
    case "$v" in
        *cpu*|*CPU*|*gold*|*silver*) CPU_THERM="$CPU_THERM ${t%/type}/temp" ;;
        *gpu*|*GPU*) GPU_THERM="$GPU_THERM ${t%/type}/temp" ;;
        *skin*|*quiet*therm*) SKIN_THERM="$SKIN_THERM ${t%/type}/temp" ;;
    esac
done
max_thermal() {
    result=NA
    for p in $1; do
        [ -r "$p" ] || continue
        x=$(rd "$p")
        case "$x" in
            ''|*[!0-9]*) continue ;;
            *) if [ "$result" = NA ] || [ "$x" -gt "$result" ]; then result=$x; fi ;;
        esac
    done
    printf '%s' "$result"
}

printf '%s\n' '# OP6 RealPerf / read-only / version 1' > "$OUT"
kv 'format' 'pipe-delimited-v1'
kv 'device' "$(prop ro.product.device)"
kv 'model' "$(prop ro.product.model)"
kv 'android' "$(prop ro.build.version.release)"
kv 'kernel' "$(uname -r 2>/dev/null || echo NA)"
kv 'selinux' "$(getenforce 2>/dev/null || echo NA)"
kv 'root_uid' "$(id -u 2>/dev/null || echo NA)"
kv 'cpu0_governor' "$(rd /sys/devices/system/cpu/cpufreq/policy0/scaling_governor)"
kv 'cpu4_governor' "$(rd /sys/devices/system/cpu/cpufreq/policy4/scaling_governor)"
kv 'cpu0_hw_max_khz' "$(rd /sys/devices/system/cpu/cpufreq/policy0/cpuinfo_max_freq)"
kv 'cpu4_hw_max_khz' "$(rd /sys/devices/system/cpu/cpufreq/policy4/cpuinfo_max_freq)"
kv 'cpu0_up_rate_limit_us' "$(rd /sys/devices/system/cpu/cpufreq/policy0/schedutil/up_rate_limit_us)"
kv 'cpu4_up_rate_limit_us' "$(rd /sys/devices/system/cpu/cpufreq/policy4/schedutil/up_rate_limit_us)"
kv 'cpu0_down_rate_limit_us' "$(rd /sys/devices/system/cpu/cpufreq/policy0/schedutil/down_rate_limit_us)"
kv 'cpu4_down_rate_limit_us' "$(rd /sys/devices/system/cpu/cpufreq/policy4/schedutil/down_rate_limit_us)"
kv 'topapp_cpuset' "$(rd /dev/cpuset/top-app/cpus)"
kv 'foreground_cpuset' "$(rd /dev/cpuset/foreground/cpus)"
kv 'background_cpuset' "$(rd /dev/cpuset/background/cpus)"
kv 'topapp_stune' "$(rd /dev/stune/top-app/schedtune.boost)"
kv 'gpu_governor' "$(rd /sys/class/kgsl/kgsl-3d0/devfreq/governor)"
kv 'ufs_sda_scheduler' "$(rd /sys/block/sda/queue/scheduler)"
kv 'ufs_sdf_scheduler' "$(rd /sys/block/sdf/queue/scheduler)"
kv 'zram_algorithm' "$(rd /sys/block/zram0/comp_algorithm)"
kv 'zram_mmstat_start' "$(rd /sys/block/zram0/mm_stat)"
kv 'sample_interval_seconds' '2'
IDLE_N=10
ACTIVE_N=20
RECOVERY_N=5
TEST_MODE=quick
if [ -t 0 ]; then
    echo 'OnePlus 6 performance capture mode: 1=quick (~75s, default), 2=sustained (~12min)'
    printf 'Select [1/2]: '
    IFS= read -r MODE_CHOICE || MODE_CHOICE=1
    case "$MODE_CHOICE" in
        2) IDLE_N=15; ACTIVE_N=300; RECOVERY_N=25; TEST_MODE=sustained ;;
        *) : ;;
    esac
fi
kv 'test_mode' "$TEST_MODE"
kv 'schedule' "IDLE:${IDLE_N};ACTIVE:${ACTIVE_N};RECOVERY:${RECOVERY_N};PREP:5s"
printf '%s\n' '# DATA|phase|index|epoch|cpu0_cur_khz|cpu4_cur_khz|cpu0_max_khz|cpu4_max_khz|gpu_cur_hz|gpu_max_hz|gpu_busy_pct|gpu_max_pwrlevel|gpu_thermal_pwrlevel|cpu_thermal_max_raw|gpu_thermal_max_raw|skin_thermal_max_raw|battery_temp_raw|battery_current_now_raw|cpu_psi10|memory_psi10|io_psi10|io_full10|memavail_kb|swapfree_kb|cpu_total_jiffies|cpu_idle_jiffies|pswpin|pswpout|pgmajfault|workingset_refault' >> "$OUT"

sample() {
    phase=$1
    index=$2
    epoch=$(date '+%s' 2>/dev/null || echo 0)
    c0=$(rd /sys/devices/system/cpu/cpufreq/policy0/scaling_cur_freq)
    c4=$(rd /sys/devices/system/cpu/cpufreq/policy4/scaling_cur_freq)
    m0=$(rd /sys/devices/system/cpu/cpufreq/policy0/scaling_max_freq)
    m4=$(rd /sys/devices/system/cpu/cpufreq/policy4/scaling_max_freq)
    gc=$(rd /sys/class/kgsl/kgsl-3d0/devfreq/cur_freq)
    gm=$(rd /sys/class/kgsl/kgsl-3d0/devfreq/max_freq)
    gb=$(rd /sys/class/kgsl/kgsl-3d0/gpu_busy_percentage)
    gp=$(rd /sys/class/kgsl/kgsl-3d0/max_pwrlevel)
    gt=$(rd /sys/class/kgsl/kgsl-3d0/thermal_pwrlevel)
    ct=$(max_thermal "$CPU_THERM")
    tg=$(max_thermal "$GPU_THERM")
    ts=$(max_thermal "$SKIN_THERM")
    bt=$(rd /sys/class/power_supply/battery/temp)
    bc=$(rd /sys/class/power_supply/battery/current_now)
    pc=$(psi10 /proc/pressure/cpu)
    pm=$(psi10 /proc/pressure/memory)
    pi=$(psi10 /proc/pressure/io)
    pf=$(iofull10)
    mm=$(memstat)
    jiff=$(cpujiffies)
    vm=$(vmcounters)
    printf 'DATA|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s\n' \
        "$phase" "$index" "$epoch" "$c0" "$c4" "$m0" "$m4" "$gc" "$gm" "$gb" "$gp" "$gt" \
        "$ct" "$tg" "$ts" "$bt" "$bc" "$pc" "$pm" "$pi" "$pf" "$mm" "$jiff" "$vm" >> "$OUT"
}
run_phase() {
    tag=$1
    count=$2
    i=1
    echo "Recording $tag (${count} samples at 2s intervals)..."
    while [ "$i" -le "$count" ]; do
        sample "$tag" "$i"
        sleep 2
        i=$((i+1))
    done
}

printf 'Log file: %s\n' "$OUT"
printf '%s\n' 'Keep screen and ambient conditions comparable between runs.'
printf '%s\n' 'Phase 1/3: leave device idle, avoid touching the screen.'
run_phase IDLE "$IDLE_N"
printf '%s\n' 'Phase 2/3: in 5 seconds switch to ONE reproducible workload (same app, same steps each run).'
sleep 5
run_phase ACTIVE "$ACTIVE_N"
printf '%s\n' 'Phase 3/3: stop the workload and let the device recover.'
run_phase RECOVERY "$RECOVERY_N"
kv 'zram_mmstat_end' "$(rd /sys/block/zram0/mm_stat)"
kv 'end_epoch' "$(date '+%s' 2>/dev/null || echo 0)"
echo "COMPLETE|$OUT" >> "$OUT"
printf 'Finished. Diagnostic saved to %s\n' "$OUT"
printf '%s\n' 'Read-only. No performance gain can be inferred from one unpaired run.'