# 接续约束

本轮恢复现有 voice-chat-memory-20261029-r9，没有新部署或改指纹。以verification.json、endpoints.json、voice_probe.json和README为运行状态证据。r9功能与性能报告仍在../2026-10-29_chat_latency；不要重复旧部署或覆盖其数据。

当前板卡boot 605eaf50-c66a-4559-bfc9-5ae177e0f305，UI1296/相机1333，实际运行配置/home/root/aura-boundary-nav-20261029/gui-page-sync-v2/startup/config.json，根/home/root/aura-boundary-nav-20261029/gui-page-sync-v2/runtime，279组件匹配。并行任务将下次启动unit配置改为/home/root/aura-avatar-startup-speed-20261029/config.json，运行进程尚未切换；必须读/proc/MainPID/cmdline及systemd两者，不能回退该并行更新。以后每次动态重查，本文不是永久绑定。

转轴FAULT、脉宽null、跟随/监听/麦克风关闭。当前加载benchmark固件，驱动要求wide-v1，boot/FDT/VART也不匹配；完整对照motion_binding_audit.json。所需安装文件哈希保持不代表已经加载或运动可用。只读核对没有导入驱动/MMIO/改绑定/切固件/运动，不能只写新boot或恢复旧1604脉宽。后续复机必须协调DPU使用者和并行任务，成套恢复正确wide固件与VART、核验本次环境与实体位置/STOP；保留机械保护。

本轮当前基线是144会话/276轮、188实时缓存/183视觉历史，不能按旧77/73或143/273覆盖。恢复后实时缓存187：原24小时策略自动清理1条过期记录，cache_retention_verification.json严格证明，其余源表SHA不变。database_verification.json初次全表相等失败保留，不能删掉该记录或称所有表逐字节相同。真实私有库仍用独立隐藏WMI视图，备份留AppData，不复制身份数据或权重到E盘。

恢复原启动器成功后的首次收尾因并行unit改变而拒绝旧入口确认，recovery.json保留原失败；recovery_resolution.json和verification.json给出后续实际进程核对结果。不应为清掉这条历史记录重跑恢复/结束脚本。业务源码无改动，其他模型运行和D盘LLM存储保持，无新自动任务；板端迁移继续暂缓。
