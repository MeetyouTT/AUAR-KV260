# 微雪触屏接线后的真实输入与驱动持久化

本地日期：2026-10-09（America/Los_Angeles）；主机 UTC 证据日期为 2026-10-10。接续用户“好了”，核查 TOUCH USB 接线并完成本轮修复。较早的 [驱动排查](2026-10-09-WAVESHARE-TOUCH-DRIVER.md) 保留为历史记录。

## 结果与依据

- USB `1-1.4` 已枚举 `WaveShare WS170120`，VID:PID `0eef:0005`；U 盘已不在该端口。
- 板卡已发生外部重启：本轮 boot ID 为 `0ecc7063-1b99-4bca-9e9c-d9f8026732f5`，与上一轮不同。本轮没有执行重启命令。之前仅当前启动加载的触屏模块已消失，旧 GUI PID/日志不能代表本次运行。
- 重新正常加载此前核验的 `hid-multitouch.ko` 后，控制器自动绑定 `hid-multitouch`，无需手动解绑。真实输入为 `/dev/input/event5`，带 `INPUT_PROP_DIRECT`；XInput 显示 direct、最多五触点。这是能力枚举，未做五指压力测试。
- 读取并核对实际 EDID SHA 后，将本次 X 会话从 1024×768 恢复至 **1024×600、59.85 Hz**，将该触屏映射到 `DP-1`。
- 恢复现有 GTK3 界面，PID **2175**，保存的音量 **64%** 随启动恢复。之后收到真实手指操作；25 秒只读 evdev 观察记录 **3348** 个事件，包括触点按下/抬起与 X/Y 移动。未使用 XTest、未合成事件、未独占输入设备。
- GTK 实际收到音量滑块的 touch-begin/end，以及“互动／设置”页签的 touch-begin/end 和对应 activation。观察前后音量分别为 11% 与 18%；最后界面、ALSA PCM 回读和实际配置文件均为 **18%、非静音、全屏、普通动画**，无设置错误或未应用请求。没有把音量强制改回 100%。
- 截图回读并查看，尺寸为 1024×600，设置页显示“音响已连接 · 触摸已连接”，音量 18%。

## 板端改动与备份

1. 已加载模块 SHA256：`fce568b070bbc0e9210bc6417b39e1c57637d9d24d9fdebc4cb913603505417b`，34944 字节；vermagic 为 `5.15.36-xilinx-v2022.2 SMP mod_unload aarch64`。
2. 将同一模块安装至 `/lib/modules/5.15.36-xilinx-v2022.2/extra/aura/hid-multitouch.ko`，运行 `depmod`，`modinfo` 与 `modprobe --show-depends` 正确解析至该路径。
3. 新建 `/etc/modules-load.d/aura-touch.conf`，内容为 `hid-multitouch`。实际 `systemd-modules-load.service` 已安装、当前状态 active/exited、Result=success；**新配置的下次开机加载尚未重启验收**。
4. 原模块索引备份至 `/home/root/aura-waveshare-touch-20261009/module-index-backup-1637343387439831887/`。
5. 旧启动记录与 GUI 日志移入 `runtime-1a8677ce-20261009/recovery-backup-0ecc7063-1b99-4bca-9e9c-d9f8026732f5/`。本次 GUI 使用独立 `run-evidence-0ecc7063-1b99-4bca-9e9c-d9f8026732f5/`，原报告与素材保留，GUI 源码没有修改。

本轮未停止/启动 A 的视觉、重载 PL 或操作舵机。实际进程扫描显示 DFX manager PID 1073 在运行，**当前未发现 `realtime_vision.py`**；此前“视觉 PID 16981 继续运行”仅属于重启前记录，不能用作本轮并行性能结论。

## 验证与证据

工作目录：[aura-waveshare-touch-20261009](/home/ghmd/aura-waveshare-touch-20261009)。

| 检查 | 证据目录（相对于工作目录的 `evidence/`） |
| --- | --- |
| 新启动后的 USB/内核诊断 | `20261010T003358.049945Z-inspect/` |
| 模块重新加载、自动绑定 | `20261010T004102.352941Z-module-load/` |
| EDID/显示恢复 | `20261010T004657.517295Z-display/` |
| GUI 启动与就绪 | `20261010T004708.706549Z-start/`、`20261010T004739.045326Z-status/` |
| 真实手指 evdev | `20261010T004814.984757Z-observe/` |
| GTK 触摸与页面激活 | `20261010T004851.140454Z-report/` |
| 模块安装与加载配置 | `20261010T004925.087528Z-persist-driver/` |
| 配置、音量、绑定和实际进程复查 | `20261010T005007.394749Z-verify-final/` |
| 实际窗口截图 | `20261010T005024.206584Z-window/board-window.jpg` |

执行 `python3 -B /home/ghmd/aura-waveshare-touch-20261009/verify_touch_connection.py`：八份关键响应的大小/SHA256/JSON 回读、真实输入、GTK 事件、ALSA 与保存值、模块 SHA/解析/自启配置检查全部通过，详见 [独立核验](/home/ghmd/aura-waveshare-touch-20261009/touch_connection_validation.json)。`touch_runtime.py --validate` 检查各阶段源码可编译，含外层封装的 UART 命令长度均在限制内。既有 70 项主机、12 项板端设置测试是前次软件验证；本轮没有修改 UI 源码或重复执行这些测试。

## 问题处理及尚未验证

- 初始 API connection refused 的原因是板卡已重启、GUI 未运行。另一次恢复后的短暂 connection refused 出现在资源加载期间；后续 READY、FOREGROUND 和 API 正常，无需再次启动进程。
- 模块加载工具一次因外层 UART 长度限制在发送任务命令前停止；压缩必要探测并补充外层长度检查后成功。失败原件保留，不能计为驱动加载失败。
- UI 原报告中的 `preferences.volume` 缓存的是启动值 64%，不是最新声音值；本轮以 `ui_settings`、ALSA 和实际 `avatar_user_settings.json` 三方一致的 18% 为准。
- 手指拖动和页签切换已实测；当前记录没有音量加减按钮的手指 activation。全屏边缘精度、五指并发、长期运行与主观触摸反馈仍未完整验收。
- 已配置触屏模块自启；未配置 GUI 自动启动或持久化 X 会话分辨率，也没有发起重启验收。UI 动画仍偏慢，本轮报告 p95 间隔约 502ms，不作为流畅度通过。当前没有真实视觉进程，不能给出本次视觉/UI 并行验收结论。
