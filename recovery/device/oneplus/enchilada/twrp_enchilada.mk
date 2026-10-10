$(call inherit-product, $(SRC_TARGET_DIR)/product/core_64_bit.mk)
$(call inherit-product, $(SRC_TARGET_DIR)/product/base.mk)
$(call inherit-product, device/oneplus/enchilada/device.mk)
$(call inherit-product, vendor/twrp/config/common.mk)
PRODUCT_NAME := twrp_enchilada
PRODUCT_DEVICE := enchilada
PRODUCT_BRAND := OnePlus
PRODUCT_MANUFACTURER := OnePlus
PRODUCT_MODEL := OnePlus 6