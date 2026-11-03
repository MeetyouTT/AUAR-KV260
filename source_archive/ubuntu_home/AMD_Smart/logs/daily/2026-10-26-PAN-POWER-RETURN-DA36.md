# 来电后无运动恢复与固定轨迹离线对照

用户“继续，来电力，但是我有要离开一下”。本轮在主机UTC2026-10-27 00:07后执行（本地10月26日）。只恢复联合平台与原业务，用户不在时未发运动；主终端独占UART/固件/服务，独立子终端仅本地轨迹和恢复脚本审阅。

初检新boot da36c36a-ef4d-4122-8ad6-cfae3931303e，camera1333/GUI1296，默认kv260-benchmark-b4096，转轴旧boot配置FAULT/no MMIO/automaticfalse。实板核对r15 control24/source-v17 11/GUI259及joint4个文件SHA，导出FDT55805463…、本地overlay2ec4fc…合并b18b9dbb…通过。15.039s新增150主推理、primary1保持、optional0；474实流包UNCONFIRMED、149检测轮、无READY/断连；相机/预览/检测错误空，覆盖时间窗内目标USB告警0。不是真人精度或随动测试。

新建独立root `/home/root/aura-pan-current-20261024/da36c36a`，复用审查过的5步恢复脚本并核对当前GUI/ID_STOP工具SHA。正常stop camera1333，fresh CP8205868c…对应boot/PID/birth/quiescent、ZOCL0；stop GUI后独占DPU/motion锁切联合固件，ID/STOP通过flags0/lease0/ack0，没有BIND/REFERENCE/ARM/COMMIT。随后原source-v17/GUI按同boot CP恢复，camera54394/GUI54429，native exact same boot承接，GUI259pins复验。manual仍FAULT且automaticfalse，/dev/mem持有者0。复位width1500不代表实际角度；旧1420/1426均未绑定。未改自动开机固件选择。

本bootprimary从停前/CP的1到恢复后2，新增1保留；不能称全程0超限。另新kernel归档旧seed来自673020/primary27，但前次最后实测720342/29，因此原归档history_is_lower_bound=false/unknown_tail=false不代表完整旧运行历史。只在本次state/交接sidecar明确unknown_tail=true，未修改原始归档/清计数；归档标记缺陷待单独修。

启动有界1800秒只读观察PID55316，使用原pinned monitor88279b…，新root readonly-watch-5378292649339。先取回95.191s/20样本，后于主机UTC00:31再取回725.668s/146样本，0读取错误/0自动跟随，primary2保持、13个内核窗USB告警0且未截断；仅是已取得约12分钟，30分钟未完成。无图片/姓名/声音/对话采集。owner变化/读取错误/到期自动退出，不恢复业务或发动作。板端墙钟2021错误仍保留，时长用monotonic、主机证据UTC2026。

离线fixed_motion_isolation_20261026用同一现役Ruckig主机库生成2s±5us、20ms共101样本，限速/加速度/jerk20/100/800，端点静止/最大整数step1。随后补run_fixed_motion.py注入式有限执行核心：同一2s截止、98次完整提交、40ms结束预留、错误优先/finallySTOP、不可变ACK快照、禁止短间隔追赶。25项过（8数学+17行为），保留98条完整Fake记录；主审提出的19ms迟到→1ms密集补发、最终STOP超过期限仍PASS、可变ACK改写历史3个反例已修。首轮测试一项失败是Fake到期在STOP后继续覆盖flags的夹具缺陷，已修正并重跑。核心SHA ed11be3b…，无真实硬件adapter；CLI默认PLAN_ONLY/execute拒绝，不能把dataclass许可字段当授权证明，也未解决native最后写Q09。现役r15不变。

原bench真实源码与缓存板端字节一致，实际1秒保持后跳5us，并非平滑轨迹。无视觉时首整数改变160ms、到3us380ms仅数学结论。历史manual1402..1420，+5至1425只是数学对称；未来确认1420可先负向1415往返。旧r14 220/234不完整、幅度不同，不能称配对；固定与真人同条件完整轨迹对照仍待返场，r15物理平滑未验收。共享代码只是源快照，主机库依赖仍位于原Ubuntu目录，未宣称Windows可独立运行。

前置错误：UART封装超3800、传输清单缺ops_root、本地fdtoverlay缺libfdt路径均在上板操作前拒绝，改用immutable文件传输/补字段/仅命令级LD_LIBRARY_PATH修正。首次恢复后GUI接口连接拒绝处于启动期，后续active/IDLE_READY核对通过，未重复restart。

完整源/证据/下一步：[来电恢复与固定轨迹对照](/home/ghmd/Win共享文件/协作任务/2026-10-26_来电恢复与固定轨迹对照/README.md)。本机最新交接为aura-pan-board-20261024/POWER_RETURN_HANDOFF_LATEST.json，旧POWER_OFF_HANDOFF_LATEST.json保留历史。共享入口只改本任务marker，未覆盖Windows回执；未共享原UART/FDT/私有图像或录音。
