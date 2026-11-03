"""Archive implementation and evidence only; no audio, model weights or identities."""
import hashlib,json,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[1];WORKSPACE=PROJECT.parent
c=json.loads((HERE/'integration_candidate.json').read_text())
d=json.loads((HERE/'integration_deployment.json').read_text())
assert d['status']=='LOCAL_FRONTEND_DEPLOYED' and d['runtime']==c['runtime']
testlog=(HERE/'integration_tests_log.log').read_text();assert '313 passed' in testlog
lan=json.loads((HERE/'integration_lan_validation.json').read_text())
public=json.loads((HERE/'integration_validation.json').read_text(encoding='utf-8'))
old=HERE/'isolated_verification_summary.json'
if not old.exists():old.write_bytes((HERE/'verification_summary.json').read_bytes())
summary={'date':'2026-10-21','user_choice':'local_open_source','status':'DEPLOYED_FIELD_ACCEPTANCE_PENDING',
 'runtime':c['runtime'],'original_runtime':'/home/root/aura-speech-motion-20261021/922dab49a74f/runtime',
 'architecture':'Board capture/AEC/endpoint/ownership; PC CPU stock sherpa-onnx GTCRN+Silero v5; original PCM for ASR',
 'board_tests_passed':313,'new_transport_boundary_tests':9,'preflight_passed':c['preflight_passed'],
 'hidden_gtk_config_passed':json.loads((HERE/'integration_smoke.json').read_text())['passed'],
 'hidden_gtk_native_video_disabled':True,'native_video_enabled_in_production':True,
 'public_cases':35,'speech_cases_completed':30,'non_speech_cases':5,'non_speech_starts':public['noise_starts'],
 'original_pcm_slice_exact':all(x['pcm_original_slice_exact'] for x in public['cases']),
 'asr_transcript_equal_claimed':False,'final_protocol_paced_lan':lan,
 'monitor_enabled':d['monitor_enabled'],'camera_unchanged_during_switch':d['camera_unchanged'],
 'identity_database_unchanged_during_switch':d['identity_database_unchanged'],
 'pc_model_services_restarted':False,'independent_cpu_service_port':8795,
 'llm_weights_copied':False,'private_recordings_read':False,'new_field_recording_saved':False,
 'human_environment_verified':False,'speaker_verification_in_production':False,
 'human_barge_in_revalidated_for_this_combination':False,
 'unexpected_reboot_during_initial_isolated_tests':'Observed new boot; cause unconfirmed, previous journal unavailable; original UI recovered. Hidden retest disabled second native sink.',
 'remaining':['Real speech/noise/barge-in acceptance','ECAPA integration and cross-session threshold calibration','TV/bystander speech and active-speaker attribution','Sustained conversation/load and reboot recovery'],
 'startup':'Run start_frontend.ps1 on PC when its independent service is absent; Windows login autorun was not configured.',
 'rollback_override':d['override'],'backup':d['backup']}
passive=HERE/'integration_passive_observation.json'
if passive.exists():
 xs=json.loads(passive.read_text())['observations']
 summary['passive_observation']={'samples':len(xs),'microphone_seen':any(x['microphone_open'] for x in xs),
  'frontend_frames_seen':max(x['frontend'].get('current',{}).get('frames',0) for x in xs),
  'max_observed_frontend_roundtrip_ms':max(x['frontend'].get('current',{}).get('max_roundtrip_ms',0) for x in xs),
  'errors_seen':any(x['error'] or x['recording_error'] or x['barge_error'] for x in xs),'human_acceptance':False}
(HERE/'verification_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
text=f'''# 本地开源音频前端接入（2026-10-21）

用户已选择本地开源。GTCRN＋Silero v5 已正式接入，当前板端根 `{c['runtime']}`，电脑独立 CPU 服务为 `192.168.50.1:8795`。本版实机听音与现场噪声尚待用户验收，不能沿用此前回声/打断真人结果。

板端继续负责收音、SpeexDSP 回声消除、20ms切帧、单捕获归属和取消；成熟官方 sherpa-onnx SDK 在电脑CPU运行降噪和VAD，只返回逐帧语音判断。ASR继续使用原始音频（打断路径为既有AEC输出），不使用降噪后音频替换识别输入。保留原700ms静音端点与180/240ms起点，前导改500ms补算法缓冲；前导计入既有20秒总预算。未训练、重写任何降噪/VAD/声纹网络。

每个捕获实例独立UUID、严格序号和样本进度，一次仅一包；电脑预热两条独立流，忙时拒绝，队列不积压。网络超时、错归属、取消后的回包不能变成语音事件，也不会回退为纯能量打断。保留取消前ASR核验、完整PCM提交、ACK交接、记忆、首句优化、922dab渲染/动作/pan/状态缓存和阶段性能日志。

## 验证与边界

- 最终板端313项回归、预检、隐藏GTK配置检查通过。隐藏检查关闭第二个native显示通道和麦克风；正式服务仍启用原native显示。
- 35段公开/合成输入中，30段语音均收尾，5段非人声0次起点；ASR输入是原音频精确切片。裁切与强噪声仍有4项公开转写差异，不能说识别完全无损或达到现场准确率。
- 最终协议公开PCM实际板端→PC→板端，180/240ms两种起点共622帧，P95约4.38/4.29ms，最大13.83ms，0帧超过20ms；此值不包括算法起点、说完判定、ASR、LLM和TTS的完整等待。
- 独立300秒回退守护下切换并提交，监听保持 `{d['monitor_enabled']}`，最终 `{d['phase']}/{d['audio_output_state']}`。切换期间相机PID/epoch、身份库指纹保持，未重启8792模型服务；本版尚无现场录音/听音验收。
- 初次隔离隐藏UI/传输测试期间观察到板卡重启，原因未确认、上次日志未持久化；不归因于某组件。正式922dab自动恢复。后续隐藏检查关闭重复原生显示，单独传输及正式切换通过。诊断见 integration_reboot_diagnostic.json。
- VAD/降噪主要防非人声误触发，不拒绝所有电视或旁人人声。既有SpeechBrain ECAPA仍只通过公开素材隔离复测，未接入正式聊天、未读取个人声纹库、未改阈值。下一阶段才做说话者验证、短句策略及多人的真实标定；视觉正脸不是声画归属证明。

## 启停与回退

电脑运行 `start_frontend.ps1` 可启动经过模型/源码指纹检查的独立服务，隐藏窗口并脱离终端；模型在 `D:/AIModels/audio-frontend-eval-20261021`，未进入共享目录。没有配置Windows登录自动启动；电脑重启后须重启此独立服务，服务不可用时音频捕获报错而不会误打断。

本次两层覆盖分别为 `zzzzzzzz-aura-audio-frontend-20261021.conf` 和 `zzzzzzzzz-aura-audio-frontend-budget-20261021.conf`，旧覆盖全部保留。仅撤销最终budget层会回到初次前端；完整回退应在自然空闲、保存当前监听选择后停止UI，核对并撤销这两份本次覆盖、daemon-reload、启动原922dab，再核对音频/监听状态。不得删除旧候选、模型或身份库。备份位置 `{d['backup']}`，原922dab配置在 initial_integration/integration_board_baseline.json。

## 证据

verification_summary.json、integration_candidate.json、integration_tests_log.log、integration_preflight_log.log、integration_smoke.json、integration_validation.json、integration_lan_validation.json、integration_deployment.json、pc_service/manifest.json。此前隔离结论保留在 isolated_verification_summary.json；finalize.py为旧阶段脚本，不能用其覆盖当前摘要。
'''
if 'passive_observation' in summary:
 p=summary['passive_observation']
 note=f"补充被动观察：{p['samples']}次采样看到实际开麦及前端{p['frontend_frames_seen']}帧，未出现UI/录音/打断错误。单帧往返最大约{p['max_observed_frontend_roundtrip_ms']}ms，高于公开节拍测试，不能把公开样本的0超20ms当作真实运行保证。也不能据此认定现场噪声、延迟或打断体验验收通过。\n\n"
 text=text.replace('## 启停与回退',note+'## 启停与回退',1)
(HERE/'INTEGRATION.md').write_text(text,encoding='utf-8')
readme=HERE/'README.md';s=readme.read_text(encoding='utf-8')
marker='<!-- local-open-source-integrated-20261021 -->'
block=marker+'\n用户已选择本地开源并完成首阶段接入，当前结果、启动与回退见 [INTEGRATION.md](INTEGRATION.md)。313回归通过，监听保留，现场噪声/新版打断仍待实测；声纹尚未进入正式聊天。以下为之前的隔离评估历史。\n\n'
if marker not in s:readme.write_text(block+s,encoding='utf-8')
archive={}
for n in json.loads((HERE/'initial_integration/integration_candidate.json').read_text())['files']:
 p=HERE/'integration_sources'/n;archive[n]=p
for n in c['files']:archive[n]=HERE/'integration_sources'/n
with zipfile.ZipFile(HERE/'integrated_sources.zip','w',compression=zipfile.ZIP_DEFLATED) as z:
 for n,p in archive.items():z.write(p,n)
 for n in ('INTEGRATION.md','start_frontend.py','start_frontend.ps1','pc_service/manifest.json'):
  z.write(HERE/n,n)
(HERE/'integrated_sources_manifest.json').write_text(json.dumps({n:hashlib.sha256(p.read_bytes()).hexdigest() for n,p in archive.items()},indent=2)+'\n',encoding='utf-8')
ag=PROJECT/'AGENTS.md';s=ag.read_text(encoding='utf-8')
tag='<!-- local-open-source-production-20261021 -->'
block=tag+f'\n- 用户明确选择本地开源；GTCRN+Silero v5 经官方sherpa-onnx SDK已接入，最新正式UI `{c["runtime"]}`（基于922dab，保留渲染/动作/pan/缓存/perf和回声核验），PC独立CPU8795、模型D盘，无8792模型服务重载。313回归/预检/隐藏配置检查及公开PCM622帧LAN通过，P95约4.4/4.3ms、0超20ms，非整轮延迟。35公开/生成输入30语音收尾/5非人声0起点，原PCM切片精确但4转写差异。500ms前导已计入20秒上限；网络失效/错序/取消不作语音或能量回退。监听true/IDLE_READY，相机及身份库在切换期间保持。新版现场噪声、听音/打断/长稳未验收；ECAPA尚未正式接聊天或读取个人库，电视/旁人不能称过滤通过。初次隔离时板端曾重启原因未明，后续隐藏检查禁第二native sink并通过，不能声称全程无重启。Windows未设自启动，独立服务缺失运行start_frontend.ps1；资料/回退见deliverables/2026-10-21_environment_frontend/INTEGRATION.md与当前verification_summary.json，下方“未选择/未部署/922dab最新”为历史。\n\n'
if tag not in s:ag.write_text(block+s,encoding='utf-8')
for p in (WORKSPACE/'语言模型分析/README.md',WORKSPACE/'语言模型分析/环境干扰与声纹_成熟方案调研_20261021.md'):
 s=p.read_text(encoding='utf-8');tag='<!-- local-open-source-selected-20261021 -->'
 if tag not in s:
  pos=s.find('\n')+1
  block='\n'+tag+'\n[本地开源首阶段已接入](../语音共享文件/deliverables/2026-10-21_environment_frontend/INTEGRATION.md)：用户已选择本地开源，GTCRN+Silero v5在电脑CPU运行，313回归通过、监听保留。正式入口更新，声纹/电视及旁人人声仍待后续接入和实测；下方隔离与路线未选状态为历史。\n\n'
  p.write_text(s[:pos]+block+s[pos:],encoding='utf-8')
print(json.dumps({'status':summary['status'],'runtime':c['runtime'],'archive':'integrated_sources.zip'}))
