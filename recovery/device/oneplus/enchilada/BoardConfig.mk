# Minimal OnePlus 6 TWRP recovery-as-boot board; independent of Lineage device tree.
DEVICE_PATH := device/oneplus/enchilada

TARGET_ARCH := arm64
TARGET_ARCH_VARIANT := armv8-a
TARGET_CPU_ABI := arm64-v8a
TARGET_CPU_ABI2 :=
TARGET_CPU_VARIANT := generic
TARGET_CPU_VARIANT_RUNTIME := kryo385
TARGET_2ND_ARCH := arm
TARGET_2ND_ARCH_VARIANT := armv8-a
TARGET_2ND_CPU_ABI := armeabi-v7a
TARGET_2ND_CPU_ABI2 := armeabi
TARGET_2ND_CPU_VARIANT := generic
TARGET_2ND_CPU_VARIANT_RUNTIME := kryo385

TARGET_BOARD_PLATFORM := sdm845
TARGET_BOOTLOADER_BOARD_NAME := sdm845
TARGET_NO_BOOTLOADER := true

# This kernel is extracted from the pinned, successful 4.19.325 BakaSU CI.
# We NEVER transplant the user-provided 4.9.337 boot.img kernel here.
TARGET_PREBUILT_KERNEL := $(DEVICE_PATH)/prebuilt/Image.gz-dtb
BOARD_KERNEL_IMAGE_NAME := Image.gz-dtb
BOARD_BOOT_HEADER_VERSION := 1
BOARD_KERNEL_BASE := 0x00000000
BOARD_KERNEL_PAGESIZE := 4096
BOARD_MKBOOTIMG_ARGS += --header_version $(BOARD_BOOT_HEADER_VERSION)
BOARD_KERNEL_CMDLINE := androidboot.configfs=true androidboot.hardware=qcom androidboot.usbcontroller=a600000.dwc3 androidboot.boot_devices=soc/1d84000.ufshc ehci-hcd.park=3 firmware_class.path=/vendor/firmware_mnt/image loop.max_part=7 lpm_levels.sleep_disabled=1 msm_rtb.filter=0x237 service_locator.enable=1 swiotlb=2048 androidboot.super_partition=system
BOARD_BOOTIMAGE_PARTITION_SIZE := 67108864
BOARD_DTBOIMG_PARTITION_SIZE := 8388608
BOARD_USES_RECOVERY_AS_BOOT := true
TARGET_NO_RECOVERY := true
TARGET_RECOVERY_PIXEL_FORMAT := BGRA_8888
TARGET_RECOVERY_FSTAB := $(DEVICE_PATH)/recovery/root/system/etc/recovery.fstab
BOARD_FLASH_BLOCK_SIZE := 262144

TARGET_USERIMAGES_USE_EXT4 := true
TARGET_USERIMAGES_USE_F2FS := true
TARGET_USES_MKE2FS := true
TARGET_USES_64_BIT_BINDER := true
BOARD_USES_QCOM_HARDWARE := true

# DO NOT implicitly enable AVB resigning; never flash this temporary boot image.
# AVB must be handled using *current target-ROM keys/policies* in a later stage.
BOARD_AVB_ENABLE := false

# Basic TWRP settings; avoid Qualcomm proprietary crypto/userdata assumptions.
TW_THEME := portrait_hdpi
TW_SCREEN_BLANK_ON_BOOT := true
TW_INPUT_BLACKLIST := "hbtp_vm"
TW_BRIGHTNESS_PATH := /sys/class/backlight/panel0-backlight/brightness
TW_NO_SCREEN_TIMEOUT := true
TW_EXCLUDE_DEFAULT_USB_INIT := false
TW_HAS_EDL_MODE := true
TW_USE_TOOLBOX := true
TW_INCLUDE_REPACKTOOLS := true
TW_EXTRA_LANGUAGES := true
TW_INCLUDE_LOGCAT := true
TW_USE_FSCRYPT_POLICY := 1
# FBE decryption for Android 17 is NOT VERIFIED. Turn on only after HAL and
# provider shims pass testing. Build deliberately defaults to no crypto UI.
TW_INCLUDE_CRYPTO := false
TW_INCLUDE_CRYPTO_FBE := false
RECOVERY_SDCARD_ON_DATA := false