#!/system/bin/sh
# OnePlus 6 TrueFuel v0.5 - read-only native telemetry + charging safety snapshot.
# Usage: sh OP6_TrueFuel_Native_Check_v0.5.sh  (NO arguments)
# No direct I2C, no DataFlash commands, no sysfs/charge-control writes.
umask 077
PATH=/system/bin:/system/xbin:/vendor/bin:/sbin:/bin:/usr/bin:$PATH
export PATH

# Test overrides are used by offline mock verification only.
ROOT=${TF_TEST_ROOT:-}
DIR=${TF_TEST_OUTPUT_DIR:-/sdcard/Download}
[ -d "$DIR" ] && [ -w "$DIR" ] || DIR=/data/local/tmp
if [ ! -d "$DIR" ] || [ ! -w "$DIR" ]; then
    printf 'ERROR: no writable report directory\n' >&2
    exit 1
fi
SAMPLES=${TF_TEST_SAMPLES:-6}
INTERVAL=${TF_TEST_INTERVAL:-12}
case "$SAMPLES:$INTERVAL" in *[!0-9:]*|:*|*:) echo 'Invalid test settings' >&2; exit 1;; esac
NOW=$(date +%Y%m%d_%H%M%S 2>/dev/null)
[ -n "$NOW" ] || NOW=unknown
BASE="$DIR/OP6_TrueFuel_Native_${NOW}_$$"
TXT="$BASE.txt"
CSV="$BASE.csv"

read_value() {
    if [ -r "$ROOT$1" ]; then
        v=$(cat "$ROOT$1" 2>/dev/null)
        [ -n "$v" ] || v=NA
        printf '%s' "$v" | tr '\n\r,' '___'
    else
        printf 'NA'
    fi
}
field() {
    v=$(printf '%s\n' "$NATIVE" | sed -n "s/^$1=//p" | head -n 1)
    [ -n "$v" ] || v=NA
    printf '%s' "$v"
}
log() {
    printf '%s\n' "$1" | tee -a "$TXT"
}

DEVICE=$(getprop ro.product.device 2>/dev/null)
KERNEL=$(uname -r 2>/dev/null)
UID_NOW=$(id -u 2>/dev/null)
{
    printf 'TrueFuel v0.5 / READ ONLY / OP6 / %s\n' "$(date)"
    printf 'device=%s kernel=%s uid=%s\n' "${DEVICE:-unknown}" "${KERNEL:-unknown}" "${UID_NOW:-unknown}"
    printf 'All electric values are raw sysfs units: temperature=0.1 C, current=uA, capacity=uAh.\n'
    printf 'Negative battery current indicates charging on this known OnePlus 6 driver.\n'
    printf 'The optional native kernel endpoint samples only on SAFE DISCHARGE polling.\n'
    printf 'No DataFlash access, no voltage/current changes, no battery model writes.\n'
    printf 'Native readings require booting the matching TrueFuel kernel; this script never loads a KO.\n'
} > "$TXT"
if [ "$UID_NOW" != 0 ] && [ -z "$ROOT" ]; then
    log 'ERROR: run this script inside a ROOT terminal (su), without arguments.'
    exit 1
fi
printf 'utc_time,charging_status,usb_type,usb_online,android_soc_pct,bq_soc_pct,qualcomm_soc_pct,temp_decic,voltage_uV,current_uA,charge_full_uAh,design_uAh,charge_counter_uAh,remaining_capacity_mAh,fastchg_status,fastchg_starting,native_status,native_age_s,native_soc_unfiltered_pct,native_fcc_unfiltered_mAh,native_rm_unfiltered_mAh\n' > "$CSV"
log "REPORT=$TXT"
log "CSV=$CSV"
idx=1
while [ "$idx" -le "$SAMPLES" ]; do
    ST=$(read_value /sys/class/power_supply/battery/status)
    TYPE=$(read_value /sys/class/power_supply/usb/type)
    ONLINE=$(read_value /sys/class/power_supply/usb/online)
    SOC=$(read_value /sys/class/power_supply/battery/capacity)
    BQ=$(read_value /sys/class/power_supply/bms/bq_soc)
    QC=$(read_value /sys/class/power_supply/bms/real_capacity)
    TEMP=$(read_value /sys/class/power_supply/battery/temp)
    VOLT=$(read_value /sys/class/power_supply/battery/voltage_now)
    CURRENT=$(read_value /sys/class/power_supply/battery/current_now)
    FCC=$(read_value /sys/class/power_supply/bms/charge_full)
    DESIGN=$(read_value /sys/class/power_supply/bms/charge_full_design)
    COUNTER=$(read_value /sys/class/power_supply/battery/charge_counter)
    RM=$(read_value /sys/class/power_supply/bms/remaining_capacity)
    DASH=$(read_value /sys/class/power_supply/battery/fastchg_status)
    DASH_START=$(read_value /sys/class/power_supply/battery/fastchg_starting)
    NATIVE=''
    NODE="$ROOT/sys/bus/i2c/devices/0-0055/op6_truefuel_hw"
    if [ -r "$NODE" ]; then
        NATIVE=$(cat "$NODE" 2>/dev/null)
    fi
    if [ -n "$NATIVE" ]; then
        NS=$(field status)
        AGE=$(field age_seconds)
        RAW_SOC=$(field soc_unfiltered_pct)
        RAW_FCC=$(field fcc_unfiltered_mAh)
        RAW_RM=$(field remaining_unfiltered_mAh)
    else
        NS=unavailable; AGE=NA; RAW_SOC=NA; RAW_FCC=NA; RAW_RM=NA
    fi
    UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null)
    printf '%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n' \
        "$UTC" "$ST" "$TYPE" "$ONLINE" "$SOC" "$BQ" "$QC" "$TEMP" "$VOLT" "$CURRENT" \
        "$FCC" "$DESIGN" "$COUNTER" "$RM" "$DASH" "$DASH_START" \
        "$NS" "$AGE" "$RAW_SOC" "$RAW_FCC" "$RAW_RM" >> "$CSV"
    log "sample=$idx/$SAMPLES status=$ST usb=$TYPE soc=$SOC bq=$BQ qc=$QC temp_decic=$TEMP current_uA=$CURRENT native=$NS raw_soc=$RAW_SOC"
    if [ "$idx" -eq 1 ] || [ "$idx" -eq "$SAMPLES" ]; then
        {
            printf '\n=== Native snapshot at sample %s ===\n' "$idx"
            if [ -n "$NATIVE" ]; then printf '%s\n' "$NATIVE"; else echo 'Native kernel endpoint unavailable on running kernel.'; fi
        } >> "$TXT"
    fi
    case "$TEMP" in
        ''|*[!0-9]*) : ;;
        *) if [ "$TEMP" -ge 420 ]; then
            log 'HIGH TEMPERATURE >=42 C: ending log. Logging stopped ONLY; charger is NOT disconnected. Unplug charger manually if hot.'
            break
           fi ;;
    esac
    [ "$idx" -ge "$SAMPLES" ] && break
    idx=$((idx + 1))
    sleep "$INTERVAL"
done
log 'DONE - raw sysfs telemetry is not independent laboratory capacity calibration.'
