# 2026-10-04：HDMI 屏幕接入检查

用户说明已连接 HDMI 屏幕并要求检查。按规则读取 ZIP README、A/C 的实屏与显示通路要求、最新平台告警和 FPGA 环境记录，再通过同一目标板 UART 采集 39/40/41 三轮证据。

## 实际结果与调整

- 当前 boot ID 为 `b39598d6-1118-4ef3-af52-36f0c1a4d396`；SD CID 与 2022.2 内核身份匹配。未观察此次关机/上电，不追加冷启动验收结论。
- 初次 DRM：连接存在，但输出 disabled、DPMS Off、EDID 缓存为空。Xorg 查询后取得有效 128 字节 EDID，推荐 1024×600、约 59.85 Hz。
- Xorg 仍为 1024×768 回退模式，且 600 秒自动息屏已触发。执行本次会话的 `xset ... dpms force on` 和 `xrandr ... --mode 1024x600 --rate 59.85`，均返回 0。
- 调整后 Xorg、DRM sysfs/scanout、实际 bus ID 的 modetest 相互印证：connected、enabled、On、Good，1024×600 framebuffer，CRTC active/enabled。
- manager PID 1018、显示服务 PID 994 在调整前后保持 active。不修改启动文件，不切换 PL，不重跑 DPU 推理。
- `modetest -M xlnx` 无法按 driver 名打开的失败证据保留；以 `-D fd4a0000.display` 指定实际 bus ID 查询成功。不能将该探针失败误报为驱动未安装。
- 主机独立复核 64 项检查通过，23 个文件登记哈希/长度，三轮 UART 输出完整且 echo 恢复。

## 尚未验收

裁剪/闪烁、触摸/鼠标操作仍未验证。600 秒节能保留，仅本会话调整；开机两条时钟 -13 和既有 overlay 告警未修复。GLX 缺失/Soft EXA 已记录，中文、最终 UI/3D 及相机/DPU/音频并发未验证。

## 后续实屏照片确认

用户提供 `/home/ghmd/图片/03041AF473ABB3214A5E7BF6D8C24CA4.jpg` 并说明屏幕显示这个页面。实际查看照片：这是 Linux 桌面的 `Applications` 页面，可见 File Manager、Terminal、Shutdown、GVim/Vim 图标和文字；基础 HDMI 静态桌面显示通过。用户所说“没看到桌面”是对桌面样式的疑问，照片中已经有桌面内容。

照片 1612715 字节，SHA-256 `6c57e7c8d54c5922bb98187f6bd917911692f277778f6d39fefbd90f0f9d3357`，见 [照片确认记录](/home/ghmd/kv260-hdmi-display-check-20261004/PHOTO_CONFIRMATION.json)。本次补录只检查照片并更新记录，没有再操作板卡或运行测试；照片不代替动态显示/输入/常亮或项目 UI 验收。

详见 [显示检查报告](/home/ghmd/kv260-hdmi-display-check-20261004/DISPLAY_CHECK_REPORT.md) 与 [原始证据复核](/home/ghmd/kv260-hdmi-display-check-20261004/EVIDENCE_REVIEW.json)。
