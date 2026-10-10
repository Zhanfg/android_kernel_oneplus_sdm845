# OnePlus 6 (enchilada): TWRP Recovery on Android 17 / Linux 4.19

**2026-10-10: static feasibility review. No TWRP port or flashable ROM is produced here.**

## Bottom line

The stock SDM845 A/B bootloader uses **Recovery-as-Boot**, not a separately addressable GPT `recovery` partition. Retrofit dynamic partitions are distinct from A/B: they expose logical system/vendor/odm devices through Linux device mapper, not a new bootloader-loadable recovery image.

**Viable**: independent full TWRP recovery *environment* (GUI/ADB/fastbootd), booting through existing `boot_a` / `boot_b` in recovery mode and sharing an unchanged tested Linux 4.19 kernel and root integration.

**Not supported by the factory bootloader**: adding `recovery` under a retrofit dynamic `super` arrangement and expecting fastboot or recovery-mode bootloader dispatch to jump to it. Avoid risky repartitioning, using a spare A/B slot as permanent recovery, and running `fastboot flash recovery`.

## Evidence collected from the user-provided boot.img (never committed)

| Property | Measured, read-only |
|---|---|
| Android boot header | v1 |
| Boot image size | 64 MiB |
| Kernel segment | 22,342,066 bytes |
| gzip recovery Ramdisk | 16,469,684 bytes, ~37.87 MB decompressed |
| Existing recovery userland | `system/bin/recovery`, `system/bin/fastbootd`, 596 cpio entries |
| Existing fstab | `system/etc/recovery.fstab` present |
| Dynamic file systems | `system`, `vendor`, `odm`: EROFS, logical, slotselect and first-stage mount |
| User data | ext4, `fileencryption=aes-256-xts:aes-256-cts:v2` |
| Metadata | `/metadata` is provided by the physical `logdump` partition (do not repurpose it) |
| Verified Boot | AVB footer `AVBf` v1.0 present, embedded vbmeta location declared |

These observations establish that the existing boot image already contains a **complete AOSP Recovery**. The goal is replacing or extending **recovery-mode userspace**, not manufacturing a new GPT bootloader entry. A new TWRP recovery image must correctly rebuild boot-header fields, images, and AVB footer; the padded 64 MiB region after the old Ramdisk is **not** a free licence to concatenate arbitrary images.

## Critical upstream compatibility limitation

The [TeamWin device page](https://twrp.me/oneplus/oneplus6.html) lists OnePlus 6 as supported, but its [official download list](https://dl.twrp.me/enchilada/) presently ends at **TWRP 3.7.0_11-0 from 2022-10-04**, based on an Android 11 recovery tree. The official [TeamWin device tree](https://github.com/TeamWin/android_device_oneplus_enchilada) is also on `android-11`. The official TWRP `fastboot boot twrp.img` path is appropriate **for testing**, not proof that this old binary mounts the current ROM's retrofit dynamic/EROFS layout or decrypts FBE v2. TeamWin explicitly states that modern FBE decryption support is device-and-OEM-specific and may require unavailable vendor interfaces.

Other ROMs' retrofit dynamic installation guides explicitly warn that their packaged TWRP does not support that ROM's layout (example: [crDroid 11 enchilada](https://crdroid.net/enchilada/11/install)). The currently flashed ROM's fstab must be authoritative, not another ROM's partition assumptions.

## Stability-first implementation (not yet completed)

1. Keep working AOSP Recovery and known-good `boot.img` backups, active slot record, and fastboot restore route.
2. Build a **separate modern TWRP recovery userspace/device tree**, reusing the Android 17 ramdisk's recovery fstab and init semantics; compile matching kernel+FDT separately.
3. Implement mount handling for retrofit dm-linear `logical` / `slotselect`, EROFS read-only mounts, /metadata via `logdump`; retain ADB sideload and userspace `fastbootd`.
4. FBE v2 `/data` decrypt is a separately gated requirement; when unsupported, run read-only and never auto-format userdata.
5. Integrate without replacing the pinned BakaSU kernel/DTBs. Respect Android boot header v1, 64 MiB size, AVB footer and correct rollback behavior.
6. Test via **external host** `fastboot boot twrp.img`, not `fastboot flash recovery`. UI+touch alone is insufficient; validate ADB, read-only dynamic mounts, USB OTG, recovery logs, slot handling, crypto and fastbootd before writes.
7. Only after real-device success, consider a permanently installed unified Android 17 + TWRP + BakaSU `boot.img` / optional AK3, with OTA survival and repeated reboot tests.

## On-device read-only probe

The script `tools/OP6_A17_Recovery_Partition_ReadOnly.sh` accepts **no arguments**, produces a TXT file in `Download` or `/data/local/tmp`, and only reads non-sensitive A/B by-name links, logical mapper names, selected fstab flags, runtime version and file-system support. It does **not** mount, erase, repartition, flash, reboot, alter SELinux, or dump image/encryption keys.

## References

- https://source.android.com/docs/core/ota/ab/ab_implement
- https://source.android.com/docs/core/ota/dynamic_partitions/implement
- https://twrp.me/oneplus/oneplus6.html
- https://dl.twrp.me/enchilada/
- https://twrp.me/faq/encryptionsupport.html
- https://github.com/TeamWin/android_device_oneplus_enchilada
- https://crdroid.net/enchilada/11/install
