# OnePlus 6 (enchilada): HDR and refresh capabilities

## Source facts verified on `lineage-23.2-4.19`

The **OnePlus 6** panel baseline is not the same as the OnePlus 6T (fajita).

- `arch/arm64/boot/dts/qcom/enchilada.dtsi` selects
  `dsi_samsung_sofef00_m_cmd` by default.
- `arch/arm64/boot/dts/qcom/dsi-panel-samsung_sofef00_m_cmd.dtsi`
  defines **1080 × 2280 @ 60 Hz** and `qcom,mdss-dsi-bpp = <24>`.
- This 2280 panel source **does** carry `qcom,mdss-dsi-panel-hdr-enabled`,
  chromaticity primaries and peak/average/black luminance metadata.
  It also carries DSI command sequences for sRGB and P3 display modes.
- The same source advertises **only one 60Hz mode**. No validated
  30/48/90/120Hz physical DSI timing mode is provided by this panel file.
- `dsi-panel-samsung_s6e3fc2x01.dtsi` has height **2340**, so it is
  **not a drop-in replacement** for the 2280 panel.

## What this does and does NOT prove

- **HDR metadata in DTS != verified end-to-end Android HDR playback.**
  This panel's 24-bit DSI link does not establish a true native 10-bit
  output path. Check the active display HAL, SurfaceFlinger/HWC2,
  media codecs, HDR dataspace support and tone mapping before enabling
  any HDR feature in the ROM.
- sRGB/P3 panel commands make accurate color-profile handling worth
  reviewing. They do not guarantee HDR10 or HDR10+ certification.
- **Only one 60Hz physical mode** is defined here. Frame pacing
  (24/30/60 frames/s) on a fixed 60Hz display does not equal
  variable *physical* refresh. Android 15+ ARR requires hardware/HWC support.
- Do not overclock the panel by editing framerate/DSI PLL timings or
  transplanting the 6T panel definitions. Such patches require panel,
  DSI PHY and power/thermal measurements on disposable test hardware.

## Verification workflow

1. Run `sh tools/display/enchilada_display_probe.sh` on OnePlus 6
   (no arguments; read-only) and inspect the generated TXT file.
2. Verify the actual `display` and `SurfaceFlinger` service modes,
   HDR formats and color management. A failing binder query
   means *unknown*, not *unsupported*.
3. Check stock `vendor` HWC/color services and VINTF support for the
   matching Android 17 ROM build; kernel DTS is only one layer.
4. When real same-resolution secondary display modes are reported,
   use Android's built-in SurfaceFlinger frame-rate selector. Do not
   fake new modes in Settings.
5. Compare SDR and known-good HDR test patterns with brightness/
   white-point measurements and verify no black crush, clipping or
   severe thermal/battery regression. Keep original modes as fallback.

This work is a conservative, source-anchored audit. It deliberately
does not change boot-critical DTS timings or claim HDR playback is ready.
