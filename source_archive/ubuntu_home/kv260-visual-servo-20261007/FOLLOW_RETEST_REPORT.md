# 视觉随动复测：2026-10-08（本地日期）

结论：真实左右视觉命令链路已覆盖，失跟停止和目标重现不自动恢复已有本次板测证据；30 秒持续随动及机械方向现场验收仍未完成。结束时 PWM 禁能，镜像预览继续运行。

## 本轮实际结果

| 测试 | 实测 | 结束原因 |
|---|---|---|
| 左右联动 | 22.226 秒，275/275 条命令接受；CENTER 56、CLOCKWISE 88、COUNTERCLOCKWISE 131；目标与有效宽度读回范围 1480..1518 µs | FACE_QUALITY，STOP 通过 |
| 失跟测试 | 2.105 秒，3/3 条命令接受 | LOST_OR_AMBIGUOUS，STOP 通过 |
| 重现后只读观察 | 10 秒、47 次采样均可见目标，全部 flags=0、lease=0、active/armed=false，ACK 保持 3 | 观察完成，没有命令写入 |
| 最后持续补测 | 0.877 秒，10/10 条命令接受 | FACE_QUALITY，STOP 通过；30 秒验收未通过 |

第一轮 ACK 时源年龄中位 55.685 ms、最大 82.629 ms；提交中位 2.894 ms、最大 13.935 ms。三轮均未发生此前 STALE_SOURCE 或 HARDWARE_LEASE_ENDED。该结论只适用于记录的测试窗口。

最终独立核对 flags=0、lease=0、ACK=10、active/armed/bound/referenced=false。width_us=1502 是停止后保留的寄存器值，不表示仍有 PWM 输出，也不是机械角度。唯一摄像头拥有者 PID 16981；采集、检测、显示持续增长，error=null，Monitor On。最后窗口累计检测约 12.43 Hz，为 CPU YuNet，不能称为 DPU 视觉验收。

## 重启恢复与验证

最初沙箱没有串口设备；获准使用既有 UART 入口后连接成功。随后旧 boot 检查拒绝执行，没有发出运动指令。只读盘点确认本次 boot 为 c2753755-e758-4ab6-a4b6-2929271aa723，官方 B4096 活动、摄像头无人占用、屏幕休眠。

本次基础 FDT 的二进制 SHA 与旧启动不同，主机逐项比较全部属性未见差异，既有候选 overlay 在本次 FDT 上合并通过。先核对 common/load 源 SHA、设备身份、基础 FDT、固件与运行时 SHA、无 DPU 客户，再明确将此次受控脚本绑定到已盘点的新 boot；旧发布源码和 common.py 未修改。联合配置加载后初态与 STOP 均禁能。

恢复原 mirror-0c1d48dd418e922d 发布：逐文件 SHA 校验及预检通过，保留镜像、192×192 检测、2 CPU 线程和蓝线 x=320。Xorg 重探测后提供 1024×600，恢复本次显示会话并唤醒。没有持久化运动自启或显示设置。

5 秒只读预检取得 865 个年龄样本，中位 85.143 ms、最大 133.974 ms，超过 250 ms 为 0；64 个新帧满足既有方向测试条件。第一、第二轮完整命令事件已回读并校验 SHA；主机逐条复核 ACK、目标、会话、代次、源帧递增、源年龄、范围与单步限值，以及目标横坐标对应的方向，全部通过。新增恢复、绑定、预检、观察和导出脚本语法编译通过。

## 原始证据

- 新启动盘点：adaptation-check/evidence/20261009T030828.488815Z-restart_inventory
- FDT 与主机合并：adaptation-check/evidence/20261009T031035.220551Z-source_platform_dt_export/compatibility.json
- 联合配置恢复：adaptation-check/evidence/20261009T031213.545235Z-newboot_vsrv_load
- 预览恢复：adaptation-check/evidence/20261009T031332.638672Z-newboot_preview_start
- 只读预检：adaptation-check/evidence/20261009T031400.786459Z-newboot_visual_preflight
- 左右测试：adaptation-check/evidence/20261009T031438.404568Z-newboot_visual_direction_start
- 失跟测试：adaptation-check/evidence/20261009T031627.087994Z-newboot_visual_direction_start
- 重现观察：adaptation-check/evidence/20261009T031722.608555Z-newboot_stop_monitor
- 回读与逐条核验：adaptation-check/evidence/20261009T031744.253555Z-newboot_direction_evidence/HOST_TRACE_VERIFICATION.json
- 持续补测：adaptation-check/evidence/20261009T031804.999593Z-newboot_visual_direction_start
- 最终停止与预览：adaptation-check/evidence/20261009T031903.092907Z-newboot_vsrv_final

上述 adaptation-check 指 /home/ghmd/kv260-adaptation-check-20261006。各执行目录包含 remote.py、result.txt、status.json 与 UART 原始记录，输出完整性 SHA 和回显恢复检查通过。屏幕截图已人工检查：20261009T031538.075014Z-realtime_verify/screen.jpg。

## 尚需完成

保持整张脸稳定入镜、避免贴边后补足 30 秒持续测试。当前 FACE_QUALITY 涵盖裁剪、框尺寸、面积及分数；本次没有逐项记录触发值，不能断言每次都是同一具体条件。截图中人脸占画面较大，建议先调整距离/机位，不放宽质量保护。

机械顺逆时针仍等待本轮现场反馈。已有脉宽增加逆时针的历史用户报告保持追溯；命令方向及宽度回读不代替轴角实测。1500 µs 仅受控测试点，机械参考与三点指向标定仍无效。速度、增益、250 ms 源时效、每次 4 µs/每秒 40 µs 限值保持；速度调配按用户决定留到 3D 打印机构完成后。

新增脚本均位于 adaptation-check/scripts/newboot_*，只适用于明确记录的新 boot；换启动会拒绝执行。未修改运动 RTL、模型权重、控制算法或原不可变发布。
