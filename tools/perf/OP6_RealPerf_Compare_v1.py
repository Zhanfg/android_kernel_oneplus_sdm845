#!/usr/bin/env python3
"""Compare two OnePlus 6 RealPerf v1 logs; never claims unmeasured FPS/speed."""
from __future__ import annotations

import argparse
import math
import statistics
from pathlib import Path

COLUMNS = (
    "phase index epoch cpu0_cur_khz cpu4_cur_khz cpu0_max_khz cpu4_max_khz "
    "gpu_cur_hz gpu_max_hz gpu_busy_pct gpu_max_pwrlevel gpu_thermal_pwrlevel "
    "cpu_thermal_max_raw gpu_thermal_max_raw skin_thermal_max_raw battery_temp_raw "
    "battery_current_now_raw cpu_psi10 memory_psi10 io_psi10 io_full10 "
    "memavail_kb swapfree_kb cpu_total_jiffies cpu_idle_jiffies "
    "pswpin pswpout pgmajfault workingset_refault"
).split()


def load(path: Path) -> tuple[dict[str, str], list[dict[str, str]]]:
    meta: dict[str, str] = {}
    samples: list[dict[str, str]] = []
    for lineno, raw in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if raw.startswith("META|"):
            _, key, *val = raw.split("|")
            meta[key] = "|".join(val)
        if raw.startswith("DATA|"):
            parts = raw.split("|")[1:]
            if len(parts) != len(COLUMNS):
                raise ValueError(f"{path.name}:{lineno}: expected {len(COLUMNS)} columns, found {len(parts)}")
            samples.append(dict(zip(COLUMNS, parts)))
    if meta.get("format") != "pipe-delimited-v1" or not samples:
        raise ValueError(f"{path.name}: not a complete RealPerf v1 dataset")
    if not path.read_text(encoding="utf-8-sig").rstrip().endswith("COMPLETE|" + str(path)):
        # Allow logs moved from Android to a new host path; original file name remains unchanged.
        last = path.read_text(encoding="utf-8-sig").splitlines()[-1]
        if not last.startswith("COMPLETE|"):
            raise ValueError(f"{path.name}: capture incomplete; do not compare")
    return meta, samples


def numbers(rows: list[dict[str, str]], key: str) -> list[float]:
    out = []
    for row in rows:
        try:
            value = float(row[key])
        except (ValueError, KeyError, TypeError):
            continue
        if math.isfinite(value):
            out.append(value)
    return out


def pctl(vals: list[float], fraction: float) -> float | None:
    if not vals:
        return None
    vals = sorted(vals)
    idx = (len(vals) - 1) * fraction
    low = int(idx)
    high = min(len(vals) - 1, low + 1)
    return vals[low] + (vals[high] - vals[low]) * (idx - low)


def cpu_load(rows: list[dict[str, str]]) -> float | None:
    # /proc/stat aggregate uses all eight CPUs, not per-app CPU time.
    if len(rows) < 2:
        return None
    try:
        total = float(rows[-1]["cpu_total_jiffies"]) - float(rows[0]["cpu_total_jiffies"])
        idle = float(rows[-1]["cpu_idle_jiffies"]) - float(rows[0]["cpu_idle_jiffies"])
    except ValueError:
        return None
    return 100 * max(0, min(1, (total - idle) / total)) if total > 0 else None


def counter_delta(rows: list[dict[str, str]], key: str) -> float | None:
    try:
        result = float(rows[-1][key]) - float(rows[0][key])
        return result if result >= 0 else None
    except (ValueError, IndexError, KeyError):
        return None


def f(value: float | None, unit: str = "", decimals: int = 1) -> str:
    return "n/a" if value is None else f"{value:,.{decimals}f}{unit}"


def compare(before: Path, after: Path) -> str:
    base_meta, base = load(before)
    new_meta, new = load(after)
    out = ["# OnePlus 6 performance comparison (read-only measurement)", ""]
    out.append(f"Before: {before.name} | After: {after.name}")
    out.append("This report compares device state; it does NOT measure FPS, app completion time, or power in mWh.")
    out.append("Sampling interval: 2 s, workloads must be reproduced manually.")
    for key in ("device", "android", "kernel", "cpu0_governor", "cpu4_governor"):
        a, b = base_meta.get(key, "?"), new_meta.get(key, "?")
        out.append(f"{key}: {a} -> {b}" + (" [changed]" if a != b else ""))
    out += ["", "## Per-phase medians and cumulative event deltas"]
    measures = [
        ("cpu_load", "CPU busy, overall", "%"),
        ("cpu0_cur_khz", "LITTLE frequency (median)", " kHz"),
        ("cpu4_cur_khz", "BIG frequency (median)", " kHz"),
        ("cpu0_max_khz", "LITTLE allowed maximum", " kHz"),
        ("cpu4_max_khz", "BIG allowed maximum", " kHz"),
        ("gpu_cur_hz", "GPU instantaneous frequency (median)", " Hz"),
        ("gpu_busy_pct", "GPU busy (median)", "%"),
        ("cpu_thermal_max_raw", "Max CPU zone raw (median)", " raw"),
        ("gpu_thermal_max_raw", "Max GPU zone raw (median)", " raw"),
        ("battery_temp_raw", "Battery temperature raw (median)", " raw"),
        ("cpu_psi10", "CPU PSI some avg10 (median)", "%"),
        ("memory_psi10", "Memory PSI some avg10", "%"),
        ("io_psi10", "I/O PSI some avg10", "%"),
        ("io_full10", "I/O PSI full avg10", "%"),
        ("memavail_kb", "Available RAM (median)", " KiB"),
        ("pswpin", "Swap-ins (period delta)", " events"),
        ("pswpout", "Swap-outs (period delta)", " events"),
        ("pgmajfault", "Major faults (period delta)", " events"),
        ("workingset_refault", "Workingset refault (period delta)", " events"),
    ]
    for phase in ("IDLE", "ACTIVE", "RECOVERY"):
        aa = [r for r in base if r["phase"] == phase]
        bb = [r for r in new if r["phase"] == phase]
        out += ["", f"### {phase} (samples: {len(aa)} / {len(bb)})", "Metric | Before | After | Difference (after-before)", "--- | ---: | ---: | ---:"]
        for key, title, unit in measures:
            def value(rows: list[dict[str, str]]) -> float | None:
                if key == "cpu_load":
                    return cpu_load(rows)
                if key in ("pswpin", "pswpout", "pgmajfault", "workingset_refault"):
                    return counter_delta(rows, key)
                x = numbers(rows, key)
                return statistics.median(x) if x else None
            a, b = value(aa), value(bb)
            delta = (b - a) if (a is not None and b is not None) else None
            out.append(f"{title} | {f(a, unit)} | {f(b, unit)} | {f(delta, unit)}")
        if len(aa) < 7 or len(bb) < 7:
            out.append("Warning: insufficient valid samples; interpretation limited.")
    out += ["", "## Interpretation rules", "",
            "- Frequency is not throughput. A lower CPU frequency under the same workload could mean improved efficiency OR throttling.",
            "- Pressure is not FPS. PSI and GPU utilization are workload/temperature dependent.",
            "- Sensor raw scales can differ; never convert CPU/skin temperatures without the sensor's documented units.",
            "- PSI avg10 is a smoothed window; early samples include prior phase activity.",
            "- Battery current_now is an instantaneous value; no net energy/mWh claim is possible from this sample.",
            "- A sustained performance improvement needs paired Perfetto FrameTimeline p95/p99 + the same app and workload, matched ambient/screen brightness, plus repeated runs.",
            "- Stable-release gate: normal thermal mitigation, no thermal override, no wakelocks, no bootloop or storage corruption."]
    return "\n".join(out) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("before", type=Path)
    ap.add_argument("after", type=Path)
    args = ap.parse_args()
    print(compare(args.before, args.after), end="")


if __name__ == "__main__":
    main()