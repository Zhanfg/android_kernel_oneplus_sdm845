# Recovery-only OnePlus 6 product. Do not inherit legacy ROM vendor stacks.
LOCAL_PATH := device/oneplus/enchilada
PRODUCT_DEVICE := enchilada
PRODUCT_BRAND := OnePlus
PRODUCT_MANUFACTURER := OnePlus
PRODUCT_MODEL := OnePlus 6
PRODUCT_SHIPPING_API_LEVEL := 27
TARGET_SCREEN_WIDTH := 1080
TARGET_SCREEN_HEIGHT := 2280

# Filesystems required by retrofit dynamic partitions are present in the
# Android 14-based recovery toolchain; actual mounts remain gated by fstab.
PRODUCT_PACKAGES += \
    fastbootd

PRODUCT_COPY_FILES += \
    $(LOCAL_PATH)/recovery/root/init.recovery.enchilada.rc:$(TARGET_COPY_OUT_RECOVERY)/root/init.recovery.enchilada.rc