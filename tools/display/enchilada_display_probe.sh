#!/system/bin/sh
# OnePlus 6 Android 17 display diagnostic. Read-only, no args, no root required.
# It does not force panel modes, HDR flags, refresh rates or brightness.
PATH=/system/bin:/system/xbin:/vendor/bin:/product/bin:/sbin:$PATH
DEST=/sdcard/Download
[ -d "$DEST" ] || DEST=.
TS=$(date +%Y%m%d_%H%M%S 2>/dev/null)
[ -n "$TS" ] || TS=unknown
OUT="$DEST/OP6_HDR_Refresh_Probe_$TS.txt"
umask 077

report() {
    echo "===== $1 ====="
}
prop() {
    value=$(getprop "$1" 2>/dev/null)
    echo "$1=$value"
}
safe_command() {
    title="$1"
    shift
    report "$title"
    "$@" 2>&1 || echo "command unavailable / permission denied"
}

{
    echo "OnePlus 6 HDR / physical refresh / color capability PROBE"
    echo "Read only. Unknown output is not proof of absent hardware capabilities."
    report "Device"
    for k in ro.product.device ro.product.model ro.build.version.sdk ro.build.id ro.boot.slot_suffix ro.hardware; do
        prop "$k"
    done
    report "Kernel"
    uname -r

    report "HDR Settings state (null = unset, not disabled)"
    for name in hdr_brightness_enabled hdr_brightness_boost_level; do
        printf '%s=' "$name"
        settings get secure "$name" 2>/dev/null || echo "unavailable"
    done
    report "SurfaceFlinger HDR/wide color property declarations (not proof of output)"
    for k in ro.surface_flinger.has_HDR_display \
             ro.surface_flinger.has_wide_color_display \
             ro.surface_flinger.use_color_management \
             vendor.display.disable_hdr; do
        prop "$k"
    done
    report "Android HDR / SDR ratio hints (missing = unknown)"
    dumpsys display 2>/dev/null |
        grep -i -E 'hdrsdr|hdr.sdr|hdr.*ratio|sdr.*ratio|hdr.*supported|hdr.*disabled|hdr.*conversion' |
        head -n 75 || :
    echo "Display.isHdrSdrRatioAvailable() must be checked by a framework API caller."
    echo "An HDR formats list alone does NOT enable HDR brightness settings."

    safe_command "Display service (prefer capability modes)" dumpsys display
    safe_command "SurfaceFlinger display capability snapshot" dumpsys SurfaceFlinger --displays
    report "SurfaceFlinger short mode and HDR output"
    if command -v dumpsys >/dev/null 2>&1; then
        dumpsys SurfaceFlinger 2>/dev/null |
            grep -i -E 'hdr|color.?mode|refresh.?rate|vsync|display.?mode|supported.?mode' |
            head -n 180 || :
    fi

    report "Legacy framebuffer and DRM modes"
    for f in /sys/class/graphics/fb0/modes /sys/class/graphics/fb0/msm_fb_panel_info /sys/class/graphics/fb0/panel_name /sys/class/drm/card*-*/modes; do
        [ -r "$f" ] || continue
        echo "PATH: $f"
        head -n 60 "$f" 2>&1 || :
    done

    report "Reported refresh-rate settings (not proof of physical panel mode)"
    for n in min_refresh_rate peak_refresh_rate user_refresh_rate; do
        printf '%s=' "$n"
        settings get system "$n" 2>&1 || :
    done

    report "HDR/codec declarations in media codec configuration"
    for f in /vendor/etc/media_codecs.xml /vendor/etc/media_codecs_performance.xml /vendor/etc/media_codecs_vendor.xml /vendor/etc/media_codecs_google_video.xml /system/etc/media_codecs.xml; do
        [ -r "$f" ] || continue
        echo "CONFIG: $f"
        grep -i -E 'hdr|hevc|main10|vp9|color-format' "$f" | head -n 35 || :
    done

    report "Read-only panel driver indicators"
    for root in /sys/class/drm /sys/class/graphics; do
        [ -d "$root" ] && ls "$root" 2>/dev/null | head -n 80 || :
    done
    report "Footer"
    echo "Do not infer hardware 10-bit HDR from DTS flags or app decoder profiles alone."
    echo "Do not infer hardware variable refresh from 24/30fps video playback."
} > "$OUT" 2>&1
echo "Saved: $OUT"
