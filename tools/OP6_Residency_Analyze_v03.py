#!/usr/bin/env python3
"""Host-side diagnostic parser for OP6 v0.3 residency logs; never connects to phone.
No performance win is inferred from a single run. Zero I/O writes unless --json-out is given.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

PHASES = ("IDLE", "ACTIVE", "RECOVERY")

@dataclass
class PhaseSummary:
    phase: str
    duration_s: int | None
    samples: int
    little_high_residency_pct: float | None
    big_high_residency_pct: float | None
    little_mean_freq_khz: float | None
    big_mean_freq_khz: float | None
    cpu_some_psi_pct: float | None
    io_some_psi_pct: float | None
    memory_some_psi_pct: float | None
    cpu_thermal_max_raw: int | None
    battery_temp_max_raw: int | None
    gfx_total_frames_delta: int | None
    gfx_jank_frames_delta: int | None
    gfx_jank_pct: float | None
    warnings: list[str]


def number(text: str) -> int | None:
    try:
        return int(text)
    except (TypeError, ValueError):
        return None


def parse(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8", errors="replace")
    meta: dict[str, str] = {}
    times: dict[tuple[str, str], int] = {}
    tis: dict[tuple[str, str, str], dict[int, int]] = {}
    pressure: dict[tuple[str, str, str, str], int] = {}
    samples: dict[str, list[list[str]]] = {p: [] for p in PHASES}
    completed = False
    gfx: dict[str, tuple[str, int, int]] = {}

    for row in raw.splitlines():
        fields = row.split("|")
        kind = fields[0]
        if kind == "META" and len(fields) >= 3:
            meta[fields[1]] = "|".join(fields[2:])
        elif kind in ("PHASE_START", "PHASE_END") and len(fields) == 3:
            v = number(fields[2])
            if v is not None:
                times[(fields[1], "START" if kind.endswith("START") else "END")] = v
        elif kind == "TIS" and len(fields) == 6:
            phase, edge, policy, freq, t = fields[1:]
            fv, tv = number(freq), number(t)
            if fv is not None and tv is not None:
                tis.setdefault((phase, edge, policy), {})[fv] = tv
        elif kind == "PSI" and len(fields) == 6:
            phase, edge, resource, mode, total = fields[1:]
            val = number(total)
            if val is not None:
                pressure[(phase, edge, resource, mode)] = val
        elif kind == "GFX" and len(fields) == 5:
            edge, target, frames, jank = fields[1:]
            fv, jv = number(frames), number(jank)
            if edge in ("START", "END") and fv is not None and jv is not None:
                gfx[edge] = (target, fv, jv)
        elif kind == "SAMPLE" and len(fields) >= 12 and fields[1] in samples:
            samples[fields[1]].append(fields)
        elif kind == "COMPLETE" and len(fields) == 2:
            completed = True

    if meta.get("format") != "op6-v03-residency-1":
        raise ValueError(f"{path.name}: invalid/unrecognized v0.3 log format")
    if not completed:
        raise ValueError(f"{path.name}: log incomplete (no COMPLETE sentinel)")

    summaries = []
    for phase in PHASES:
        warnings = []
        start, end = times.get((phase, "START")), times.get((phase, "END"))
        duration = (end - start) if start is not None and end is not None and end > start else None
        if duration is None:
            warnings.append("no valid phase duration")

        def freq_summary(policy: str) -> tuple[float | None, float | None]:
            a, b = tis.get((phase, "START", policy), {}), tis.get((phase, "END", policy), {})
            common = set(a) & set(b)
            if not common:
                warnings.append(f"policy {policy}: missing time_in_state")
                return None, None
            # Frequency times can be reset after hotplug/reboot; refuse negative deltas.
            deltas = {f: b[f] - a[f] for f in common}
            if any(t < 0 for t in deltas.values()):
                warnings.append(f"policy {policy}: counters went backward; invalid measurement")
                return None, None
            total = sum(deltas.values())
            if total <= 0:
                warnings.append(f"policy {policy}: no residency increment")
                return None, None
            maxfreq = max(common)
            high = deltas[maxfreq] * 100.0 / total
            weighted = sum(freq * amount for freq, amount in deltas.items()) / total
            return round(high, 2), round(weighted, 1)

        lohi, loavg = freq_summary("0")
        bihi, biavg = freq_summary("4")

        def psi_summary(resource: str, mode: str = "some") -> float | None:
            startp = pressure.get((phase, "START", resource, mode))
            endp = pressure.get((phase, "END", resource, mode))
            if startp is None or endp is None or duration is None:
                return None
            if endp < startp:
                warnings.append(f"{resource}/{mode} PSI counter reset")
                return None
            frac = (endp - startp) * 100.0 / (duration * 1_000_000)
            if frac > 100.5:
                warnings.append(f"{resource}/{mode} PSI >100%; invalid timestamps")
                return None
            return round(frac, 3)

        dframes = djank = jankpct = None
        if phase == "ACTIVE" and "START" in gfx and "END" in gfx:
            x, y = gfx["START"], gfx["END"]
            if x[0] != y[0]:
                warnings.append("focused app changed between gfx snapshots")
            elif y[1] < x[1] or y[2] < x[2]:
                warnings.append("gfx frame counters reset between snapshots")
            elif y[1] > x[1] and y[2] - x[2] <= y[1] - x[1]:
                dframes, djank = y[1] - x[1], y[2] - x[2]
                jankpct = round(100.0 * djank / dframes, 2)
            else:
                warnings.append("gfx counters unchanged or inconsistent")
        elif phase == "ACTIVE":
            warnings.append("gfxinfo unavailable (optional)")

        thermal, battery = [], []
        for s in samples[phase]:
            if len(s) >= 11:
                a = number(s[8])
                b = number(s[9])
                if a is not None:
                    thermal.append(a)
                if b is not None:
                    battery.append(b)
        summaries.append(PhaseSummary(
            phase=phase,
            duration_s=duration,
            samples=len(samples[phase]),
            little_high_residency_pct=lohi,
            big_high_residency_pct=bihi,
            little_mean_freq_khz=loavg,
            big_mean_freq_khz=biavg,
            cpu_some_psi_pct=psi_summary("cpu"),
            io_some_psi_pct=psi_summary("io"),
            memory_some_psi_pct=psi_summary("memory"),
            cpu_thermal_max_raw=max(thermal) if thermal else None,
            battery_temp_max_raw=max(battery) if battery else None,
            gfx_total_frames_delta=dframes,
            gfx_jank_frames_delta=djank,
            gfx_jank_pct=jankpct,
            warnings=warnings,
        ))
    return {"file": path.name, "meta": meta, "phases": [asdict(v) for v in summaries], "complete": completed}


def main() -> None:
    ap = argparse.ArgumentParser(description="OnePlus 6 v0.3 residency / PSI host report, optional two-log comparison")
    ap.add_argument("logs", nargs="+", type=Path)
    ap.add_argument("--json-out", type=Path)
    args = ap.parse_args()
    if len(args.logs) > 2:
        ap.error("compare at most two logs for now")
    data = [parse(f) for f in args.logs]
    for log in data:
        print(f"\n{log['file']}: {log['meta'].get('kernel')} | {log['meta'].get('rom')} | charging={log['meta'].get('battery_status')}")
        for x in log["phases"]:
            print(f"  {x['phase']}: t={x['duration_s']}s, little@max={x['little_high_residency_pct']}%, "
                  f"big@max={x['big_high_residency_pct']}%, little_avg={x['little_mean_freq_khz']} kHz, "
                  f"big_avg={x['big_mean_freq_khz']} kHz, cpuPSI={x['cpu_some_psi_pct']}%, "
                  f"ioPSI={x['io_some_psi_pct']}%, heatRaw={x['cpu_thermal_max_raw']}, gfxJank={x['gfx_jank_pct']}%")
            if x["warnings"]:
                print("    unavailable/invalid: " + "; ".join(x["warnings"]))
    if len(data) == 2:
        print("\nCOMPARISON LIMIT: Results reflect measured residency/stalls only, not energy savings or frame-time gains.")
        ma, mb = data[0]["meta"], data[1]["meta"]
        for fld in ("device", "android", "rom", "battery_status", "cpu0_governor", "cpu4_governor"):
            if ma.get(fld) != mb.get(fld):
                print(f"WARNING: {fld} differs: {ma.get(fld)!r} vs {mb.get(fld)!r}")
        for a, b in zip(data[0]["phases"], data[1]["phases"]):
            if a["duration_s"] and b["duration_s"]:
                print(f"  {a['phase']} duration: {a['duration_s']}s vs {b['duration_s']}s")
    if args.json_out:
        args.json_out.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Saved host report: {args.json_out}")


if __name__ == "__main__":
    main()