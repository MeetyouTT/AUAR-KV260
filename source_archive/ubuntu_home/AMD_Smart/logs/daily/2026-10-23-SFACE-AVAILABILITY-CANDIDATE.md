# SFace持续可用性与语音错误状态修复候选

用户问如何解决项目问题，随后指定YuNet偶发超限由另一个AI审查、Ubuntu先处理其他事项。已按规则复核ZIP/项目/共享入口和当前正式源，新建独立workspace aura-sface-availability-20261023，不开agent。只改相机dpu_sface/camera_faces/live与实际GUI消费spoken_query4份候选，不改YuNet、共享调度/30ms/5ms、模型/阈值/库、语音配置、位流或运动。

旧正式源3个反例确实失败：SFace保护停用后仍ready、仍显示TTL内缓存姓名、语音ERROR误当UNKNOWN。候选增加轻量持续可用性及原因，使health/view/预览/登记/采样一致；错误状态不显示缓存匹配，登记及新采样拒绝，删除/取消仍可用；语音返回identity_unavailable。普通时隙争用、UNKNOWN及CPU/Windows参考兼容保持。自动恢复没有实现，不把状态修复当恢复完成。

本机92项相关回归通过，旧源3反例按预期失败。首次系统Python无numpy，改用已有离线Vitis-AI镜像；扩大回归缺pipeline_metrics，读回实际依赖并重跑通过；额外旧语音模块缺test_simple_enrollment夹具，未计为通过，专项覆盖ERROR/UNKNOWN消费。KV260 helper c3f602be…实际16项隔离合成通过（1.791秒），SQLite全部16个`:memory:`，VART/XIR导入被禁止，不读真实照片/库或开第二DPU owner。前后camera333557/GUI333586和4份正式源SHA保持，没有部署候选。

重要现场变化：隔离检查开始前已读到YuNet第三次82.926870ms/guard+0.358214ms，当前CPU_YUNET_FALLBACK_AFTER_DPU_OVERRUN、LATCHED/unsafe_or_unknown_completion，累计faults3/attempts2/recoveries2。随后只读确认YOLO9.94、SFace仍DPU2534次/超限0、gap0。没有重启/解锁或解释为本候选已修复；完整三次数值环已写用户指定另一AI的交接。时序不证明或排除系统并发负载影响，根因由审查任务处理。

GUI只读利用现有日志与240帧profile，没有开启新profiler：core p50/p95 38.492/76.711ms，total41.263/79.476ms，public1.023/2.072ms，compose1.205/2.465ms，jpeg0.118/0.240ms。12个5秒窗口均IDLE。实际worker源码读回证明core为controller.tick整体，包含控制/音频/动画，不能把该墙钟当纯绘制CPU；下一步细分此段，不盲目重复改当前约1ms的快照路径。4份GUI参考源读回SHA保存，没有启动另一套UI。

共享[候选包](/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-23_sface_availability_candidate/README.md)封存66工件/54Python AST/JSON/SHA通过；4源patch、旧反例/92软件/16板隔离、父版本PIN和实际依赖、GUI阶段证据齐备，不含真实音视频/向量/库/权重或原始UART。[第三次故障补充交接](/home/ghmd/Win共享文件/协作任务/2026-10-18_双机联调/YuNet审查交接_第三次超限与保护锁定_20261023.md)需与另一任务准备的两故障版DeepSeek包一起读。入口/Ubuntu回执/索引/active优先级已置顶更新，另一任务新增段落原样保留，Windows回执未代改。

限制：候选未正式激活，以保留另一AI审查现场；SFace自动恢复、GUI CPU收益、真人精度/强负载/冷启动仍未验收。后续合并双方最新源，分相机与GUI组件协调接入，不原地覆盖封存release。
