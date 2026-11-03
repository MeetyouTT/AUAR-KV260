**最新已接受SFace正式DPU三模型业务：** unit a29082ba…/camera333557，现行入口为[三模型交付](../Win共享文件/语音共享文件/deliverables/2026-10-23_sface_formal_dpu/README.md)和`/home/ghmd/aura-sface-formal-20261023/ACTIVE_RELEASE.json`。本目录早期release源码只作历史。

# 当前结果：协调切换与YuNet恢复已启用

当前版本已推进至unit `048ee59c…`/相机298571，YuNet通知等待与独立取消实板通过，双模型DPU。最新入口为[实板交付](../Win共享文件/语音共享文件/deliverables/2026-10-23_yunet_event_slot_wait/README.md)与`/home/ghmd/aura-yunet-slot-wait-live-20261023/ACTIVE_RELEASE.json`。本文e89393 bounded-recovery及更早配置均为历史。

最新复查：相同相机198117在进程启动2263.609秒后YuNet31.340203ms超原30ms硬保护，现已回CPU；YOLO仍DPU，正式SFace仍Windows。故障窗口匹配USB告警0，唯一原因未定。原30分钟通过及20分钟审计保留为历史，不再代表当前双DPU状态。最新证据见[运行复查](../Win共享文件/语音共享文件/deliverables/2026-10-23_runtime_overrun_recheck/README.md)。

最终状态以[共享交付](../Win共享文件/语音共享文件/deliverables/2026-10-23_coordinated_camera_audio/README.md)、`ACTIVE_RELEASE.json`和最新板端审计为准。

原版协调120秒、候选120/600/1800秒与实际启用R2独立120秒通过。当前camera unit `af337bce…`，活动目录`/home/root/aura-dpu-vision-20261021/postpower-retry-live/release-recovery50-946d1a0d500f-197870`，相机198117/UI198147/Xserver1077。原unit84116d8f…已备份；旧固定原unit的helper不能用于当前实际版本。

首次实际启用EDA…超限回退，记录保留；对齐监测负载并补故障快照后的R2 63d4244d…启用通过，不把额外监测认作唯一已证明原因。当前slot retry、light3、失败轮次50ms与进程GIL1ms启用，成功节拍200ms、30ms/5ms/TTL保留。20分钟后续回读879文件与当前运行状态通过，gap/超限/真实native失败0，guard及CU统计关闭。

当前boot专用只读/显式回退入口已安装；未执行手动回退来撤销最终版本。正式SFace仍Windows/旧库，未改语音模型、运动或位流。真人/强交互与冷启动需要现场验收。工作结果已冻结共享；本目录早期manifest中的prepared/未执行只反映对应生成时点。
