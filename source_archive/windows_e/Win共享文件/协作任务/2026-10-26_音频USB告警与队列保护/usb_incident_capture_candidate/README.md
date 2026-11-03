# MCP01 USB复发事件只读采样候选

本目录由独立音频终端实现，未访问板卡、UART或任何HTTP端点，未改现役。它用于在告警复发时留住同时段数值证据，不是USB修复或自动恢复程序。

运行方式：

```sh
python3 -B usb_incident_capture.py --output <全新证据目录> --duration 20 --camera-pid <当前相机PID> --gui-pid <当前GUI主PID>
```

先由主端验证固定路径与3秒事件快照可读，再运行20秒无动作观察；较长观察可用`--duration 7200`。参数最长7200秒；固定每10秒检查，最多3个事件，每两个事件开始时间至少60秒。外部读取使用有限超时，退出时仍可能需要完成当前有界读取/自有元数据子进程清理。程序没有修改服务、加载模型、USB reset、音频播放、相机/转轴控制或MMIO入口。

## 告警真实性与去重

只读取本boot `journalctl -k -b … -n 120 -o json`，仅保留内核transport、完全匹配`xhci-hcd.1.auto`、slot4/ep3的现有告警文本。boot UUID统一为32位小写无横线；使用journal `__MONOTONIC_TIMESTAMP`微秒，严格丢弃启动前/相同时间戳重复/未来时间条目，不使用板卡2021年墙钟当当前UTC。每个窗口只有末120条，满120明确标`sample_capped`，不能将采样计数称完整告警率。冷却期内新事件仍被消费去重，不能稍后拿旧事件再次触发。

## 事件证据与停止条件

每轮核对实际camera health PID、systemd GUI MainPID、两进程birth ticks、板boot、ALSA card1 USB ID `17ef:a03b`、sysfs1-1.2身份和debugfs slot04名称。核对PCM处于RUNNING且audio owner仍相同；任何读数失败、owner/boot/设备变化都结束，保留错误回执。HTTP只抽取运行数值/有限状态，不保存对话、人名、人脸框或图像。

事件采样固定读取：MCP01 PCM status/hw_params/sw_params，约3秒、每250ms记录hw_ptr/appl_ptr/delay/avail；相关USB/xhci/dwc IRQ计数、CPU/proc/stat/loadavg；设备speed/power/runtime_status/control及slot/endpoint context。PCM指针原始差不等于USB包全部成功，也不等于声学效果。不会读取音频payload、设备流或进程私有argv。剩余总时限不足3秒时不开始完整事件，结果明确为未完成，不伪造成功incident。

输出目录必须全新，文件用exclusive-create及NOFOLLOW。`run.json`记录启动参数，`progress.jsonl`追加有界进度，`incident-001..003.json`保存事件，`result.json`记录最终原因。单事件≤128KiB，进度≤512KiB，总输出≤1MiB且为最终结果预留8KiB；不覆盖旧证据。正常7200秒/720poll的实际生成JSON已由假时钟测试确认在上限以内。

## 本地验证

`python3 -B -m unittest discover -s . -p 'test_*.py' -v`共15项通过：精确boot/来源/文本、微秒/旧事件/未来/重复过滤、120行截断标记与坏JSON拒绝、三事件/冷却期、20秒和7200秒有限运行、owner变化/事件中变化/读错退出、目录/符号链接/文件独占、每文件与总字节上限、PCM解析、实际Platform抽取不泄漏HTTP私有字段、控制命令白名单拒绝和不足三秒不伪造事件。

这些测试使用fake clock/journal/proc/HTTP，未读取实板状态，未注入真实告警。主端需另验证实际平台固定字段和路径，再决定启动有限只读观察。
