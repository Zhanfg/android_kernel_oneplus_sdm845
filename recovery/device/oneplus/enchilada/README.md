# OnePlus 6 / enchilada — Android 17 TWRP 14 recovery port, G1

Actual uploaded `boot.img` SHA-256 `6b305cace01270c797c7ad44a1457154ec91667227ce1e4b35be49156d940a0e` **is Linux 4.19.325-cip136**, boot header v1 and 64 MiB. Its recovery cpio uses **EROFS+logical** `system`/`vendor`/`odm`, ext4 `/metadata` backed by `logdump`, and `/data` `fileencryption=aes-256-xts:aes-256-cts:v2`. Current default fstab follows the observed 4.19 ROM. The old extracted 4.9.337 image was a stale sidecar from an earlier boot and is deliberately not used here.

The compiled BakaSU 4.19 kernel is reused unchanged from successful AK3 job `38047144934`; its 3 appended DTBs are verified to match the **current 4.19 boot.img's** DTBs. TWRP14 userspace is built independently from `nebrassy/platform_manifest_twrp_aosp` `twrp-14`. This build is experimental until CI emits a valid `boot.img` and device host performs temporary boot and functional testing.

## Safety
- `recovery.fstab` is the selected *actual 4.19 retrofit* profile. Sensitive partitions deliberately mount read-only and `formattable` is removed; no flash/wipe is authorized.
- `recovery-legacy.fstab` is only for the earlier **different** 4.9.337 donor image; do not select it on this 4.19 ROM.
- `TW_INCLUDE_CRYPTO=false`, so `/data` decryption is **not supported** in this candidate, despite `fileencryption=...` describing on-disk data.
- Do NOT run `fastboot flash recovery`, `fastboot flash boot` or any persistent installer based on this G1 port; first validate temporary `fastboot boot` with external host and existing recovery/boot backup.
- The 4.19 ROM fstab had `formattable` in it, but this recovery prototype does **not** inherit any formatter privileges by default.
- Android 14 TWRP userspace may lack Android 17 FBE HAL compatibility. A compiled binary is not a stable daily recovery.

See root README for GitHub CI steps and source snapshot.