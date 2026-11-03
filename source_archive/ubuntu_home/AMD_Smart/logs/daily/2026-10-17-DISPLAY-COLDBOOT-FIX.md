# 2026-10-17 断电后花屏检查与启动补丁

用户报告断电第二天开机屏幕花屏，需要重新插拔 HDMI。按 ZIP README、启动文档、旧 EDID 故障记录和实际串口证据排查；用户尚未确认当前是否仍花屏，本轮未复现该物理现象。

## 实测与结论

UTC 2026-10-18 04:22 起读板：boot `4e34d2fb-8f97-4cda-a598-c01d510e5c99`，本轮没有发起启动。当前 boot 的 setup 明确为 EDID 缺失回退；sysfs EDID 为0字节，Xrandr保留正确屏幕信息/1024×600时序，GUI和相机active。优先排查显示冷启动识别/初始化，尚不能确诊供电/HDMI/驱动根因，软件状态不代表面板正常。

已安装新启动器 `d2e45eb7fee4fa08` 并更新下次启动入口：EDID宽限15秒、稳定3秒、每boot一次指定输出关闭1秒后恢复；保留已实测时序及触摸/屏幕身份校验，关闭前记尝试，失败/取消也尝试恢复，避免服务重试反复闪屏。物理面板验收标记保持false。

本次不重启当前界面/相机/整板、不实际切换输出；GUI PID1349、监督器PID1047、相机PID986和代次保持，音量58%非静音。当前仍运行旧 `190bbd429af06931`，新逻辑下次服务启动/开机执行，**真实冷启动和花屏是否消失待验收**。

## 验证与改动

- 主机/板端启动逻辑各17项通过，显示命令为fixture；不是物理HDMI验收。
- 新启动器实际组件预检通过，保留实板54项组件哈希；5部署文件SHA回读匹配，保护文件、运行PID与相机代次保持。
- 已保存旧unit/launcher/config；ZIP 13085字节，SHA `83f284ba2d5b3af0270f9f2f7f5911c70250f2b9aeb95246d389a9226e366f8a`。
- 最终独立核验36份UART响应、4附件、包载荷、5部署文件与54项保留组件；真实板端17项原始输出已回传，当前监督器仍运行旧版本，恢复标记未生成。[核验JSON](/home/ghmd/Win共享文件/共享文件夹/aura/report/display_coldboot_20261017/validation.json)状态为 `PASS_INSTALLED_NEXT_START_ONLY_COLD_BOOT_NOT_VERIFIED`。
- 修改主仓 scripts/board_ui_startup 的launcher/config/service/release_manifest、增加test_display_startup.py并更新说明；同步实际当前GUI/ASR/相机哈希，未修改业务功能或模型。
- 参考Linux内核EDID说明和Xorg官方Xrandr手册，机制与本机证据分开记录。没有修改内核参数、驱动、Xserver、相机、FPGA或运动配置。

详见 [共享报告](/home/ghmd/Win共享文件/共享文件夹/aura/report/display_coldboot_20261017/REPORT.md)。本轮下一项实物验证是完全断电后保持HDMI连接启动；若仍花屏需保留现场取证，不能将预防性补丁写为根因已彻底修复。
