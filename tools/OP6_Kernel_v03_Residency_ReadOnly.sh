#!/system/bin/sh
# OnePlus 6 Android 17 / Linux 4.19: v0.3 controlled residency / PSI sampler
# Shell script takes NO parameters, does NOT alter governor, device or kernel settings.
# Writes only a private text report to Download or /data/local/tmp.
set -u
umask 077
PATH=/system/bin:/system/xbin:/vendor/bin:/product/bin:/sbin:/bin:$PATH
find_output() {
    for p in /sdcard/Download /storage/emulated/0/Download /data/local/tmp; do
        if [ -d "$p" ] && [ -w "$p" ]; then printf '%s' "$p"; return 0; fi
    done
    return 1
}
D=$(find_output) || { echo 'Cannot write to Download or /data/local/tmp'; exit 1; }
STAMP=$(date '+%Y%m%d_%H%M%S' 2>/dev/null || echo unknown)
OUT="$D/OP6_Kernel_v03_Residency_${STAMP}.txt"
: > "$OUT" || { echo 'Cannot create report'; exit 1; }
line() { printf '%s\n' "$*" >> "$OUT"; }
rd() { if [ -r "$1" ]; then IFS= read -r v < "$1" || :; printf '%s' "${v:-NA}"; else printf NA; fi; }
pr() { getprop "$1" 2>/dev/null || printf NA; }
mono() { date '+%s' 2>/dev/null || echo 0; }

# Never read or transmit account identifiers, per-UID histories, serial numbers, logs, or app data.
line '# OP6 Kernel v0.3 read-only residency, PSI and thermal experiment'
line 'META|format|op6-v03-residency-1'
line "META|utc|$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || echo unknown)"
line "META|device|$(pr ro.product.device)"
line "META|android|$(pr ro.build.version.release)"
line "META|rom|$(pr ro.uwu.release)"
line "META|kernel|$(uname -r 2>/dev/null || echo unknown)"
line "META|slot|$(pr ro.boot.slot_suffix)"
line "META|root_uid|$(id -u 2>/dev/null || echo unknown)"
line "META|battery_status|$(rd /sys/class/power_supply/battery/status)"
line "META|cpu0_governor|$(rd /sys/devices/system/cpu/cpufreq/policy0/scaling_governor)"
line "META|cpu4_governor|$(rd /sys/devices/system/cpu/cpufreq/policy4/scaling_governor)"
line "META|cpu0_up_rate_limit_us|$(rd /sys/devices/system/cpu/cpufreq/policy0/schedutil/up_rate_limit_us)"
line "META|cpu0_down_rate_limit_us|$(rd /sys/devices/system/cpu/cpufreq/policy0/schedutil/down_rate_limit_us)"
line "META|cpu4_up_rate_limit_us|$(rd /sys/devices/system/cpu/cpufreq/policy4/schedutil/up_rate_limit_us)"
line "META|cpu4_down_rate_limit_us|$(rd /sys/devices/system/cpu/cpufreq/policy4/schedutil/down_rate_limit_us)"
line "META|ufs_scheduler|$(rd /sys/block/sda/queue/scheduler)"
line "META|zram_algorithm|$(rd /sys/block/zram0/comp_algorithm)"

# TIS snapshots are the actual frequency-residency counters, unlike cur_freq probes.
residency() {
    phase=$1; edge=$2; policy=$3
    path="/sys/devices/system/cpu/cpufreq/policy${policy}/stats/time_in_state"
    if [ -r "$path" ]; then
        awk -v phase="$phase" -v edge="$edge" -v policy="$policy" \
            'NF>=2 && $1 ~ /^[0-9]+$/ && $2 ~ /^[0-9]+$/ {printf "TIS|%s|%s|%s|%s|%s\n",phase,edge,policy,$1,$2}' "$path" >> "$OUT" 2>/dev/null
    else
        line "TIS_UNAVAILABLE|$phase|$edge|$policy"
    fi
}
psi() {
    phase=$1; edge=$2
    for kind in cpu memory io; do
        file="/proc/pressure/$kind"
        if [ -r "$file" ]; then
            awk -v phase="$phase" -v edge="$edge" -v kind="$kind" \
              '{ for(i=1;i<=NF;i++) if($i ~ /^total=/) {split($i,p,"="); if (p[2] ~ /^[0-9]+$/) printf "PSI|%s|%s|%s|%s|%s\n",phase,edge,kind,$1,p[2] } }' "$file" >> "$OUT" 2>/dev/null
        else
            line "PSI_UNAVAILABLE|$phase|$edge|$kind"
        fi
    done
}
# Thermals: capture only one representative maximum. For snap readings, unknown type = unknown unit.
therm() {
    mx=NA
    for f in /sys/class/thermal/thermal_zone*/type; do
        [ -r "$f" ] || continue
        case "$(rd "$f")" in
            *cpu*|*CPU*|*gold*|*silver*)
                path="${f%/type}/temp"
                tmp=$(rd "$path")
                case "$tmp" in ''|*[!0-9]*) continue;; esac
                if [ "$mx" = NA ] || [ "$tmp" -gt "$mx" ]; then mx=$tmp; fi
            ;;
        esac
    done
    printf '%s' "$mx"
}


# Optional, read-only UI jank counters from the foreground app. This is NOT a
# Perfetto frame-time trace; gfxinfo counters can reset when an app restarts.
# Package identity is not recorded: only a CRC tag to detect target changes.
focus_package() {
    command -v dumpsys >/dev/null 2>&1 || return 1
    dumpsys window windows 2>/dev/null | sed -n 's/.*mCurrentFocus=.*u[0-9][0-9]* \([A-Za-z0-9_.]*\)\/.*/\1/p' | head -n 1
}
gfx_snapshot() {
    edge=$1
    pkg=$(focus_package)
    case "$pkg" in ''|*[!a-zA-Z0-9._]*) line "GFX_UNAVAILABLE|$edge|no-focus"; return;; esac
    digest=$(printf '%s' "$pkg" | cksum | awk '{print $1}')
    raw=$(dumpsys gfxinfo "$pkg" 2>/dev/null) || { line "GFX_UNAVAILABLE|$edge|dumpsys-error"; return; }
    frames=$(printf '%s\n' "$raw" | awk '/Total frames rendered:/{print $NF;exit}')
    jank=$(printf '%s\n' "$raw" | awk '/Janky frames:/{print $3;exit}')
    case "$frames:$jank" in *[!0-9:]*|:*) line "GFX_UNAVAILABLE|$edge|counters-missing";;
        *) line "GFX|$edge|$digest|$frames|$jank";; esac
}

IDLE=12; ACTIVE=30; RECOVERY=10
if [ -t 0 ]; then
    echo 'OP6 v0.3: choose 1=quick (~2 minutes), 2=sustained (~6 minutes)'
    printf 'Choice [1]: '
    IFS= read -r choice || choice=1
    if [ "$choice" = 2 ]; then IDLE=24; ACTIVE=125; RECOVERY=30; fi
fi
line "META|sample_interval|2"
line "META|schedule|IDLE:${IDLE};ACTIVE:${ACTIVE};RECOVERY:${RECOVERY}"
line '# SAMPLE|phase|index|epoch|cpu0_cur_khz|cpu4_cur_khz|gpu_freq_hz|gpu_busy|cpu_thermal_raw|battery_temp_raw|battery_current_raw|mem_available_kb'

sample() {
    phase=$1; idx=$2
    c0=$(rd /sys/devices/system/cpu/cpufreq/policy0/scaling_cur_freq)
    c4=$(rd /sys/devices/system/cpu/cpufreq/policy4/scaling_cur_freq)
    gpu=$(rd /sys/class/kgsl/kgsl-3d0/devfreq/cur_freq)
    busy=$(rd /sys/class/kgsl/kgsl-3d0/gpu_busy_percentage)
    busy=$(printf '%s' "$busy" | tr ' |' '__')
    th=$(therm)
    btemp=$(rd /sys/class/power_supply/battery/temp)
    bcur=$(rd /sys/class/power_supply/battery/current_now)
    avail=$(awk '$1=="MemAvailable:"{print $2;exit}' /proc/meminfo 2>/dev/null)
    line "SAMPLE|$phase|$idx|$(mono)|$c0|$c4|$gpu|$busy|$th|$btemp|$bcur|${avail:-NA}"
}
phase_run() {
    p=$1; count=$2
    line "PHASE_START|$p|$(mono)"
    residency "$p" START 0; residency "$p" START 4; psi "$p" START
    i=1
    while [ "$i" -le "$count" ]; do
        sample "$p" "$i"
        # Give the user time to enter the target app, then snapshot.
        if [ "$p" = ACTIVE ] && [ "$i" -eq 3 ]; then gfx_snapshot START; fi
        sleep 2
        i=$((i+1))
    done
    if [ "$p" = ACTIVE ]; then gfx_snapshot END; fi
    residency "$p" END 0; residency "$p" END 4; psi "$p" END
    line "PHASE_END|$p|$(mono)"
}

printf 'Report: %s\n' "$OUT"
echo 'Keep the screen, charging state and brightness identical across tests.'
echo 'Phase 1: leave idle without opening an app.'
phase_run IDLE "$IDLE"
echo '5 seconds to start reproducible workload: SAME app and actions across tests.'
sleep 5
phase_run ACTIVE "$ACTIVE"
echo 'Phase 3: stop touching the screen and allow recovery.'
phase_run RECOVERY "$RECOVERY"
line "COMPLETE|$(mono)"
echo "Done, report saved to $OUT"
echo 'This is a no-write diagnostic. No power-saving gain can be inferred from one run.'