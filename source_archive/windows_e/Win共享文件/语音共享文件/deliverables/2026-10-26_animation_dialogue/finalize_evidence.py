"""Publish the tested scope and an explicit, small, model-free source archive."""
import hashlib,json,zipfile
from datetime import datetime,timezone
from pathlib import Path
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[1];AURA=PROJECT/'aura'
deployment=json.loads((HERE/'deployment.json').read_text(encoding='utf-8'))
live=json.loads((HERE/'live_runtime_verification.json').read_text(encoding='utf-8'))
assert deployment['status']=='COMMITTED' and live['status']=='PASS'
assert live['monitor_enabled'] is False and live['profile_mode']=='guest'
assert live['services']['8792']['source_fingerprint']==json.loads((HERE/'windows_health_final.json').read_text())['source_fingerprint']
wire=json.loads((HERE/'fps_probe/wire_transport.json').read_text(encoding='utf-8'))
assert wire['status']=='PASS' and wire['listener_closed']
for line in (HERE/'live_dialogue_animation_warm.log').read_text(encoding='utf-8').splitlines():
    try:old=json.loads(line)
    except ValueError:continue
    if isinstance(old,dict) and old.get('status')=='PASS' and 'first_ms' in old:
        (HERE/'live_dialogue_animation_warm.json').write_text(json.dumps(old,ensure_ascii=False,indent=2),encoding='utf-8');break

progress={'date':'2026-10-26','status':'AUTOMATED_SCOPE_VERIFIED_HUMAN_ACCEPTANCE_PENDING',
 'windows_voice_regression_passed':303,'windows_voice_skipped':2,'additional_subtests_passed':27,
 'arm_first_run':{'passed':326,'failed':1,'skipped':1},'arm_renderer_retry':{'passed':7,'assertions_unchanged':True,'renderer_import_preloaded':True},
 'arm_distinct_cases_resolved':327,'counts_overlap_across_platforms':True,'full_hidden_gtk_passed':True,
 'candidate_ui_committed':True,'active_runtime':json.loads((HERE/'candidate.json').read_text(encoding='utf-8'))['runtime'],
 'boot':live['boot'],'native_idle_trial_fps':deployment['trial']['fps'],'native_idle_trial_p95_ms':deployment['trial']['p95_ms'],
 'windows_stack_healthy':True,'service_revision':live['services']['8792']['service_revision'],
 'real_wired_dialogue_and_silent_material_replay':'PASS','latest_first_audio_ms':json.loads((HERE/'live_dialogue_animation.json').read_text(encoding='utf-8'))['first_ms']['audio'],
 'monitor_enabled':False,'microphone_used':False,'physical_audio_test':False,'physical_follow_test':False,
 'manual_pan_state':live['manual_pan_state'],'visual_bound':live['visual_bound'],'camera_pids':live['camera_pids'],
 'other_model_unloaded':False,'windows_render_cpu_probe':'PASS','rgb_wire_12_16_24fps_probe':'PASS',
 'windows_render_deployed':False,'physical_24fps_verified':False,'model_migration':'deferred; D-drive storage unchanged',
 'remaining':['new-combination human listening, interruption, profile choice and noise acceptance','continuous real conversation stability',
              'visual readiness and exact motion environment, mechanical calibration and following',
              'Windows-render frame ingress, audio-clock sync, cancellation and fallback; actual screen fps acceptance'],
 'recorded_at_utc':datetime.now(timezone.utc).isoformat()}
(HERE/'PROGRESS.json').write_text(json.dumps(progress,ensure_ascii=False,indent=2),encoding='utf-8')

marker='<!-- animation-dialogue-auto-20261026 -->'
note='''<!-- animation-dialogue-auto-20261026 -->
- 最新接续证据 `deliverables/2026-10-26_animation_dialogue/README.md`：板端正式UI已COMMITTED至 `/home/root/aura-animation-dialogue-20261026/d6d1617467724213b3d9fd3d11530a47`，30z独立覆盖，原入口/旧覆盖保留；加入个人记忆按钮及纯情绪等待可听回答，默认访客，监听false/无开麦保持。Windows已恢复并核对r3、8791/8792 HTTP及8795帧协议；原27B/OmniVoice16和D盘存储保持。303项Windows/27子测试；ARM首次326过1冷cv2超时1跳过，原工作线程7项按GUI预载cv2后重测全过，327不同用例解决，不能累加为334。
- 最终boot da36c36a-ef4d-4122-8ad6-cfae3931303e，相机PID54394在切换前后保持；178份未改Python一致，继承原manual_release及pan配置SHA。当前视觉未就绪、manual_pan FAULT，精确环境不匹配时拒绝MMIO，不能仅更新boot或越过保护。短时待机8.078fps/P95中位137.49ms不代表实聊长稳；本轮无实际播放/开麦/机械命令。
- 用户明确“保持其他模型运行”，没有卸载maibot或停止其进程；最后只读11434无驻留模型是环境观察，非卸载对照。真实公开WAV最新首PCM6.48秒，旧冷28秒/热12.87秒保留，不能主张稳定或真人接受。新版组合仍待真人选档、听音、插话、噪声和长稳；视觉/转轴及声纹/ASD等未全部完成。
- 用户提出Windows合成提帧，独立CPU真实素材6类预热P95约3.74–5.93ms；423x438 RGB网线12/16/24fps每类64帧CRC通过，24fps RTT P95约14.03ms。仅计算/传输初测，正式仍8fps，没有第二native sink或高帧显示上线；下一步是有界最新帧、PCM时钟/代次/取消、断网回退和单sink实际送显分级验收。实验隔离加载板端模块，不覆盖共享演示开发版的factory/FSM/player差异。见fps_probe/README.md。
<!-- /animation-dialogue-auto-20261026 -->

'''
agents=PROJECT/'AGENTS.md';old=agents.read_text(encoding='utf-8')
if marker not in old:agents.write_text(note+old,encoding='utf-8')
index=PROJECT.parent/'语言模型分析/README.md';old=index.read_text(encoding='utf-8')
entry='''<!-- animation-dialogue-auto-20261026 -->
[最新：动画与对话自动验证及正式界面接续](../语音共享文件/deliverables/2026-10-26_animation_dialogue/README.md)：新版正式UI已部署，访客/监听关闭；Windows三服务r3健康。四动作、嘴型/身体及真实网线公开WAV链路通过，短时原生待机约8.08fps。新版真人体验、视觉就绪和机械随动仍待完成。[Windows合成提帧初测](../语音共享文件/deliverables/2026-10-26_animation_dialogue/fps_probe/README.md)显示CPU合成及24fps原始RGB网线传输有余量，正式送显尚未迁移，不能称屏幕已24fps。
<!-- /animation-dialogue-auto-20261026 -->

'''
if marker not in old:index.write_text(entry+old,encoding='utf-8')
profile=HERE.parent/'2026-10-26_profile_memory/README.md';old=profile.read_text(encoding='utf-8')
old=old.replace('本轮完成了明确授权的个人记忆后端和客户端源码。Windows 8792已加载r2并通过真实公开WAV检查；板端设置页“个人记忆”按钮已形成基于实际活动版本的独立候选，并通过客户端和隐藏GTK对话框检查，**正式板端界面尚未切换**。整个玩偶项目仍未全部完成。',
 '本轮完成了明确授权的个人记忆后端和客户端源码。后续[动画与对话接续轮](../2026-10-26_animation_dialogue/README.md)已将设置页“个人记忆”入口受控合入正式板端UI，完整隐藏GTK及正式原生界面试运行通过；Windows升级到兼容r3。默认访客、监听关闭，没有代用户创建真实个人档案。以下r2检查与旧候选元数据为当轮历史，整个玩偶项目仍未全部完成。')
old=old.replace('后续板端候选正式合并后，Windows执行','板端入口已在接续轮合并；Windows执行')
old=old.replace('1. 将已测试的板端候选受控合并到当前启动版本，完成完整GUI初始化、正式界面状态与同版链路检查。候选仅改原活动版三个文件的9个小补丁并增加三个模块，其余界面/渲染/运动源保留；本轮未重启正式UI。',
 '1. 正式GUI合并、完整隐藏初始化和正式原生界面状态检查已在[接续轮](../2026-10-26_animation_dialogue/README.md)完成；本目录的旧候选和原源码包作为历史保留。')
profile.write_text(old,encoding='utf-8')

sources=['tools/streaming_controller.py','tools/motion_queue.py','tools/realtime_controller.py','tools/realtime_facials.py',
 'tools/idle_body_compositor.py','tools/board_avatar_worker.py','tools/render_performance.py',
 'common/voice_service_capabilities.py','board/runtime/audio/voice_channel.py','tests/framework/test_animation_dialogue.py']
items={('source/aura/'+name):(AURA/name) for name in sources}
for folder in ('board_evidence','board_before','shared_before','current_base','fps_probe'):
    for path in (HERE/folder).rglob('*'):
        if path.is_file() and path.suffix.lower() in ('.py','.json','.xml','.md','.log','.diff'):
            items['evidence/'+path.relative_to(HERE).as_posix()]=path
for path in HERE.iterdir():
    if path.is_file() and path.suffix.lower() in ('.py','.json','.log','.xml','.md','.png','.gif') and path.name not in ('SOURCE_MANIFEST.json','archive_verification.json'):
        items['evidence/'+path.name]=path
items['evidence/windows_voice_regression.xml']=HERE.parent/'2026-10-26_profile_memory/animation_dialogue.xml'
manifest=[]
for name,path in sorted(items.items()):
    assert path.resolve().is_relative_to(PROJECT.resolve())
    raw=path.read_bytes();assert len(raw)<3_000_000,(name,len(raw))
    manifest.append({'path':name,'source':str(path),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
(HERE/'SOURCE_MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
archive=HERE/'source_and_evidence.zip'
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as target:
    for item in manifest:target.write(items[item['path']],item['path'])
    target.write(HERE/'SOURCE_MANIFEST.json','SOURCE_MANIFEST.json')
with zipfile.ZipFile(archive) as target:
    assert target.testzip() is None
    for item in manifest:assert hashlib.sha256(target.read(item['path'])).hexdigest()==item['sha256']
result={'status':'PASS','files':len(manifest),'zip_bytes':archive.stat().st_size,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
        'models_environments_private_keys_tokens_audio_databases_included':False}
(HERE/'archive_verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
