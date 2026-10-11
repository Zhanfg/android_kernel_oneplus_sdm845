# OnePlus 6 / Linux 4.19 — 功耗与显示专项审查 (2026-10-11)

实验父提交：95858e26d1303427d5156aab1bd04ad4effd5111
分支：audit/enchilada-power-display-20261011
此分支仅增加只读探针与审查文档，不改动正在编译的 PR #12 内核配置、驱动或 DTB。

## 源码核对结果

| 文件 | 发现 | 后续动作 |
| --- | --- | --- |
| arch/arm64/boot/dts/qcom/sdm845-gpu.dtsi | GPU idle-timeout=80ms；GPU/GMU 频率及带宽等级 | 比较不同 idle 延迟的 GMU 休眠驻留、唤醒次数、帧延迟及整机耗电 |
| drivers/gpu/msm/adreno_a6xx_gmu.c | 实现 GPU GMU/RPMh 休眠与 power collapse | 必须核实低功耗状态是否被调用，不以锁最低频率替代休眠 |
| drivers/cpufreq/cpu-boost.c | input_boost_ms 初始值 40ms；sched_boost_on_input 可选 | 核查运行时是否发生与 Power HAL/WALT 重复的触摸 boost |
| arch/arm64/boot/dts/qcom/sdm845-pm.dtsi | CPU/cluster idle 电源状态与 entry latency | 按深度驻留率/唤醒增量定点优化 |
| arch/arm64/boot/dts/qcom/sdm845-sde-display.dtsi | 原本已有 panel_active/panel_suspend pinctrl | 不直接套用主线 OnePlus DSI 休眠补丁 |
| techpack/display/msm/dsi/dsi_panel.c | panel power-off 选择 suspend pinctrl；DCS 背光 | 检查熄屏后确实到达正确时钟/引脚/电源路径 |
| techpack/display/msm/dsi/dsi_display.c | ULPS、PHY idle、clamp、display idle-power-collapse 路径 | 查明 ULPS 标志与实际转换，不盲开新功能 |
| dsi-panel-samsung_s6e3fc1_cmd.dtsi、dsi-panel-samsung_sofef00_m_cmd.dtsi、dsi-panel-samsung_sefeg01_s_cmd.dtsi、dsi-panel-samsung_s6e3fc2x01.dtsi | 四个已检查的 panel 节点均为 60Hz 且带 qcom,ulps-enabled；ESD 设置并不一致 | 禁止统一启用 ESD 或把屏幕超频至 90/120Hz |
| arch/arm64/configs/vendor/sdm845-perf_defconfig | KFENCE、SCHEDSTATS、PROFILING、DEBUG_INFO 等诊断选项存在 | 评估日用构建和调试构建分离，不降低 CFI/SELinux/热保护 |

## 优先顺序

P0：熄屏 deep suspend / wakeup source -> GPU GMU idle/power-collapse -> DSI ULPS / suspend pinctrl / DSI 时钟投票。
P1：CPU Boost 与 WALT/Power HAL 重复升频 -> DDR/LLCC/DEVFREQ 高频带宽投票 -> 帧时延与掉帧。
P2：日用构建减少不必要的追踪和采样成本 -> UFS idle/link 低功耗能力。

注意：调小 GPU idle 超时若造成频繁进入退出反而可能增加耗电；高频 CPU/DDR 锁定不是性能调优。热管理、充电、指纹唤醒、基带、ESD 保护应保持完整。

## 显示优化的界限

现有 OnePlus 6 相关面板树为 60 Hz；在没有该具体面板的电气时序与稳定性验证前，不添加 90 Hz、120 Hz 等新时钟配置。不要通过关掉 ESD 检测换取轻微 CPU 性能。真正有价值的是空闲显示管线（DSI PHY、panel、GMU、SDE/LLCC 投票）可靠地进入低功耗状态。来自新 Linux 主线的 pinctrl 改动需要先与这个 Qualcomm 4.19 厂商树逐项比较。

## 验收矩阵

分别在飞行模式待机、Wi-Fi 待机、蜂窝待机、普通网页滑动、视频播放、游戏与 50 次熄屏唤醒测试。比较温度与亮度一致情况下的电流/能量、CPU idle residency、GMU/DSI 活动、唤醒次数、帧时间 p95/p99、ANR/黑屏和充电/通话/指纹可靠性。既要考核 performance，也要考核 wakeup 与 battery cost。

电池若不是系统标称容量，电量百分比/小时不代表真实能量，必须核实 charge_counter/current_now 单位或用外置仪表测量。

## 新工具

tools/op6-power-display-probe.sh：设备本地执行 sh op6-power-display-probe.sh，无需参数。报告保存 /sdcard/Download/OP6_Power_Display_时间.txt（必要时 /data/local/tmp）。读取 wakeup/CPU/GPU/DRM/电池状态，但不会写内核参数或启用跟踪；两次报告的计数差值更有意义。日志中可能出现唤醒源名称，请自行检查脱敏后再分享。

## 参考

- 官方设备参数 https://www.oneplus.com/us/support/spec/oneplus-6
- Google Android Power Measurement https://source.android.com/docs/core/power/component
- Google Power Stats HAL https://source.android.com/docs/core/power/power-stats-hal
- Upstream panel sleep pinctrl 讨论 https://lists.openwall.net/linux-kernel/2026/03/11/1913
