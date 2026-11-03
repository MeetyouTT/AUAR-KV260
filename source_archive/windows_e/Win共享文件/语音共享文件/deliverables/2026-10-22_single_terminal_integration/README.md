# 单终端接续验证

2026-10-22。按用户最新约束，仅主任务串行执行，没有启动并行Codex。接续[前阶段结果](../2026-10-22_parallel_pipeline/README.md)，本轮完成音频维护引擎测试与板端虚拟出口检查，并串行合并模型候选。机器状态和最终证据以本目录`release.json`为准。

## 音频维护引擎

`audio-maintenance/idle_maintenance_engine.py`修正了重复请求和关闭后stream的状态处理：同一受理事务重复请求不再次重建，改变内容或旧事务拒绝；最多保留32个请求ID，不淘汰后允许回放。关闭后不再接纳stream。原stop静音保活语义保持。

补齐异步NULL确认、关闭失败/超时不创建第二管线、预热超时/晚到返回、令牌/参考代次、限次、owner线程和关闭检查，**20项软件测试通过**。晚于截止返回或poll异常时请求NULL并保持失败屏障，保留对象供关闭/监督处理；不把NULL请求当成释放已确认。原生调用本身卡住仍需外部进程监督。

本板GStreamer1.18.5以合成静音数据和`fakesink`执行实际生命周期：旧管线确认NULL后创建新管线、预热、参考sequence保持/epoch推进、重复请求不重建、close后拒绝stream；所有虚拟管线最终NULL释放通过。**未打开ALSA/MCP01、未播音/录音、未接入当前UI/IPC，也未证明USB根因修复。** 引擎最终源SHA与板测报告一致，详见[evidence/audio-dummy-final.json](evidence/audio-dummy-final.json)。

首轮草稿检查失败与后续修正日志保留，不能以最终通过覆盖失败事实。6份音频实际依赖已私有回收并记录SHA，共享仅含必要两份引擎参考源码和依赖清单；原控制器、ASR队列、AEC参考的原子屏障和worker回执仍是生产接线前置。

## 模型候选合并

在新`merged-candidate/aura`合并13源码：SFace独立供给和RAM标定、正常wall/调用线程CPU统计，以及采集单copy移除。**56项身份/供给回归＋45项计时/运行器回归，全部通过。** 原冻结候选未改写，13源的上游/合并SHA见`merged-manifest.json`。

合并包在板端Python3.9.9完成13模块导入、原Windows身份配置校验、默认开关和合成正常计时检查。导入检查禁止XIR/VART导入与SQLite连接；没有创建真实runner、新相机、音频设备或身份库；合成的1次native完成标记是协议检查，**实际DPU调用0次**。见[evidence/merged-import-contract.json](evidence/merged-import-contract.json)。这不是合并包的真实推理/现场识别验收，新辅助功能未常驻。

共享目录布局也已实际复跑同样两组56＋45项，以及从交付中recovered-engine运行音频20项，均通过；这些是复现检查，不重复计为新增测试数量。Ubuntu上可运行`python3 -B run_merged_tests.py`；依赖既有Vitis AI容器、同版回收源码及ONNX依赖，可通过`AURA_LIVE_SOURCE`和`AURA_PYTHON_DEPS`指定本机根。原执行脚本在source中保留作为过程证据。

## 采集单copy实际运行检查

主任务另设隔离源目录，只更改原UI的一处`.copy()`，未把13源、标定或计时同时切入相机。**60.18秒真实UVC观察通过，YOLO9.936帧/秒、实际采集12.479帧/秒、0新增匹配USB告警；完成后恢复原保留配置，回退timer停止。** 原UI215734和Xserver1077在短测与恢复期间保持，相机恢复后PID264975。原6源码/模型/manifest/单元/身份库路径及配置偏好保护通过，影子和统计关闭。完整记录见[evidence/capture-copy-live.json](evidence/capture-copy-live.json)及[evidence/final-active-audit.json](evidence/final-active-audit.json)。

本次是实际摄像头路径的短时行为验收，不是相同输入的整板加速比对照。前阶段的11.9%/21.1%仍只属于两种OpenCV线程条件下的合成输入局部微基准。候选短测通过也不等于全业务长期验收或自动常驻。

## 下一关

音频维护还需要UI命令所有者的原子准入、worker实例/request/token回执及参考订阅处理，未把引擎测试当完整恢复接线。模型路径还需对独立供给的真实任务完成率、主检测时效和音频稳定性做隔离验收；正式INT8登记/阈值与多人独立验证尚未完成。已知30ms占用上限、YOLO guard及原回退策略保持。

原始UART、现场人脸/声音/向量和身份库没有放共享目录。Windows同步/接收与当前远端服务仍需独立验证；本轮仅操作本机文件和授权板卡验证，没有发送消息或改Windows回执。
