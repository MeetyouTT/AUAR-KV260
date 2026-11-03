# 单终端接续：音频维护及模型集成

按用户最新“只允许开一个终端”“继续做”，仅主任务串行执行，没有启动新子agent。重新读取ZIP README、项目规则、最新共享入口/实测和前阶段候选；旧多终端工作仅作为已产出的代码来源。

音频维护引擎补实际继承原PersistentGstAudioEngine的测试。首轮15项出现重复请求非幂等、close后stream落入原错误分支两处失败；加有界32事务ID/内容类型匹配、旧事务拒绝、close后持屏障。进一步补poll晚于预热期限返回和异常时请求NULL/保留失败态。最终20项通过，原stop仍保活、NULL未确认不新建、参考代次/sequence、owner/限次及超时/close行为检查。最终源SHA001898f491e026120f668580d0547698bfcfb97d6e0ceb181d40e6e61a866f30。

本板真实Gst1.18.5＋合成静音/fakesink：NULL确认→新管线WARMING→READY_UNVERIFIED→close，重复事务不重建、旧参考不交付、新epoch/单调sequence、所有虚拟管线NULL释放通过。未打开ALSA/MCP01或新相机/DPU/DB，无新声音采集播放、未改生产。helper7e9ce91c…最终证据在20261022T095718.379606Z-audio-maintenance-dummy-v2；较早helper0b475375…是修正前成功路径快照，不代替最终源。上层UI/worker原子门控和AEC接线仍未完成。

回收此前已传回的真实transcription.py到私有actual-source，补到6份实际依赖SHA清单。测试支持共享recovered-engine或AURA_AUDIO_SOURCE路径，避免拿旧共享控制器冒充实际版本。

新独立13源码合并SFace独立供给/标定、正常wall/threadCPU统计及单copy。Docker56＋45项合并回归全部通过，无网络/只读依赖。源包0dd98eee68320ec7fbf5e60832f88360a88272ffa0ff21423eead8bfccee9d33共42820B以独占UART完整暂存。板端Python3.9.9导入13模块、原Windows配置/默认关闭/合成计时检查通过，实际DPU作业0、DB连接0、无新设备或生产修改。helper3dc41357…，该结果是兼容检查，不是实时推理/身份/利用率验收。

串行准备原UI单copy真实UVC60秒运行验证，helper3a73b43d…、隔离candidate SHA d74e3025…，原单元84116d8f…与源/模型/原库/配置偏好保护、独立240秒rollback timer；完成始终恢复原配置，实际结果后补，不预报通过。生产合并包/正式身份没有启用，30ms/guard保持。

交付入口：Win共享文件/语音共享文件/deliverables/2026-10-22_single_terminal_integration/README.md。实际结果和最终审计完成后更新机器状态及父级SHA，原始UART和现场生物数据留私有。

实际UVC结果：60.183秒观察通过，YOLO9.93632Hz/实采12.47856Hz，0新增匹配USB告警，passed/complete/rollback_verified均true，独立timer已停。新相机264199测试后恢复原保留源/单元为264975，UI215734/Xserver1077保持。6源码/模型/manifest/原库/原配置偏好复核通过；后续日志尾最后保留警告距读取约4991秒，journald仍28次，无新重启。指标仅短窗行为验收，无同输入整板收益或长期稳定结论。

UTC10:13最终再次只读核验相机264975/DPU_YUNET_INT8、当前YuNet真超限0、原单元/源/旧库一致、影子无/统计关闭/全部相关回退timerinactive。共享布局也实际复跑同56＋45项及音频20项，均通过，不计为新增测试。最终94工件SHA、60份Python AST、18份JSON和5个本地引用核验PASS；producer冻结23项、timing冻结16项与13合并源SHA保持。当前正式SFace仍Windows配置，新音频维护/合并包/单copy均未常驻，接线/三模型长期与现场身份仍未验收。用户单终端限制保持。
