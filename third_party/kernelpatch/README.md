# Official KernelPatch snapshot (review only)
The files below lkm/ and kernel/ are exact, GPL-licensed copies of official
https://github.com/bmax121/KernelPatch at commit `f36f3d1377004871f8c964f7cd3276712eeba943`
(October 10 2026). License and attribution remain with upstream.
This is a **nonexecuting source snapshot**, **not** an APatch/KernelPatch root
manager and not a KPM loader wired into the OnePlus 6 kernel.

Canonical pin and per-file blob SHAs: UPSTREAM_MANIFEST.json.
Check locally: `python3 tools/check_op6_kernelpatch_snapshot.py`.
Update: `python3 tools/sync_op6_kernelpatch.py --update`
(separate review PR only, GitHub CI never merges automatic changes).

CAUTION: upstream LKM contains independent privileged su / syscall 45,
APatch signature scanning and manager code. None of those are to be imported
into our KSU/BakaSU runtime. Only ELF KPM loader, ARM64 relocations, trampoline
and hooks should be adapted, with a fail-closed 4.19-specific KSU authorization
boundary.
