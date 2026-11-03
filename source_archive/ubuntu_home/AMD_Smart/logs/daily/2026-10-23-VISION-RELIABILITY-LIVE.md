# 视觉可靠性修复正式部署

封存前只读续查：同camera450495/GUI450525、unit29786434保持，YOLO累计9.89Hz，YuNet1479次、SFace52次完成，optional超限0、gap0、diagnostic_failures0、owner_fenced=false、身份ready。52次包含观察前后的自然运行，不回填成正式60秒窗口推理量或准确率。final-liveness.json已追加并重新封存SHA；协调工作目录ACTIVE_RELEASE/CHECKPOINT更新，原a290指针单独归档，不修改原冻结交付。

用户要求解决已确认问题并继续，明确允许新开一个终端。主任务串行持UART/部署，副任务仅离线独立审查和测试；中断接续后原副任务已退出，重新单一副任务继续部署审查，全程最多两任务，无第二DPU owner。开工已按ZIP/项目/共享入口/最新回执及原实板源复核。

9份业务源：dpu_vision_schedule、pipeline_metrics、dpu_vision_runtime、dpu_yunet、face_targets及原SFace dpu_sface/camera_faces/live、GUI spoken_query。辅助诊断finish在释放后聚合，begin/finish/error/snapshot异常清理不泄漏active，迟到trace不清新owner；健康snapshot明确non_atomic。成功status0长尾沿用原保护/恢复；native完成无法确认时typed error使所有新DPU准入owner_fenced，不盲重投或称硬件已取消。worker异常后ready=false、拒新帧/等待协调关闭，真实is_alive/fault计数；fallback次数/耗时/原因直记。SFace停用不再伪ready/消费旧结果，登记/采样拒绝、删除取消可用；GUI把ERROR与UNKNOWN分开。SFace自动恢复没有实现。

210项软件回归通过，含独立23项真实线程/故障审查；26项部署/恢复回归通过。期间独立审查拦住了候选最终接受须严格fault0/primary起点、foreign dropin集合等问题并补反例。前期旧fixture缺初始化/旧不支持SFace断言、未知native后允许复投的旧期望已按明确合同更新，未隐瞒失败。KV26071项隔离检查全通过、禁止VART/XIR且合成内存库，无新的真实模型执行。

真实发布挫折：第一helper60d81145…要求无目标也必须有sface job行，候选出帧且YuNet正常仍被错误验收器拒绝，已协调完整恢复a290/445907/445937、guard/override清理；补模型ready/零请求反例。第二helper18df18c3…GUI clone错误继承旧stage.log软链接，启动器relative_to正确拒绝，多次重试日志留档，控制器超时后完整恢复a290/camera447318/GUI447344、自有override及timer移除；补排除stage.log反例。第三269026b9…在切换前发现旧SFace36.742758ms/status0/guard未越界已停用，20次完成后持续defer、顶层仍ready；前置拒绝无生产变更。故障数值留档，与原333557 YuNet3故障分进程。第四f7624754…仅允许已确认native完成的父版停用进入有timer协调重启，候选仍严格fault0；没有放宽30ms/5ms。

最终正式unit SHA **29786434df9bb9b94a8e640a7a48db47019c224d3876037ce27d3467bb2f5512**，release `/home/root/aura-dpu-vision-20261021/postpower-retry-live/release-reliability-f7624754038f-450136`；camera450495、GUI450525、Xserver1077，新GUI在release/gui-runtime。GUI复制175份实际Python源仅spoken_query改变，原资源目录/原生库软链接保持、设置独立复制；原GUI cfg/launcher和旧dropin受保护，只新增自有reliability override。先ARM独立600秒恢复timer，再关GUI/PCMclosed/切相机及GUI，之后观察并最终校验才停timer。前两轮实际回退可核，最终版本没有为测手动入口而撤销。

**60.518819秒真实观察通过：** YOLO9.930795Hz、YuNet发布3.816995Hz/231次真实native完成、整板CPU56.918718%；窗口新增primary/optional超限、逐发布gap、USB/诊断错误0。启动累计primary超限1保留。SFace启动完成5次，正式窗口新增0；接受后只读累计6次，不能宣称本轮持续三模型高负载、本人/异人精度或同输入CPU收益。窗口人与输入不同，56.92%不与前真人66%直接相减。

最终审计与12份关键源从板端读回SHA通过，880相机包与175GUI源核验。identity配置SHA398ece6a…保持，原INT8库ee22b97d…与原Windows库e0d2113e…保持，无登记/迁移；0.50/0.10、模型/身份域、GIL1ms/TTL/YOLO周期锚点/30ms/5ms不变。回退--check实板通过，aura-handoff-restore-reliability-450136.timer及controller inactive，三主服务active/NRestarts0、音频IDLE_READY。未切位流、USB复位或操作转轴。新/旧计数按进程分别保留，不因重启归零称等待根因消失。

交付[源码、证据及运维](/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-23_vision_reliability_live/README.md)，104工件/77Python AST/14JSON、12源匹配与SHA通过；完整失败/恢复、旧SFace故障及原YuNet环均保留。共享入口/Ubuntu回执/索引及active优先级更新，Windows回执未代改，未称跨机已同步接收。原始UART、真实图像/音频/向量/库和权重不共享。

仍未完成：82ms native marker等待唯一根因、SFace有界自动恢复、GUI CPU内部热点/严格同输入收益、异人/多人精度和冷启强混合长稳。当前修复解决可用性/资源清理和可观测性，不把短窗通过称根因根治。
