# KV260 HDMI 屏幕接入检查

检查日期：2026-10-04，时间使用主机 UTC；板卡时间不作为验收时间。用户说明已接入 HDMI 屏幕，本轮通过 UART 查询目标板并调整本次桌面显示状态。

## 结果

板端已识别屏幕，并已启用其 EDID 推荐的 **1024×600、59.85186 Hz** 模式。`xrandr`、DRM sysfs、内核 DRM scanout 状态及指定实际显示设备的 `modetest` 查询相互一致。当前 `connected`、`enabled`、`DPMS On`、`link-status Good`，Xorg 分配的 RGB565 framebuffer 为 1024×600，CRTC `enable=1`、`active=1`。

**用户随后提供的实屏照片已确认桌面有画面：屏幕显示 Linux 桌面的 `Applications` 应用页面，能看到 File Manager、Terminal、Shutdown、GVim 等图标和文字。基础 HDMI 静态桌面显示通过。** 单张照片不能验收闪烁、精确裁剪、触摸/鼠标操作或 UI/动画并发；本轮没有测量物理视频信号。

照片见 [用户提供的实屏照片](/home/ghmd/图片/03041AF473ABB3214A5E7BF6D8C24CA4.jpg)，哈希、可见内容和验证范围见 [照片确认记录](PHOTO_CONFIRMATION.json)。原 `EVIDENCE_REVIEW.json` 保留 UART 检查时尚待实屏反馈的状态，照片确认是后续追加证据，没有改写原始检查结果。

## 实际发现和处理

1. 初次读取时屏幕连接为 `connected`，输出 `disabled`、`Off`。EDID 缓存为空，modes 是 1024×768 等回退模式。
2. 查询 Xorg 的 `xrandr --verbose` 后成功取得 128 字节 EDID，校验和为 0；首个详细时序为 1024×600、49 MHz 像素时钟，刷新率约 59.85 Hz。初次空 EDID 不能继续认定为屏幕或线缆故障。
3. Xorg 仍使用开机时的 1024×768 回退模式；`xset q` 显示 600 秒 DPMS 节能且 `Monitor is Off`。自动息屏解释了此次关闭的输出状态；是否同时存在其他实屏问题仍须观察。
4. 在核对 SD CID、新 boot ID 和原状态后执行：

   ```bash
   xset -display :0 dpms force on
   xrandr --display :0 --output DP-1 --mode 1024x600 --rate 59.85
   ```

   两条命令均返回 0，随后的 Xorg 与内核检查确认新模式启用。命令预设失败时恢复原模式和 Off 状态，本次未触发回退。
5. 最初 `modetest -M xlnx -c -p` 返回 255，提示无法按该 driver 名打开设备。原始失败保留。改用 Xorg 已记录的实际 bus ID：`modetest -D fd4a0000.display -c -p` 返回 0，确认 connector 43、CRTC 41、framebuffer 47 与原生模式。这不是据以认定显示驱动缺失的证据。

## 为什么 HDMI 在 Linux 中叫 DP-1

KV260 的载板带 DP/HDMI 分配器，包含 DP 的参考平台支持 DisplayPort 和 HDMI。当前系统从 ZynqMP DisplayPort 显示设备输出，因此 HDMI 实物接入可以在 Linux 中表现为 `DP-1`。见 [AMD Kria 平台说明](https://xilinx-wiki.atlassian.net/wiki/pages/viewpage.action?pageId=2721415196)、[UG1089 物理接口](https://docs.amd.com/r/en-US/ug1089-kv260-starter-kit/Interfaces)。实际系统中 `card0` 是 `zynqmp-display` 显示设备，`card1` 是 ZOCL；不可用 card1 代替显示设备。

## 本次目标板和证据

- SD CID：`0353445345333247805558c00401a100`。
- 内核：`5.15.36-xilinx-v2022.2`。
- 本次 boot ID：`b39598d6-1118-4ef3-af52-36f0c1a4d396`，与此前 NFS 冷启动验收不同。本轮未观察这次关机/上电过程，不追加物理冷启动通过次数。
- manager PID 1018、Xorg PID 1076、xserver-nodm service PID 994。显示调整前后 manager 与显示服务保持 active，相应服务 PID 不变。
- 调整前官方 `kv260-benchmark-b4096` 在 slot 0；本轮未加载或卸载任何 PL 硬件包，未重跑 DPU 推理。
- EDID SHA-256：`727d3e1893df759c757c35232f9465b670a64d6de2011b586de48c6446e17c35`。

原始 UART 证据保存在既有 UART 工作区的三个新目录，旧封存交付包未重打包：

- `/home/ghmd/kv260-dfx-state-boardtest-20261004/evidence/20261004T122419.533161Z-39-display-readonly-inventory`
- `/home/ghmd/kv260-dfx-state-boardtest-20261004/evidence/20261004T122614.821640Z-40-display-xorg-readonly`
- `/home/ghmd/kv260-dfx-state-boardtest-20261004/evidence/20261004T122750.224677Z-41-display-wake-native-mode`

[独立证据复核](EVIDENCE_REVIEW.json)：**64 项检查通过，23 个证据/清单/脚本文件记录 SHA-256 与长度**。其中失败的 driver-name 查询按其真实非零结果复核，不能把脚本整体返回 0 当作内部每个探针均成功。三次 UART 会话均完整，输出帧哈希一致，控制台 echo 恢复。

## 限制与下一步

- 只调整当前 X 会话；没有修改启动配置。600 秒自动息屏设置仍保留，空闲后可能再次关闭屏幕。后续 UI 的常亮/节能策略需要在实际显示服务中配置并验收。
- 开机的 `dpdma_ref_div1`、`dpll_int` 两条 `ret = -13` 时钟权限告警仍存在。此次调整前后日志没有新增链路训练失败、时钟失败或内核致命异常，不能据此宣称其根因已经修复。
- Xorg 日志有 GLX 模块缺失，并使用 Soft EXA；3D 加速和最终 Qt/SDL/中文字体能力未验证。当前桌面服务存在不等于全部 UI 依赖齐全。
- 实屏照片已确认静态桌面显示。下一阶段可做中文静态界面、动画/字幕及与相机/DPU/音频并发的显示验收；当前 Applications 页面是系统自带桌面，尚未表示项目 UI 已部署。
