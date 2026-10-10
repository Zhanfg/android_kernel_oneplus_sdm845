# OnePlus 6 / enchilada — Android 17 TWRP port, experimental source

This is a **real device-tree and build integration work-in-progress**, not a finished TWRP recovery image.

Recovery userspace: nebrassy TWRP AOSP 14 (`twrp-14`); older TeamWin OnePlus6 `android-11` is only a device reference. Kernel: pinned successful `4.19.325` BakaSU `Image.gz-dtb` from workflow `38043895739`, repacked to 4.19 donor's DTB order by job `38047144934`.

**Critical mismatch**: user-provided `/mnt/data/boot.img` is Linux **4.9.337** with legacy ext4 `fileencryption=ice` recovery.fstab. It is **not** the `4.19` Android17 production boot image. The 4.19 AK3's FDT hashes **do not match** the 4.9 boot FDTs, so do not use the 4.9 image to assert that a 4.19 recovery can boot. The prior analysis suggesting EROFS/FBEv2 were inside this boot image was incorrect. The source carries two mutually exclusive fstab templates; neither proves current running ROM partition layout.

### Safe gates
1. Build source tree and inspect `boot.img` on host, without flashing.
2. Validate ROM's actual init fstab and `androidboot.super_partition` on phone using the parameterless read-only probe.
3. Only when donor kernel boots AND boot image/AVB has been validated: `fastboot boot twrp_enchilada_boot.img` from external host (never `fastboot flash recovery`).
4. Test GUI, touchscreen, adb, userspace fastbootd, block device mappings and read-only access; **never wipe/format** while encryption unavailable.
5. FBE/Keymaster for Android17 is disabled by default, not magically solved by building Android14 TWRP.
6. No permanent flashable image or AK3 is authorized until actual device test of this candidate.

### Rebuild instructions (Android host)
```
repo init --depth=1 -u https://github.com/nebrassy/platform_manifest_twrp_aosp -b twrp-14
repo sync -c -j4 --no-tags --no-clone-bundle
cp -a this-tree/device/oneplus/enchilada device/oneplus/
mkdir -p device/oneplus/enchilada/prebuilt
unzip -p android17-ak3.zip Image.gz-dtb > device/oneplus/enchilada/prebuilt/Image.gz-dtb
. build/envsetup.sh
lunch twrp_enchilada-eng
m -j4 bootimage
```
`bootimage` is the output because this is Recovery-as-Boot. The compilation can fail on unresolved 14.x/TWRP API or device-blob dependencies; CI records the failure rather than fabricating a binary. Boot image must be <= 64 MiB and v1; AVB is not signed in this preflight.