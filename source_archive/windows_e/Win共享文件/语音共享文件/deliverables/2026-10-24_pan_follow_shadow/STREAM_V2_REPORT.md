# 实况推送通道与10秒Shadow结果

**后续更新：** 本boot已恢复VSRV/2联合固件、完成新的人眼20µs往返确认和GUI READY；见[当前状态](CURRENT_BOOT_RESTORED.md)。本页的官方固件/FAULT描述属于恢复之前的时点，SFace LATCHED和实体随动未验收的限制仍保留。

UTC 2026-10-25 03:09。当前boot `463c9307-5e47-49b0-b22f-5fd3fc21451c`，相机PID17671、GUI PID1307。**只读视觉shadow完整10秒通过；实体转轴随动尚未启用。** 当前PL为官方`kv260-benchmark-b4096`，不含本次VSRV/2转轴控制；手动backend正确拒绝未知board/boot/firmware/VART上下文。

## 本轮实际改动

新增独立的`/v1/motion/stream`接口。相机发布源观测后只通知内存Condition；HTTP线程在相机锁外发送同一源帧协议，最长10秒、最多一个stream客户端、写超时250ms，空闲时50ms心跳保持原时间戳。相机业务源码、原native入口、模型、阈值和恢复预算均未改。没有第二相机或第二DPU owner。

消费者使用独立`ShadowDriver`。建议脉宽限制1425～1445µs，源帧期限仍250ms；重复帧不积分，过期/失跟/换目标仍锁停，不自动重新解锁。没有VSRV硬件依赖和寄存器写入。

当前启动覆盖为`zzzzzzzzzzzzz-aura-pan-stream-v2.conf`，SHA `98cdd6113321247353f874f91804555f439bea790cb2d0ff37b09fce9def6d56`。旧覆盖保留，可作为受控回退链；不直接删除其他任务文件。源见[source/stream_v2](source/stream_v2)，部署脚本见[source/deployment](source/deployment)。

## 验证结果

新增7项检查通过：实际r4 CameraState/旧路由兼容、源时间不刷新、通知交付、冻帧过期、单客户端/时长限制、慢消费者不阻塞发布，以及真实HTTP fixture上的完整窗口和过期停锁。

| 实板窗口 | 结果 |
| --- | --- |
| 原GET轮询shadow | 13新源帧、8条软件建议，1.304秒后SOURCE_EXPIRED，窗口未完成 |
| GET被动取样，30ms sleep | 10.088秒/99源/208请求，1次EXPIRED，最大帧龄257ms |
| GET被动取样，5ms sleep | 10.040秒/99源/427请求，当前帧均新鲜；新帧到达时旧源年龄仍达266ms，不能保证跟随连续 |
| 推送stream shadow | 10.040秒/99新源/225条READY，最大帧龄202ms、中位102ms，95条软件建议，全部1425µs；TIME_LIMIT正常结束 |
| stream窗口业务 | 相机同PID、113新检测帧，主/可选新增超限与gap均0，寄存器写0，日志0600 |

以上是不同实况时段的诊断窗口，不是相同输入性能对照；10秒通过不构成最坏延迟保证，也没有验证运动方向或目标移动时的实体居中效果。

## 安全停启和计数边界

相机PID1308正常停止（Result success/status0），fresh checkpoint精确匹配PID/birth、无pending/active/fence，ZOCL引用0。checkpoint SHA `65c6013e09c4e7493a0f1e54d3ca4a821a8f0f1d4099ae31483f10567570ff19`。随后同boot启动PID17671，计数/恢复预算承接通过，GUI PID1307保持。

原相机源码SHA `9d714b9bd00ea1da12088fa1e22100d7bdb689d0cac10332c3933b31e4f4d2df`，原native入口SHA `839df536696d16c3f538bb158edee80614fb0cef55def64d7e7849d412fa30d4`；新release6文件和原入口8个pins审计通过。服务保持Restart=no、KillMode=process、SendSIGKILL=no、TimeoutStopSec=infinity。

更早的物理断电仍造成历史断档：PID8272未生成clean checkpoint，下一boot从旧PID6351启动，主周期overrun旧boot记录4、新boot初值1。该断档未被本次修复或伪造回填；新boot内PID1308→17671的干净承接已建立，两个范围分别记录。

## 当前未闭环事项

1. **当前PL为官方DPU固件**：冷启动后VSRV/2未自动恢复，manual backend为FAULT（`Exact board/boot/firmware/VART context required; no MMIO`）。恢复实体调节需在当前boot成套加载联合固件并核对ID/STOP、当前FDT/VART及业务，不仅改boot字段。
2. **SFace保护锁定**：PID1308停机前SFace累计1次超限，PID17671随后累计3次，2次恢复预算用尽后LATCHED，identity_ready=false。最后一次native报告已完成且fresh，但约32.657ms并触发hardcap；owner未fence。stream十秒窗口内新增为0，故该窗口通过；之后全业务终审未通过。保留保护和计数，不重启解锁、不将其归因于理发或stream。
3. **实体跟随**：1435等机械中位未设定，方向/零点/最终行程/负载与线束尚未验收；本轮建议固定1425不能证明左右极性。后续先恢复窄范围手动按钮，再真人确认方向，最后做限幅、低速、受监督随动。

SFace数值证据、clean checkpoint和完整stream摘要位于[evidence](evidence)。不共享原始UART、图像、身份库或人名。
