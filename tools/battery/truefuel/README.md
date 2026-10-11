# OP6 TrueFuel v0.2 — BQ27411 hardware SOC (source-only until build verified)

**Scope**: OnePlus 6 enchilada, Android 17, BakaSU Linux 4.19.325; no modifications to `boot.img`, charge limits, JEITA, OTP or gauge DataFlash.

## Evidence from phone (2026-10-11)

- DeviceType `0x0421` = BQ27411; firmware `0x0109`; I²C bus `0-0055`.
- `bms/bq_soc=43` and Android `battery/capacity=43`; Qualcomm FG `real_capacity=35`.
- TI reported `charge_full=3,139,000µAh`; `charge_full_design=3,240,000µAh`; `remaining_capacity=0` while SOC=43, **so remaining capacity is not trustworthy until independent readback**.
- Temperature 40.2°C while discharging; Dash / charging-current validation is not covered by this snapshot.
- Kernel disables `CONFIG_KPROBES`, enables `CONFIG_MODULES` and `CONFIG_MODVERSIONS`, module signatures disabled in this confirmed v0.2 boot. Do not confuse with older ABK kernel's module-signing policy.

## Correct SOC distinctions

OEM `bms/capacity` is OnePlus **software-smoothed** BQ SOC. `bms/bq_soc` bypasses that path but reads the chip's **filtered** StateOfCharge() at register 0x1c.

The TI BQ27411-G1 Technical Reference Manual SLUUAS7B provides **StateOfChargeUnfiltered()** at register `0x30`. This revision's read-only LKM exposes filtered vs unfiltered SOC, remaining-capacity and FCC (also their unfiltered forms), and DesignCapacity() `0x3c`. The module will access direct I²C **only when discharging with USB disconnected**, never during Dash/charging or if battery state is unknown.

Reference: https://www.ti.com/lit/ug/sluuas7b/sluuas7b.pdf

## Integration plan — what is and isn't implemented

The active built-in BQ driver exposes DesignCapacity() `0x3c` through `get_batt_design_capacity()`, which becomes `bms/charge_full_design`. Therefore *updating the gauge Design Capacity* should update Android's advertised design capacity on this kernel, **if the chip accepts and retains the correct update**. No Android UI overlay is required for this capacity metadata.

However, **this module does not modify any property, perform DataFlash writes, or switch Android's displayed SOC**. Direct register telemetry is not SOC calibration. Hardware adaptation to 4500mAh requires validating the replacement cell's nominal/max voltage, actual chemistry profile, termination behavior and DataMemory design energy; then a backup/readback-verified, chip-specific supervised calibration followed by learning and field validation. Do not invent FCC=4500.

## Build and safety gates

Actions: `.github/workflows/enchilada-truefuel-lkm.yml` builds exact BakaSU kernel `Module.symvers` and a CRC-matched `op6_truefuel.ko`. The source is at `tools/battery/truefuel/op6_truefuel.c`. Load manually only after CI **success** and exact running kernel identity; no automatic module load.

- [ ] LKM build, modversions and ARM64 vermagic validation
- [ ] Manual insmod + unload on phone and I²C sampling
- [ ] Compare 0x30 unfiltered / 0x1c filtered / BMS SOC / 0x3c DesignCap
- [ ] Check battery label/spec, BQ ChemID and data-memory backup
- [ ] Independently validate BQ updates and battery safety, with rollback
- [ ] Only then consider SOC policy adjustment and high-current charging testing

Keep PR draft; never merge until phone validation.
