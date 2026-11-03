# 下层手臂自然摆动 R3

用户明确反馈 R2“下层手臂幅度太大，优化幅度确保摆动自然”。本次已将画面下方/后侧垂臂收小、放慢并增加阻尼，R3 已由原 GUI 实际加载，380 项来源匹配、角色可见、故障 0。R2 的该项观感未获接受；R3 的现场人类观感尚待反馈。

[前后 GIF](previews/before_after.gif) 左 R2、右 R3；[16fps MP4](previews/before_after_16fps.mp4) 保留完整时间轴；[抽帧总览](previews/contact_sheet.png)。均为同一 KV260、同模型、同纹理、同种子、同尺寸和时间轴的原生离屏录制，不含现场相机或音频，GIF 为8fps便览。

调整限定在 `aura_arm_left`，对应 A 姿态下层/后侧的 `腕LA_le`（原图0059/0052），也作用于 B 姿态同侧分支。目标波幅由6.5+1.3改为2.6+0.45，主周期4.8→6.8秒，阻尼0.58→0.85，角速度上限16→6度/秒。R2 的肩部支点补偿、胸前手臂、头部/躯干、头发与附属物理效果保留。实际用户语义、音色、身份、记忆、相机和转轴配置均保留。

60000个逻辑author tick的同编译条件对照中，下层臂关节角范围由 -9.24～9.28 度收至 -3.52～3.53 度，约为上一版的 38.1%；峰值角速度 11.19→3.09 度/秒。其余5通道共300000次数值逐项相同。这里是局部关节角，不是实体转轴角或整条手臂的屏幕总位移。

比较程序实际运行于 KV260 CPU，不打开显示、GPU或音频API；60000个逻辑tick不等于1000秒整机运行。原始程序输出中 `device_or_GPU_used=false` 是未调用专用设备API的诊断字段，执行主机与口径已在 [规范化数值回执](validation/NUMERIC_COMPARISON_WITH_CONTEXT.json) 明确。原 Ubuntu SSH 绑定地址不可用，未更改网络配置，改在已交接的 ARM CPU 中运行同一测试。

原口型、眼部、暂停/取消、150ms过期与owner保护通过；ARM原型另检查两姿态×三状态共1536帧。原生录制每版192帧，中立首帧0个差异像素；抽查2/4/5.5/7/9/11秒，肩部连接正常、下层臂明显收敛。两版各10秒无截图读回的实时时序约 16.000→15.999 fps，完成帧P95约 19.53→18.96 ms；不作提速声明。新版原GUI20秒swap计数约 15.40 fps，稀疏状态采样不是逐帧间隔分位数。

现役 startup `31d379389c2f2ac6d2e3ec33e49bd81f6f4076e4371a78f4ae7813a62193fbdf`，库 `e8b5df8d24dee572152e8909a98721cafb94528f4e6da51da02a540c3f5a7b7b`。只换原生库和三份绑定，另376组件保持。[发布清单](release/MANIFEST.json)、[就绪](validation/READY_R3_WAIT2.json)、[主界面后测](validation/LIVE_AFTER_R3.json)、[回退说明](ROLLBACK_R3.md)。本轮使用独立R3交接和新鲜owner，正常stop/start各一次，未重放R2事务。原监听偏好false已保持；本轮未启动或调参模型、转轴、相机、DFX和开机恢复。

R2原包、R2交接/返还/签收以及 E:/AUAR_工程交付_20261102 保持原件。R3新文件均在本目录，先前R2入口文本另留于 baseline/root_R2_docs。自然程度仍由现场观看确认，本次不将R2的观感反馈套作R3通过。

设备维护已由 DEVICE_RETURN_R3.json 明确返还；本轮0在途和辅助任务。完整新版包：[avatar_animation_R3_delivery.zip](release/avatar_animation_R3_delivery.zip)。
