# 转轴视觉随动 Shadow 候选

<!-- pan-face-edge-v5-20261024 -->
**人脸边缘随动：10.024秒输入实测通过，GUI激活中。** [当前报告/源码/证据](FACE_EDGE_REPORT.md)：camera66241，人脸区域模板测量180新源/288 READY、最大帧龄162ms/中位58ms，中间保持1425µs，寄存器写0、新主/可选超限0。按脸框8%触发/18%退出、平滑限速，实体试转仍待做。用户报告画面反复丢失已定位MCP01 USB slot04播放端点报错，关闭音频后仅重置MCP01并恢复GUI，0.3秒4440条降0；用户确认“稳定了”。YuNet当前CPU保护回退/SFace LATCHED保留，不清预算。下方旧阶段均是历史。
<!-- /pan-face-edge-v5-20261024 -->


**当前boot更新：VSRV/2联合固件和手动面板已恢复READY，本boot20µs往返已获用户确认、最终STOP。** [当前状态与限制](CURRENT_BOOT_RESTORED.md)。范围1425～1445µs，左右极性未确认，实体自动跟随仍关闭。下面的stream报告保留前序过程。

**最新：推送式只读通道已完成10.04秒shadow，99个新源帧，最大帧龄202ms，寄存器写0。** [当前报告与限制](STREAM_V2_REPORT.md)。相机PID17671、GUI PID1307；当前PL为官方DPU固件，VSRV/2实体控制未恢复。SFace在窗口后进入超限保护LATCHED，全业务终审未通过；保护和历史均保留。自动跟随关闭。

下文为前序接口和失败记录；最新状态以[STREAM_V2_REPORT.md](STREAM_V2_REPORT.md)及[PROGRESS.json](PROGRESS.json)为准。

## 前序阶段记录

- 当前新boot `463c9307-5e47-49b0-b22f-5fd3fc21451c`，相机PID1308/GUI PID1307，VSRV2 manual backend因Boot mismatch显示FAULT；自动跟随关闭。本次没有改相机业务源码、没有切固件、没有发送转轴命令。
- 当前 `GET /v1/motion/observation` 返回200/READY，source_age约45ms，选中目标可见。只读AST检查及实板实际handler启动通过；当前相机源SHA仍是 `9d714b9bd00ea1da12088fa1e22100d7bdb689d0cac10332c3933b31e4f4d2df`。
- shadow建议硬限在1425～1445µs、4µs/帧、40µs/s；1425仅是最近的停止指令，不是机械零点。相机方向及机构标定字段明确为false。
- 36项控制/源帧合同检查、2项受保护入口分派检查、1项纯shadow无IO/限幅检查通过。CameraState逻辑测试使用本机共享项目基线；当前运行源另做只读AST字段检查。90条历史fixture回放中86条得到软件建议，最后`REPLAY_ENDED`并disarm；仅为合成数据，不代表实况或实体随动。
- 实时尝试采到1个新READY源帧（年龄165ms）；目标框触发`HORIZONTAL_BORDER`，ShadowDriver软件停锁，建议0条，寄存器写0，耗时约0.037秒。相机同PID，期间主/可选新增超限和gap均0；因边界帧立即锁停，没有完成10秒连续shadow。
- 手动UI的实体按钮测试仍待用户现场操作；现有一次机械往返确认不等于左右方向/随动极性已标定。

## 当前板端阶段

受保护启动入口与只读坐标路由包已传到专属ops目录，SHA复核通过；本任务拥有的systemd drop-in在断电后随下次启动生效。现在新boot的相机/GUI、原生DPU业务就绪，实时route可用。

入口shim和shadow-only runner源码见[source/shadow_runtime](source/shadow_runtime)；安装/停启/验checkpoint工具见[source/deployment](source/deployment)。

上次power cut发生时停止控制器尚未确认UART root shell，所以相机没有得到正常停止信号。断电前最后看到PID8272；本次启动继承的checkpoint仍是PID6351，主周期累计overrun从旧boot已记录的4显示为新boot的1。计数连续性断开，两个boot的数据分开保存；不把差异解释为故障减少。新boot当前相机PID1308健康、owner未fence、YuNet/SFace新增超限均0，尚需后续长窗确认。

当前转轴手动backend在新boot为FAULT/Boot mismatch，寄存器readback未取得；故实体停止状态/脉宽不推断。本次shadow代码只读route并使用ShadowDriver，没有VSRV import或寄存器写入。下一步让选中目标完整进入画面中间，再做一个10秒shadow；之后仍需UI左右按钮的真人方向确认、机械参考与线束/负载核对，再讨论受监督实体随动。自动跟随保持关闭。

## 2026-10-25 UTC：USB恢复后的板端实况

用户接回USB后，实际boot为`463c9307-5e47-49b0-b22f-5fd3fc21451c`；camera1308/GUI1307，原生DPU owner健康、YOLO约9.89Hz、identity/worker ready，实时route返回READY，source age约45ms。说明断电后已由暂存drop-in启动shim；不是本代理安全stop/start。当前manual backend仍FAULT/Boot mismatch，readback字段null，自动跟随关闭。

startup仍读取旧PID6351/boot1236… checkpoint；主周期overrun当前boot为1，而旧boot断电前记录为4。**计数连续性因此中断**，不把计数下降解释为故障减少，也不回填伪造当前寄存器状态。新boot shadow前后主/可选超限与gap增量均0。

实时shadow只获得1条READY源帧（age165ms），选中目标触发`HORIZONTAL_BORDER`，0.037秒后软件DISARMED；建议0条、寄存器写0。试验因输入目标靠边而安全停锁，10秒窗口未完成。两个更早的runner启动问题是模块别名和PYTHONPATH，均发生在shadow循环前且无硬件访问；修复后才得到上述一条实况输入。

下一步待选中目标完整居中，再运行一个10秒shadow窗口。维持ShadowDriver、窄建议范围，不动作实体转轴；视觉极性、机械参考与按钮方向仍待现场确认。
