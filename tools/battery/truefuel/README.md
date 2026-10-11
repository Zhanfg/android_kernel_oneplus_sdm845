# OP6 TrueFuel v0.4 — 4.19.325 native telemetry + readonly LKM

**Experiment only — no automatic flash, no DataFlash writes, no current increases.**
OnePlus 6 / Android 17 uwuAOSP / 4.19.325 BakaSU.
The production kernel is **NOT** updated by this branch.

## Device-grounded observations (2026-10-11)
- BQ27411 (chip code 0x0421) at `0-0055`.
- User `bms/bq_soc=43%` (chip-filtered), OnePlus-smoothed `bms/capacity=43%`, Qualcomm FG `real_capacity=35%`.
- `bms/charge_full=3139000 µAh`; `bms/charge_full_design=3240000 µAh`.
- `bms/remaining_capacity=0` with 43% SOC was explained by OEM returning an uninitialized local 0 when reading was disabled. **v0.4 caches the last successful reading without inventing a 4500mAh value**. The cache is zero until the first real read.
- Battery was ~40.2°C discharging. No acceleration of charging may be inferred.

## Native demand-driven measurement (v0.4)
- The OEM 12-second discharge poll already opens a short BQ reading window. Almost all other periods have `allow_reading=false`, so synchronous sysfs register access normally returns `-EAGAIN`.
- The native driver now offers `/sys/bus/i2c/devices/0-0055/op6_truefuel_hw` as a root-only (0400) **demand-driven snapshot**. It makes *zero hardware I2C calls during a sysfs read*.
- First read returns `status=pending`. A request bit makes the **next normal discharge poll** sample the filtered/unfiltered SOC (0x1c/0x30), RM (0x0c/0x28), FCC (0x0e/0x2c), and DesignCapacity (0x3c). During charging, Dash, smoothing, suspend or invalid hardware state it will not force a sample.
- Subsequent reads return the cached snapshot and sample age; a read after 60 seconds marks it `stale` and queues a one-shot refresh for a later safe poll.
- No timer, daemon, independent I2C adapter, control register write, HAL override or SOC spoof.
- The LKM reads only existing `power_supply` data; it **cannot** expose the new snapshot until a kernel that includes the native patch is built and installed.

## Verified VENDOR facts from user's logical EROFS vendor.img
- The 369344512-byte EROFS image matches the phone's 2026-09-29 A17 build identity. Superblock CRC32C and AVB Vendor hash tree match the supplied signed vbmeta descriptors. This verifies file data, **not** device bootloader key trust.
- VINTF declares AIDL Android `android.hardware.health.IHealth/default`; executable `/vendor/bin/hw/android.hardware.health-service.qti`. The runtime HAL is not automatically proved healthy merely by the binary's presence.
- Separate Lineage AIDL health declares `IChargingControl/default` and `IFastCharge/default` serviced by `/vendor/bin/hw/vendor.lineage.health-service.default`. Do not confuse these *charging controls* with battery SOC calibration.
- `/vendor/bin/dashd` exists but its active state and Dash MCU link have not been validated.
- Current physical `vendor_a.img` was outdated/malformed EXT4, **not** the mounted logical EROFS VENDOR. Do not flash the physical dump.
- Physical `odm_a.img` did not match its current signed VBMETA hashtree: do not use it as a flash source.
- The AOSP HealthInfo API reports `batteryLevel` (%) and `batteryFullChargeDesignCapacityUah` (µAh) separately; a 4500mAh metadata figure does **not** calibrate the actual chip state-of-charge.

## Active kernel ABI and CI build gate
- CI on earlier commit `5a6245762072` **succeeded**: Actions run `38121789524`.
- That `.ko` has `vermagic=4.19.325-cip136-st20-perf-g5a6245762072-dirty`.
- The user's boot-tested v0.2 kernel had `uname -r=4.19.325-cip136-st20-perf-g9ad0027fcccb-dirty`.
- **NOT load-compatible by vermagic; MODVERSIONS CRCs may also differ. Do not patch strings or force-load this KO.**
- New commits will trigger a new kernel+module build. A CI success is only source validation, not hardware acceptance.

## Real 4500mAh work remains gated
1. Confirm actual replacement cell's datasheet, nominal/max charging voltage, thermistor, Chemistry ID and pack safety limits.
2. Read current BQ device model, ChemID and safely backup DataFlash with an authorized, validated protocol before proposing **any** non-volatile gauge write.
3. Compare physical voltage/current, remaining capacity and real charge/discharge curve to the gauge model.
4. Prepare signed-image provenance and a boot-tested rollback path before enabling a production kernel.
5. Keep branch isolated; do not merge into stable while no phone verification.

**Primary references**: TI BQ27411-G1 TRM SLUUAS7B; AOSP Health HAL AIDL `HealthInfo.aidl`.