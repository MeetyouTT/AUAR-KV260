from common import *
import zipfile
def main():
 m=load(HERE/'release/MANIFEST.json');q=load(HERE/'release/QUALITY_GATE.json');ready=load(HERE/'validation/READY_R3_WAIT2.json');live=load(HERE/'validation/LIVE_AFTER_R3.json');n=q['numerical_compare']
 assert ready['status']=='READY_WITH_NEW_NATIVE_LIBRARY' and ready['new_native_library_sha256']==m['components']['tools/libaura_yuki.so']['after_sha256']
 status=dict(schema='aura-avatar-natural-lower-arm-R3-status-1',updated_host_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),release='R3_natural_lower_arm',user_feedback_R2=load(HERE/'USER_FEEDBACK.json'),implemented=True,files_published=True,loaded_into_original_GUI=True,software_readiness_verified=True,render_capture_reviewed=True,R3_human_screen_acceptance=False,current_startup_sha256=m['startup_after'],native_library_sha256=ready['new_native_library_sha256'],boot_id=ready['boot_id'],gui_owner=ready['gui_owner'],gtk_owner=ready['gtk_owner'],camera_owner=ready['camera_owner'],component_count=380,other_components_preserved=376,numerical_comparison=n,actual_renderer_timing=q['same_scene_actual_render'],loaded_GUI_swap_fps=live['native_swap_fps'],listening_enabled=False,microphone_open=False,following=False,model_restarts=0,model_voice_identity_memory_configuration_changed=False,camera_restarts=0,axis_commands=0,DFX_boot_changes=0,source_directory='candidate/native',preview_GIF='previews/before_after.gif',preview_video='previews/before_after_16fps.mp4',rollback_to='R2 exact four-component backup plus startup, from this R3 stage',device_maintenance_returned=False)
 save(HERE/'STATUS_R3.json',status)
 text=f'''# 下层手臂自然摆动 R3

用户明确反馈 R2“下层手臂幅度太大，优化幅度确保摆动自然”。本次已将画面下方/后侧垂臂收小、放慢并增加阻尼，R3 已由原 GUI 实际加载，380 项来源匹配、角色可见、故障 0。R2 的该项观感未获接受；R3 的现场人类观感尚待反馈。

[前后 GIF](previews/before_after.gif) 左 R2、右 R3；[16fps MP4](previews/before_after_16fps.mp4) 保留完整时间轴；[抽帧总览](previews/contact_sheet.png)。均为同一 KV260、同模型、同纹理、同种子、同尺寸和时间轴的原生离屏录制，不含现场相机或音频，GIF 为8fps便览。

调整限定在 `aura_arm_left`，对应 A 姿态下层/后侧的 `腕LA_le`（原图0059/0052），也作用于 B 姿态同侧分支。目标波幅由6.5+1.3改为2.6+0.45，主周期4.8→6.8秒，阻尼0.58→0.85，角速度上限16→6度/秒。R2 的肩部支点补偿、胸前手臂、头部/躯干、头发与附属物理效果保留。实际用户语义、音色、身份、记忆、相机和转轴配置均保留。

60000个逻辑author tick的同编译条件对照中，下层臂关节角范围由 {n['old_lower_min']:.2f}～{n['old_lower_max']:.2f} 度收至 {n['new_lower_min']:.2f}～{n['new_lower_max']:.2f} 度，约为上一版的 {n['range_ratio']*100:.1f}%；峰值角速度 {n['old_peak_speed_deg_s']:.2f}→{n['new_peak_speed_deg_s']:.2f} 度/秒。其余5通道共300000次数值逐项相同。这里是局部关节角，不是实体转轴角或整条手臂的屏幕总位移。

比较程序实际运行于 KV260 CPU，不打开显示、GPU或音频API；60000个逻辑tick不等于1000秒整机运行。原始程序输出中 `device_or_GPU_used=false` 是未调用专用设备API的诊断字段，执行主机与口径已在 [规范化数值回执](validation/NUMERIC_COMPARISON_WITH_CONTEXT.json) 明确。原 Ubuntu SSH 绑定地址不可用，未更改网络配置，改在已交接的 ARM CPU 中运行同一测试。

原口型、眼部、暂停/取消、150ms过期与owner保护通过；ARM原型另检查两姿态×三状态共1536帧。原生录制每版192帧，中立首帧0个差异像素；抽查2/4/5.5/7/9/11秒，肩部连接正常、下层臂明显收敛。两版各10秒无截图读回的实时时序约 {q['same_scene_actual_render']['R2_fps']:.3f}→{q['same_scene_actual_render']['R3_fps']:.3f} fps，完成帧P95约 {q['same_scene_actual_render']['R2_P95_complete_ms']:.2f}→{q['same_scene_actual_render']['R3_P95_complete_ms']:.2f} ms；不作提速声明。新版原GUI20秒swap计数约 {live['native_swap_fps']:.2f} fps，稀疏状态采样不是逐帧间隔分位数。

现役 startup `{m['startup_after']}`，库 `{status['native_library_sha256']}`。只换原生库和三份绑定，另376组件保持。[发布清单](release/MANIFEST.json)、[就绪](validation/READY_R3_WAIT2.json)、[主界面后测](validation/LIVE_AFTER_R3.json)、[回退说明](ROLLBACK_R3.md)。本轮使用独立R3交接和新鲜owner，正常stop/start各一次，未重放R2事务。原监听偏好false已保持；本轮未启动或调参模型、转轴、相机、DFX和开机恢复。

R2原包、R2交接/返还/签收以及 E:/AUAR_工程交付_20261102 保持原件。R3新文件均在本目录，先前R2入口文本另留于 baseline/root_R2_docs。自然程度仍由现场观看确认，本次不将R2的观感反馈套作R3通过。
'''
 (HERE/'README_R3.md').write_text(text,encoding='utf8')
 rollback='''# R3回退

本轮原字节位于 board_results/backup：tools/libaura_yuki.so、config/yuki_pair.formal.json、tools/formal_yuki.py、config/board_avatar_gtk.json 和 startup.json。对应前版为 R2/startup3faab0eb…，不是更早的原始角色包。

当前维护者先取得新的明确设备交接，现读boot、startup、完整380来源、GUI/GTK及相机寿命、播放/录音/跟随与实际监听偏好。实际空闲后沿原保护流程正常停止GUI（本次唯一临时KillMode=process/SendSIGKILL=no/TimeoutStopSec=infinity），核实进程寿命结束并恢复原unit属性。确认停稳、相机owner未变且源仍精确为R3后，以CAS成套恢复上述4组件及startup原字节，重核380项，再核对原8797健康并构造新的正常GUI启动事务，恢复实际接手偏好。

板端 publish_r3.py --rollback 包含停稳条件及逐文件CAS核对，可由取得新授权的维护者审阅后使用；R3生命周期的已封存one-shot、旧PID与旧handoff不能直接重放。后续若有其它业务发布，先合并其增量，避免旧startup覆盖新内容。R2更早的回退材料仍在原R2交付包中。此说明不自动执行设备动作。
'''
 (HERE/'ROLLBACK_R3.md').write_text(rollback,encoding='utf8')
 historical=HERE/'baseline/root_R2_docs';historical.mkdir(parents=True,exist_ok=True)
 for name in ('README.md','STATUS.json','ROLLBACK.md','SHA256SUMS.txt'):
  p=historical/name
  if not p.exists():shutil.copyfile(BASE/name,p)
 save(BASE/'STATUS.json',dict(status,detail_directory='revision3_natural_lower_arm',current_status_file='revision3_natural_lower_arm/STATUS_R3.json',previous_R2_historical_snapshot='revision3_natural_lower_arm/baseline/root_R2_docs/STATUS.json'))
 (BASE/'README.md').write_text('''# 玩偶动画当前版本：R3

用户反馈R2下层手臂幅度过大后，已加载R3收敛版：摆幅收至约四成、摆速放慢、阻尼增加；胸前手臂、头发、身体与肩部补偿保留。

当前详细状态、前后预览、验证及回退见 [R3说明](revision3_natural_lower_arm/README_R3.md)、[R3状态](revision3_natural_lower_arm/STATUS_R3.json) 和 [16fps视频](revision3_natural_lower_arm/previews/before_after_16fps.mp4)。R3现场人类观感仍待反馈；R2的下层臂观感未获接受。

原R2版本包和全部交接回执保持在原位置；R2入口原文快照在 revision3_natural_lower_arm/baseline/root_R2_docs，原相对引用应按本任务根目录解析。E:/AUAR_工程交付_20261102 原交付基线保留。
''',encoding='utf8')
 (BASE/'ROLLBACK.md').write_text('# 当前R3回退\n\n见 [R3成套回退说明](revision3_natural_lower_arm/ROLLBACK_R3.md)。原R2回退原文在 revision3_natural_lower_arm/baseline/root_R2_docs/ROLLBACK.md；原交接和包不变。\n',encoding='utf8')
 print(json.dumps(dict(status='R3_LOADED_SOFTWARE_VERIFIED_PREVIEW_DELIVERED',startup=m['startup_after'],native=status['native_library_sha256'],GUI_fps=live['native_swap_fps'],lower_arm_range_ratio=n['range_ratio'])))
if __name__=='__main__':main()
