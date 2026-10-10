#!/usr/bin/env python3
"""Read-only validation of Android libperfmgr-style powerhint.json.

Never applies or recommends a new clock, thermal, or cpuset setting automatically.
Accepts JSON with trailing commas/comments as used by some ROM build trees.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def relaxed_json(text: str) -> dict:
    # Preserve string literals and escape sequences while removing comments and
    # trailing commas. This avoids silently damaging paths containing slashes.
    buf: list[str] = []
    i = 0
    quote = False
    escaped = False
    while i < len(text):
        c = text[i]
        if quote:
            buf.append(c)
            if escaped:
                escaped = False
            elif c == "\\":
                escaped = True
            elif c == '"':
                quote = False
            i += 1
            continue
        if c == '"':
            quote = True
            buf.append(c)
            i += 1
            continue
        if text.startswith("//", i):
            until = text.find("\n", i)
            i = len(text) if until < 0 else until
            continue
        if text.startswith("/*", i):
            until = text.find("*/", i + 2)
            if until < 0:
                raise ValueError("unterminated JSON block comment")
            i = until + 2
            continue
        if c == ",":
            j = i + 1
            while j < len(text) and text[j].isspace():
                j += 1
            if j < len(text) and text[j] in "}]":
                i += 1
                continue
        buf.append(c)
        i += 1
    obj = json.loads("".join(buf))
    if not isinstance(obj, dict):
        raise ValueError("top-level powerhint policy must be a JSON object")
    return obj


def audit(policy: dict) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    nodes: dict[str, dict] = {}
    seen_paths: dict[str, str] = {}
    entries = policy.get("Nodes")
    actions = policy.get("Actions")
    if not isinstance(entries, list) or not isinstance(actions, list):
        return ["Nodes and Actions must both be arrays"], warnings

    for n in entries:
        if not isinstance(n, dict):
            errors.append("node entry is not an object")
            continue
        name = n.get("Name")
        values = n.get("Values")
        path = n.get("Path")
        if not isinstance(name, str) or not name:
            errors.append("node has missing Name")
            continue
        if name in nodes:
            errors.append(f"node {name!r} defined more than once")
        if not isinstance(values, list) or not values:
            errors.append(f"node {name}: Values missing or empty")
            continue
        if len(set(str(v) for v in values)) != len(values):
            warnings.append(f"node {name}: repeated value")
        if not isinstance(path, str) or not path:
            errors.append(f"node {name}: missing Path")
        elif path in seen_paths and seen_paths[path] != name:
            warnings.append(f"nodes {seen_paths[path]} and {name} share resource {path}; confirm conflict arbitration")
        else:
            seen_paths[path] = name
        idx = n.get("DefaultIndex")
        if idx is not None and (not isinstance(idx, int) or idx < 0 or idx >= len(values)):
            errors.append(f"node {name}: invalid DefaultIndex={idx!r}")
        if idx is None and n.get("ResetOnInit") is True and n.get("Type") != "Property":
            warnings.append(f"node {name}: ResetOnInit without explicit DefaultIndex; validate real reset behavior")
        nodes[name] = n

    duplicates: set[tuple[str, str]] = set()
    for a in actions:
        if not isinstance(a, dict):
            errors.append("action entry is not an object")
            continue
        hint, node, value, duration = (a.get(k) for k in ("PowerHint", "Node", "Value", "Duration"))
        if not isinstance(hint, str) or not hint:
            errors.append("action lacks PowerHint")
            continue
        if node not in nodes:
            errors.append(f"hint {hint}: references unknown node {node!r}")
            continue
        n = nodes[node]
        if str(value) not in [str(v) for v in n.get("Values", [])]:
            errors.append(f"hint {hint} -> {node}: value {value!r} absent from Node.Values")
        if not isinstance(duration, int) or duration < 0:
            errors.append(f"hint {hint} -> {node}: Duration must be nonnegative integer")
            continue
        key = (hint, node)
        if key in duplicates:
            errors.append(f"hint {hint} -> {node}: duplicate binding")
        duplicates.add(key)
        if hint in ("INTERACTION", "LAUNCH") and duration == 0:
            warnings.append(f"{hint} -> {node}: duration=0 requires a reliable explicit end/stop lifecycle; not an instantaneous hint")
        if "LAUNCH" in hint and duration > 2000 and node in (
            "GPUForceClkOn", "GPUForceRailOn", "GPUIdleTimer", "PMQoSCpuDmaLatency", "SchedBoost"):
            warnings.append(f"{hint} -> {node}: prolonged {duration} ms boost/rail/latency request; A/B test shorter bounded hint before changing")
        if "CPU" in str(node) and "MinFreq" in str(node) and str(value) == "9999999":
            warnings.append(f"{hint} -> {node}: '9999999' as MIN frequency needs kernel sysfs semantics check, not interpreted as a hardware frequency")
    return errors, warnings


def report(path: Path) -> str:
    obj = relaxed_json(path.read_text(encoding="utf-8-sig"))
    errs, warns = audit(obj)
    out = [f"PowerHint source audit: {path.name}",
           f"nodes={len(obj.get('Nodes', []))}, actions={len(obj.get('Actions', []))}",
           f"errors={len(errs)}, review_warnings={len(warns)}"]
    out += ["ERROR: " + s for s in errs]
    out += ["REVIEW: " + s for s in warns]
    out += ["Result: " + ("INVALID CONFIG" if errs else "STRUCTURALLY VALID (runtime and performance NOT verified)")]
    return "\n".join(out) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("powerhint_json", type=Path)
    args = ap.parse_args()
    print(report(args.powerhint_json), end="")
    errors, _ = audit(relaxed_json(args.powerhint_json.read_text(encoding="utf-8-sig")))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()