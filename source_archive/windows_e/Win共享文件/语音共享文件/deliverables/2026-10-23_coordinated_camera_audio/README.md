# 原音频与相机协调切换

**当前已实际启用新版本。** 相机198117、界面198147、Xserver1077；活动camera unit SHA为`af337bce…`，原`84116d8f…`作为回退保留。位置、实际源码与审计见[ACTIVE_RELEASE.json](ACTIVE_RELEASE.json)、[运维入口](OPERATIONS.md)和[最终审计](evidence/active-release-final-audit.json)。后文的原版本测试数字属于历史窗口。

已实现受保护的协调顺序：原音频关闭且MCP01 PCM确认closed后，才stop/start相机；相机健康后恢复原偏好并启动原音频。正式观测窗口内音频正常运行。独立restore进程复用同一协议，源码/config/偏好/模型及Xserver PID均校验；不覆盖后来出现的其他配置，original already-ready恢复幂等。启动后允许预期的GUI PID变化，观察期间仍锁定新PID。

源码见[handoff.py](source/handoff.py)、[故障注入](source/test_handoff.py)、[生成器接线检查](source/test_generated_trial.py)。16项协议/保护反例＋6项生成接线共22项软件检查通过。原89项50ms恢复代码、模型/runtime/GIL包装字节保持，同源观察器35项板端成本前置仍是[上一轮冻结证据](../2026-10-23_yunet_gap_recovery/README.md)。协调模块只控制切换，不给每帧增加新的计算。

|实板阶段|结果|
|---|---|
|原版本协调切换120秒|120.566秒，YOLO9.953Hz/YuNet2.505Hz、CPU55.18%、USB0/硬超限0；原unit84116d8f…保持，独立恢复幂等通过、guard停止|
|同版协调＋50ms恢复120秒|120.990秒，YOLO9.893Hz/YuNet3.199Hz、CPU56.85%，USB/硬超限/逐发布gap均0；25快照源帧龄max401ms，协调恢复verified|
|同版600秒|600.350秒，1867次窗口native完成，YOLO9.951/YuNet3.110Hz、CPU56.47%，USB/硬超限/gap均0，121快照max716ms；协调回退verified|
|同版1800秒|1800.440秒，5603次窗口native完成，YOLO9.953/YuNet3.112Hz、CPU56.44%，USB/硬超限/gap均0，主检测周期计数1→1，361快照max570ms；协调回退verified|
|实际启用后的独立120秒|120.315秒，YOLO9.974/YuNet3.325Hz、CPU55.70%，USB/硬超限/gap均0；完成后停止保护timer并保留新配置|

120/600/1800的完整私有报告保留板端，过滤的逐样本数字、报告SHA在[完成窗口证据](evidence/completed-trials-projection.json)。最终已启用进程运行约1230秒时，累计gap/硬超限/真实native失败仍0，879个运行包文件、入口、原备份、正式身份与GUI配置通过回读。诊断native_failed中的守卫撤回已与withdrawn_after_slot逐项核对，不把撤回计成硬件失败。

|独立15秒负载采样|整板CPU|XRT DPU任务忙碌率|完成命令|
|---|---:|---:|---:|
|原版本，15.150秒|55.03%|4.868%|189|
|已启用版本，15.169秒|54.93%|4.934%|196|

上述DPU数字是XRT任务忙碌率，不是MAC利用率或FPGA资源占用；采样前后相机PID/后端保持，统计最后关闭并验证停止计数。两个实时窗口不构成同帧A/B，不能据此宣称显著硬件利用率提升。主收益证据是结果连续性和稳定调度。可直接导出[PNG](results/runtime-results.png)、[PDF](results/runtime-results.pdf)、[SVG](results/runtime-results.svg)及[CSV](results/measured-windows.csv)。

USB游标从PCM关闭后、相机及音频启动之前采集，覆盖后续启动与观测，不能只截取音频启动后的干净窗口。CPU/FPS为不同实时窗口的描述，不是同帧A/B加速比；恢复wait累计28含启动期，不是120秒窗口增量。

当前相机使用进程内1ms切换间隔、最新帧有界重试、失败轮次50ms恢复和light3数字观察；成功发布仍200ms、原30ms/5ms及输入/发布TTL保持。实际接线源码见[face_targets.py](active_source/aura/board/identity/face_targets.py)、[camera_faces.py](active_source/aura/board/identity/camera_faces.py)、[间隙观察器](active_source/aura/board/identity/face_freshness_metrics.py)。未更换Windows SFace/旧身份库或语音模型配置，未操作运动/位流。当前正式DPU模型是YOLO和YuNet，SFace正式特征提取仍在Windows。

首次实际启用复核发生YuNet超限并自动回退，失败完整保留于[首次启用记录](evidence/first-activation-failure.json)。上线检查原先每5秒重复全量哈希和额外健康查询，随后将监测负载对齐已验证的长测，并补故障快照，第二次启用通过；尚不能证明额外检查是首次超限的唯一原因。USB内核驱动根因也未完全确定，已验证的措施是相机切换时先关闭音频，窗口内恢复正常音频运行。

本轮为用户离场时的空/少人脸、语音空闲负载。真人识别与强交互、真实听音及冷启动尚未重新验收，图中的稀疏帧龄不能替代逐发布gap计数。原始UART、音频/图像/特征、偏好原件与权重不共享，私有快照用于受保护回退；Windows同步接收未代确认。

helper写死当前boot/source路径。请按[当前任务](../../../协作任务/2026-10-18_双机联调/自主推进_20261023_相机音频协调.md)及Ubuntu实际结果接续，Windows回执由Windows维护。
