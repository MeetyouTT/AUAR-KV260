from common import *
import zipfile
def main():
    m=load(HERE/'release/MANIFEST.json');q=load(HERE/'release/QUALITY_GATE.json')
    ready=load(HERE/'validation/READY_R4_WAIT2.json');live=load(HERE/'validation/LIVE_AFTER_R4.json')
    final=load(HERE/'validation/FINAL_DEVICE_READY_R4.json');returned=load(HERE/'DEVICE_RETURN_R4.json')
    assert ready['status']=='READY_WITH_NEW_NATIVE_LIBRARY' and final['startup_sha256']==m['startup_after']
    assert returned['permission_active_for_animation'] is False
    status=dict(schema='aura-avatar-dialogue-motion-R4-status-1',updated_host_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
      release='R4_dialogue_state_motion',implemented=True,files_published=True,loaded_into_original_GUI=True,
      software_readiness_verified=True,render_capture_reviewed=True,human_screen_acceptance=False,
      live_human_dialogue_test_performed=False,current_startup_sha256=m['startup_after'],
      native_library_sha256=final['native_library_sha256'],adapter_sha256=m['components']['tools/native_yuki.py']['after_sha256'],
      boot_id=final['boot_id'],gui_owner=final['gui_owner'],gtk_owner=final['gtk_owner'],camera_owner=final['camera_owner'],
      component_count=380,other_components_preserved=375,quality=q,loaded_GUI_swap_fps=live['native_swap_fps'],
      actual_listening_enabled=final['listening_preference']['enabled'],microphone_open=False,following=False,
      device_maintenance_returned=True,device_return_receipt='DEVICE_RETURN_R4.json',
      return_acknowledged=(HERE/'DEVICE_RETURN_ACK_R4.json').exists(),source_directory='candidate',
      preview_GIF='previews/preview_compact.gif',preview_video='previews/dialogue_motion_16fps.mp4',
      full_source_map='release/startup.after.json',last_fresh_receipt='validation/FINAL_DEVICE_READY_R4.json',
      board_stage=load(HERE/'STAGE_INTENT.json')['stage'],parallel_voice_overlap_files_changed=[])
    save(HERE/'STATUS_R4.json',status)
    text=f'''# 对话状态动作驱动 R4

R4 已加载到原 GUI，角色 READY、可见、运行故障为零。动作由现有对话状态、情绪及真实播声提示驱动。下层手臂保留 R3 的局部角度 ±4°、速度 6°/秒硬限；本轮测试峰值约 {q['lower_arm_absmax_deg']:.2f}°、{q['lower_arm_peak_speed_deg_s']:.2f}°/秒。人类实屏自然程度和真人整轮对话尚未验收。

[完整 28 秒对照视频](previews/dialogue_motion_16fps.mp4) 保留16fps；[简短 GIF](previews/preview_compact.gif)、[全部状态抽帧](previews/contact_sheet.png)、[反应动作序列](previews/reaction_sequence.png)。这些均为 KV260 原生 GLES 离屏渲染，使用合成音量包络，不含现场相机或音频播放。

待机保留轻微呼吸和重心变化；唤醒小抬头；聆听与思考收敛身体和手臂并保持轻微姿态偏移；普通/积极/低落回答采用三套强度及姿态。点头、摇头、惊讶/唤醒、困惑各有一次性曲线，动作令牌避免重复启动。回答结束、暂停和取消时平滑收势，原口型在取消或失去音频 lease 时及时归零。

新增 head_UD、body_UD 与原6通道合成后统一限幅、限速，固定60Hz更新。相位、关节速度和原头发/附属部件物理状态跨状态保留；原肩部支点与模型/纹理不变。14种派生动画姿态由现有15个业务状态及播放事实映射，摄像头/网络状态仍保留原业务含义。眼部沿用现有思考闭眼、真实回答睁眼规则。

原64字节音频控制与96字节统计 ABI 保留；新增88字节原子对话控制与80字节动作统计。原生完成令牌用于反应收尾，隐藏头像时保留原0.8秒业务兜底。现有语义白名单、每轮最多两个不同动作、至少四秒间隔及PCM提示时钟保留，不新增模型调用，不改变文字推断或语音策略。

验证：7项适配测试通过；真实模型/播放/物理核心覆盖两姿态×14状态、7603帧及四反应；原口型、眼部、暂停、过期、owner/sequence保护通过。原生对照每版448帧，B姿态另96帧；中立首帧0个差异像素。截帧审阅与数值连续性分开记录，抽帧不冒作全帧人类观感通过。

相同场景、每版10秒、计时循环不读取截图的离屏性能：R3 {q['performance']['R3_fps']:.3f}fps，R4 {q['performance']['R4_fps']:.3f}fps；完成帧P95 {q['performance']['R3_p95_complete_ms']:.2f}→{q['performance']['R4_p95_complete_ms']:.2f}ms，不作提速声明。原GUI20秒swap计数约 {live['native_swap_fps']:.2f}fps；稀疏采样并非所有帧间隔分位数。

只换原生库、native_yuki.py和三份既有绑定，另375组件保持。formal_yuki.py仅两项校验常量变化，AST确认业务语义一致；未触及并行声纹的board_speaker_business.py、board_dialogue.py、board_business.py。原模型、音色、身份、记忆、相机owner、实体转轴、DFX与开机配置保留。GUI正常停启各一次；首次25秒只读检查尚在启动中，第二次检查就绪，未重发启动。

启动SHA `{m['startup_after']}`，原生库SHA `{final['native_library_sha256']}`。完整380来源见 [startup.after.json](release/startup.after.json)，[质量门](release/QUALITY_GATE.json)、[最后就绪](validation/FINAL_DEVICE_READY_R4.json)、[返还](DEVICE_RETURN_R4.json)、[回退说明](ROLLBACK_R4.md)。返还后本窗口停止设备访问；后续声纹维护可从此基线合并并保留动画。

R2/R3原包及交接回执、E:/AUAR_工程交付_20261102 封存工程均保留。当前交付包为 release/avatar_animation_R4_delivery.zip。
'''
    (HERE/'README_R4.md').write_text(text,encoding='utf8')
    rollback='''# R4成套回退

本轮精确前版是 R3/startup31d379389…。原字节保存在 board_results/backup：tools/libaura_yuki.so、tools/native_yuki.py、config/yuki_pair.formal.json、tools/formal_yuki.py、config/board_avatar_gtk.json，以及 startup.json。

后续维护者取得新的明确交接后，先核验实际boot、startup、完整组件、GUI/GTK及相机进程寿命和实际偏好。空闲时沿正常GUI停稳与属性恢复流程，以逐文件CAS成套恢复五组件和startup，再重核来源、正常启动和就绪。R4已封存的stop/start意图、旧PID与handoff不得重放。

若声纹等后续版本已经发布，应先合并其组件映射与改动，避免旧startup覆盖新业务。publish_r4.py --rollback只适用于其严格来源条件；本说明不自动执行回退。R3更早材料仍保留于原R3目录。
'''
    (HERE/'ROLLBACK_R4.md').write_text(rollback,encoding='utf8')
    previous=HERE/'baseline/root_R3_docs';previous.mkdir(parents=True,exist_ok=True)
    for name in ('README.md','STATUS.json','ROLLBACK.md','SHA256SUMS.txt'):
        if not (previous/name).exists():shutil.copyfile(BASE/name,previous/name)
    save(BASE/'STATUS.json',dict(status,detail_directory=HERE.name,current_status_file=HERE.name+'/STATUS_R4.json'))
    (BASE/'README.md').write_text('''# 玩偶动画当前版本：R4

已接通对话状态动作、点头/摇头/困惑反应与物理跟随，下层手臂沿用R3限幅。R4已加载原GUI并通过软件、渲染与短时性能检查；真人实屏观感待反馈。

[R4说明](revision4_dialogue_motion/README_R4.md)、[R4状态](revision4_dialogue_motion/STATUS_R4.json)、[28秒对照视频](revision4_dialogue_motion/previews/dialogue_motion_16fps.mp4)、[回退](revision4_dialogue_motion/ROLLBACK_R4.md)。R2/R3原件保留，原R3入口快照在 revision4_dialogue_motion/baseline/root_R3_docs，原相对引用按动画任务根目录解析。
''',encoding='utf8')
    (BASE/'ROLLBACK.md').write_text('# 当前R4回退\n\n见 [R4成套回退说明](revision4_dialogue_motion/ROLLBACK_R4.md)。R3原说明仍在原R3目录。\n',encoding='utf8')
    chosen=[]
    for p in HERE.rglob('*'):
        if not p.is_file() or '__pycache__' in p.parts:continue
        rel=p.relative_to(HERE)
        if rel.parts[0]=='board_results' and not (rel.parts[1]=='backup' or (rel.parts[1]=='build' and p.suffix in ('.json','.log','.so'))):continue
        if p.name in ('avatar_animation_R4_delivery.zip','SHA256SUMS.txt'):continue
        chosen.append(p)
    package=HERE/'release/avatar_animation_R4_delivery.zip'
    with zipfile.ZipFile(package,'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(chosen):z.write(p,p.relative_to(HERE).as_posix())
    (HERE/'SHA256SUMS.txt').write_text(''.join(sha(p)+'  '+p.relative_to(HERE).as_posix()+'\n' for p in sorted(chosen+[package])),encoding='utf8')
    roots=[BASE/n for n in ('README.md','STATUS.json','ROLLBACK.md')]
    roots += [BASE/'release/avatar_animation_R2_delivery.zip',BASE/'revision3_natural_lower_arm/release/avatar_animation_R3_delivery.zip',package,HERE/'SHA256SUMS.txt']
    (BASE/'SHA256SUMS.txt').write_text(''.join(sha(p)+'  '+p.relative_to(BASE).as_posix()+'\n' for p in roots),encoding='utf8')
    print(json.dumps(dict(status='R4_LOADED_VERIFIED_ARCHIVED_DEVICE_RETURNED',files=len(chosen),package_bytes=package.stat().st_size,
      package_sha256=sha(package),GUI_fps=live['native_swap_fps'],return_acknowledged=status['return_acknowledged'])))
if __name__=='__main__':main()
