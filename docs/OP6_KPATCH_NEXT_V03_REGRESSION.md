# OnePlus 6: KPatch-Next KPM crash root-cause investigation
**Status: active fault isolation; NO FIX OR FLASH CANDIDATE.**

## Reproduced facts
- Clean BakaSU v0.3 `719137c7` boots on OnePlus 6 Android 17.
- User independently reports KPatch-Next/KPM supports dynamic load and embed on v0.2, while v0.3 crashes and restarts into stock Recovery, for the same device.
- v0.2 and v0.3 have the same 16,469,684-byte ROM ramdisk; both use 4096-byte page size and ARM64 Boot header v1.
- Actual extracted ARM64 headers: v0.2 uncompressed Image 48,941,072 bytes, reservation 55,398,400 bytes; v0.3 uncompressed Image 48,955,408 bytes, reservation 55,414,784 bytes.
- Both compile KALLSYMS_ALL, Clang CFI and LTO, KFENCE and BakaSU manual hooks. These features are NOT v0.3-only regressions.
- KPatch-Next specifically changes early ARM64 entry, consults `paging_init`, rewrites PAC instructions around `tcp_init_sock`, and maps an executable hook region. Its static injection and dynamic KPM hooks are separate failure boundaries.
- Existing PR #23 adds native Re:Kernel, **not KPatch Next**. Existing PR #24 provides KPM ELF preflight only, no executable loader.

## CI audit
The separate workflow compares the actual v0.3 GitHub CI image with **pinned** official `KernelSU-Next/KPatch-Next@456744b2`, compiles actual `kptools` and ARM64 `kpimg`, patches, inspects and unpatches the image; collects symbol and patch offset logs without flashing anything. Kernel, root or ROM source is not modified.

Even if the offline patch/roundtrip passes, **this does not mean KPM is safe on real hardware**. KPM panic can occur after Boot during Hook execution or in module startup.

## Needed before claiming causality or a fix
- Identical KPatch-Next + kpimg build, nohello and ReKernel KPM versions for v0.2 and v0.3.
- Patch only the kpatch-next engine with *zero* KPM and verify Boot, then each KPM separately.
- Retrieve first kernel panic via `/sys/fs/pstore/console-ramoops*` or `/proc/last_kmsg`; collect unredacted Boot only via controlled private artifact.
- Compare official kptools patch logs for both kernel Images: KALLSYMS, `tcp_init_sock` mapping/PAC, `paging_init` relocation, header reservations and KPM symbols.
- Patch only the identified failure; preserve v0.3 power/network/DTBs, compile, run CI and real-device verify.

## Warnings
Neither a successful static patch nor a green kernel compile constitutes a successful phone boot. Continue using clean boot-tested v0.3; do not attempt additional KPM embedding before identifying the fault.
