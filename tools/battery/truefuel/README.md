# OP6 TrueFuel / BakaSU 4.19.325 (WIP)

This is **read-only LKM source**, not a prebuilt boot-compatible `.ko`. It does not alter battery capacity, charging current, thermal thresholds or DataFlash.

The confirmed user-boot-tested v0.2 image contains:
- `CONFIG_MODULES=y`, `CONFIG_MODVERSIONS=y`, `CONFIG_KALLSYMS_ALL=y`
- `CONFIG_MODULE_SIG=n`, `CONFIG_KPROBES=n`.
The older ABK tree has different module signing and Kprobe options; those configs **must not be conflated**.

The built-in `bms` supplies `BQ_SOC` (external BQ gauge, not OEM smooth SOC), `CAPACITY` (OnePlus smoothing), `REMAINING_CAPACITY`, `CHARGE_FULL`, and `CHARGE_FULL_DESIGN`. This module exposes those values via `/proc/op6_truefuel`, sampled only when read.

This source **does not** cause Android to show 4500mAh, and cannot honestly claim the cell has been reconfigured. The boot-tested kernel has the stock 3300mAh battery profile. Correct 4500mAh integration requires positive identification of the TI BQ variant, compatible cell profile, chipset DataFlash transaction and capacity learning, plus active-kernel integration. Do not hardcode FCC=4500. No bypass of JEITA/Dash/current protection.

To build: use EXACT v0.2 kernel source, identical `.config` and `Module.symvers`, then `make -C KERNEL_OUT M=$PWD ARCH=arm64 modules`. `CONFIG_MODVERSIONS=y` makes arbitrary `.ko` reuse unsafe.

The full source and no-args gauge probe are also packaged as `OP6_TrueFuel_LKM_v0.1_SOURCE_ONLY.zip`. The portable read-only probe runs on device without `.ko`.

**Gates:** full module build; vermagic/CRC; device `insmod`; BQ identity; raw versus OEM SOC; battery chemistry/design capacity; noninterference under charge/suspend; rollback. No merge until done.
