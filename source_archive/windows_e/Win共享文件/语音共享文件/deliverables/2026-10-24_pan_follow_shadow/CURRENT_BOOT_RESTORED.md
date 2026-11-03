# 当前boot：联合固件与手动转轴已恢复

UTC 2026-10-25 03:32，boot `463c9307-5e47-49b0-b22f-5fd3fc21451c`。**当前VSRV/2联合固件已加载，手动调节面板READY；实体自动随动仍关闭。** 相机PID27275、GUI PID30738、手动后端30808。较早报告中的“当前为官方固件、manual FAULT”已由本页更新。

## 已实际完成

- 原位流、xclbin、DTBO和驱动SHA配套复核通过；当前FDT SHA `27960a4871bd04dd6e33854eab4542c267f3cd3014f210bab0b578e2a2c200e6`与同SHA候选DTBO独立合并通过。
- 正常结束相机PID17671，fresh checkpoint `d763407d9498217f6e812aad3851f7bfd0a019ca6d1f76bb3816c7113639dc24`，PID/birth、无pending/fence、计数不降、ZOCL0通过。保留SFace累计3超限/恢复预算LATCHED；未重启解锁。
- 加载`aura-visual-servo-b4096-v2`，ID/ABI2/build778d2512与STOP通过。随后恢复原生相机和GUI，原相机源码、模型、身份库与既有unit/drop-in保持。
- 在已观察过的1425～1445µs内完成本boot初始化1430→1425µs，再做1425→1445→1425µs往返。往返44 ACK，最后事件1992.23ms，flags0/lease0/active=false/armed=false、width/target1425。用户反馈“看到了，来会停住”，绑定本次trial SHA `4379c764507ac36de3d68720d6694dfbfc325e3d819784377f18c4fdf2227d7b`；没有复用旧boot人眼证明。
- 新GUI在独立clone中只更新boot绑定的手动配置，254组件pins通过，保留旧GUI目录及用户偏好。新manual release为`OBSERVED_MANUAL_VSRV2`，仅有限手动1425～1445µs。面板已打开，backend READY，脉宽指令1425、输出关闭，面板打开本身没有发点动。
- 联合固件下补做stream shadow：5.06秒/51新源、最大帧龄192ms，目标贴边触发HORIZONTAL_BORDER软件停锁，46条软件建议1426～1445µs，寄存器写0；相机同PID、主/可选超限和gap新增均0。该次不是完整10秒；此前完整10.04秒shadow证据见[推送报告](STREAM_V2_REPORT.md)。

## 仍未完成

左右物理极性未获本轮确认，机械零点/最终行程/负载线束未标定；目前只能人工按钮有限点动，未接实体自动跟随。SFace保护LATCHED仍保留，身份整机验收未过。旧boot因物理断电丢失的计数连续性不伪造补回；本boot受控停启承接已验证。

本次是当前boot恢复；下次冷启自动加载联合固件/安全承接尚未验证。外部PWM没有仪器实测，寄存器ACK和用户观察分别记录。

当前状态见[PROGRESS.json](PROGRESS.json)，过滤证据见[evidence](evidence)。部署脚本和新UI配置准备工具位于[source/deployment](source/deployment)，不含原始图像、UART或身份数据。
