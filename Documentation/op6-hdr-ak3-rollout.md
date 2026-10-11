# OnePlus 6 / uwuAOSP Android 17: AK3 HDR release integration

## User-facing target

A single **existing OnePlus 6 BakaSU/ReSukiSU AK3 release** will distribute
the certified HDR vendor component and enable the native ROM Settings switch
**Settings → Display → 允许原生 HDR 内容**. Enabling the switch permits HDR
content (PQ/HLG) and does **not** force all SDR material into HDR.

This is a future release target, not the current build's claim.

## Repository roles

| Area | Branch / PR | Scope |
|---|---|---|
| Qualcomm HWC | [vendor PR #9](https://github.com/Zhanfg/platform_vendor_uwu/pull/9) | Correct legacy RenderIntent=-1 parsing for verified OnePlus6 modes |
| System Settings | [Settings PR #2](https://github.com/Zhanfg/platform_packages_apps_Settings/pull/2) | AOSP 17 per-display HDR_PREFERENCE_HDR_ALLOWED / SDR_ONLY switch |
| AK3 distribution | [kernel PR #21](https://github.com/Zhanfg/android_kernel_oneplus_sdm845/pull/21) | Add-on staging, hash/architecture checks, recovery distribution |

## Why it is not a kernel patch

Current SOFEF00_M DSI/DRM panel metadata is already present. The identified
blocking issue is the Qualcomm Vendor Composer color-mode parser. No LKM can
change that parser, and changing BOOT/DTBO/HBM is not the first-line fix.

## Current AK3 stage

The AnyKernel3 package contains `op6-hdr/COMPONENT_INFO.txt` and Chinese
instructions. Unless a companion module ZIP, its archive SHA256 and the
Composer ELF SHA256 are explicitly provided at BUILD TIME, no HDR binary
is packaged. If present, the ZIP is checked for safe paths, module ID,
the exact intended composer ELF path, and AArch64 ELF64 architecture.
It is retained as an unverified, nested companion and is **not installed
automatically**. Existing BOOT installation remains unchanged.

These checks establish integrity, not full ABI compatibility or device safety.

## Final AK3 one-step activation: must meet all gates

1. Lock the **actual uwuAOSP 101** ROM revision, device/vendor trees and
   composer source commit, not merely upstream branch names.
2. Build the corrected `vendor.qti.hardware.display.composer-service`
   using the matching Android 17 Soong toolchain.
3. Compare the candidate ELF with the device's original using
   `vendor/uwu/patches/enchilada/hdr/tools/verify_composer_abi.py`, then
   check unresolved symbols, service RC, vendor library compatibility,
   VINTF matrix and SELinux contexts.
4. Confirm the candidate Vendor HAL can boot, enumerate native/sRGB/P3/PQ/HLG
   modes, and perform HDR PQ/HLG switching without broken SDR colors.
5. Build the Settings source **as part of the matching ROM** or supply a
   platform-signed, permission-compatible Settings update; AK3 alone cannot
   safely inject Java source into the existing Settings APK. Never replace
   a ROM Settings APK with an unmatched signature.
6. Validate KernelSU/Magisk vendor-file systemless mount timing **before**
   the compositor service launches. If the mount is too late or unavailable,
   use a compatible Vendor OTA rather than silently injecting runtime hacks.
7. Prove device recovery path: safe-mode module disable, rollback to
   original Composer, no black screen at boot, persistent SDR fallback.
8. Only after these gates pass, replace the passive companion with the
   tested install path and mark the AK3 HDR feature available.

## Current safety and acceptance

No stage must interpret `isHdr()` or reported formats as proof of actual HDR
optical output. Android 17's per-display setting is meaningful only when
HWC has operational HDR output. Until then its controller is gated against
the current NATIVE-only Composer state.

**Current status: SOURCE TESTED / AK3 CONTRACT TESTED.
NOT HWC-BINARY VERIFIED. NOT SETTINGS-APK VERIFIED. NOT DEVICE VERIFIED.**
