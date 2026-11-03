"""Publish reproducible code and bounded evidence; never package private stores or weights."""
import datetime,hashlib,json,zipfile,xml.etree.ElementTree as ET
from pathlib import Path
H=Path(__file__).resolve().parent;P=H.parents[1];A=P/'aura'
def read(name):return json.loads((H/name).read_text(encoding='utf-8-sig'))
def write(name,value):(H/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
release=read('release_verification.json');deployment=read('deployment.json');hotfix=read('host_memory_hotfix.json')
voice=read('live_voice_acceptance.json');devices=read('devices_live_acceptance.json');speaker=read('speaker_live_acceptance.json')
spoken=read('spoken_devices_acceptance.json');memory=read('visual_history_acceptance.json');muted=read('muted_speech_probe.json')
assert release['status']=='PASS' and deployment['status']=='COMMITTED' and hotfix['status']=='READY'
assert voice['status']=='PASS' and memory['status']=='PASS' and devices['status']=='PASS' and speaker['status']=='PASS' and muted['status']=='PASS'
last=voice['checks'][-1]['result']['8792']['body']
link=read('final_connectivity.json') if (H/'final_connectivity.json').exists() else None
link_down=bool(link and not link.get('board_live_state_confirmed'))
reconnect=read('reconnect_status.json') if (H/'reconnect_status.json').exists() else None
reconnected=bool(not link_down and reconnect and reconnect.get('ready_for_readonly_completion'))
if reconnected:
 assert reconnect['actual_runtime']==deployment['runtime'] and reconnect['component_pins_unchanged'] and not reconnect['hash_mismatches']
 assert reconnect['windows_from_board']['dialogue']['source_fingerprint']==release['host']['source_fingerprint']
current_boot=reconnect['boot'] if reconnected else release['boot']
current_camera=reconnect['camera_service']['MainPID'] if reconnected else release['camera_pid']
current_epoch=reconnect['camera_frame']['camera_epoch'] if reconnected else devices['camera_epoch']
assert last['service_revision']=='voice-device-skills-20261028-r6' and last['source_fingerprint']==release['host']['source_fingerprint']
suites=list(ET.parse(H/'voice_first_tests.xml').getroot().iter('testsuite'))
assert all(int(s.get('failures','0'))==0 and int(s.get('errors','0'))==0 for s in suites)
passed=sum(int(s.get('tests','0'))-int(s.get('skipped','0')) for s in suites)
skipped=sum(int(s.get('skipped','0')) for s in suites)
manifest=read('windows_applied.json')
for n,row in manifest.items():
 row['final']=hashlib.sha256((A/n).read_bytes()).hexdigest()
 assert row['final']==hashlib.sha256((H/'candidate_source'/n).read_bytes()).hexdigest()
release['host_files']=manifest;release['canonical_hub_source']=read('canonical_hub_source.json');write('release_verification.json',release)
first_pcm=[r['result']['first_ms']['audio'] for r in voice['checks'] if r['name'] in ('actual_public_asr_llm_tts_receive','actual_recovery_next_turn')]
visual=next(x for x in spoken['checks'] if x['id']=='visual_question')
failures=[x['id'] for x in spoken['checks'] if x['status']!='PASS']
speaking=muted['speaking']
strict_speaking=bool(speaking['native_fps']>=15.2 and speaking['p95_ms_median']<=78.125 and speaking['p99_ms_median']<=125)
assert not strict_speaking
progress={'status':'DEPLOYED_PARTIAL_ACCEPTANCE','complete':False,'updated_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'runtime':deployment['runtime'],'board_boot':current_boot,'deployment_boot':release['boot'],'windows_revision':last['service_revision'],
 'windows_source_fingerprint':last['source_fingerprint'],'board_deployment':'COMMITTED',
 'audio_first':True,'visual_required_for_voice':False,'wake_method':'VAD_then_ASR','verified_spoken_wake':'汐蓝',
 'visual_observation_interval_s':15,'observation_retention_s':86400,'observation_limit':1000,
 'observation_scope':'same_board_boot','raw_observation_images_saved':False,
 'visual_question_actual_transport':'PASS','visual_history_actual_transport':'PASS','face_route':'existing_explicit_board_enrollment',
 'speaker_enrollment_state_machine':'PASS','speaker_actual_public_sample_then_cancel':'PASS','speaker_field_calibrated':False,
 'automatic_personal_memory_unlock':False,'tests':{'windows_passed':passed,'windows_skipped':skipped,'arm_passed':71,'arm_deselected':6,'overlap_do_not_add':True},
 'public_voice_acceptance':{'status':voice['status'],'first_pcm_ms':first_pcm,'playback':False},
 'spoke_synthetic_acceptance':{'passed':len(spoken['checks'])-len(failures),'failed':failures,'additional_history_check':memory['status']},
 'idle_display':deployment['sample'],'speaking_display':speaking,'strict_speaking_16fps_passed':strict_speaking,
 'state':{'listening':False,'microphone_open':False,'following':False,'mechanical':'FAULT','pulse_us':None,'audio_output':'IDLE_READY','volume':70,'muted':False},
 'preserved':{'camera_pid':release['camera_pid'],'camera_epoch':devices['camera_epoch'],'other_ollama_pids':[22848,556],
              'mechanical_config':True,'llm_storage':'D:/AIModels'},
 'open':['哎/欸合成输入漏唤醒；KWS候选漏检且将西兰花误触发，未上线','即时流式唤醒与真实噪声验收',
         '说话时P95/P99长帧仍超严格16fps门槛','真人听音、入镜招呼、插话、持续实聊、声纹标定',
         '声画归属/TalkNet候选未通过整合验收','并行机械精确环境绑定仍FAULT；本任务不改绑定或恢复运动'],
 'automations_created':False}
if link_down:
 progress.update(status='DEPLOYED_AWAITING_RECONNECT',live_board_status='UNAVAILABLE_LAST_VERIFIED_STATE_RETAINED',connectivity_evidence='final_connectivity.json')
 progress['state']['currently_confirmed']=False
 progress['state']['as_of']='release_verification.json (before final link loss)'
 progress['open'].insert(0,'最后检查时有线网卡断开、路由转入singbox_tun；恢复网线后重新只读核验板端')
elif reconnected:
 progress.update(live_board_status='ONLINE_SERVICE_READY',connectivity_evidence='final_connectivity.json',reconnect_evidence='reconnect_status.json',
                 current_camera={'pid':current_camera,'epoch':current_epoch},post_reboot_display_snapshot=reconnect['ui']['avatar_display'])
 progress['state'].update(currently_confirmed=True,as_of=reconnect['checked_at_utc'])
 progress['preserved']['scope']='Original deployment before the subsequent user reconnect/reboot'
write('PROGRESS.json',progress)
link_notice=('**最后连接检查：Windows 两个有线网卡已显示 Disconnected，板卡 SSH 连续握手超时，192.168.50.2 路由转入 singbox_tun。Windows 四项语音/画面服务仍健康。已保存的部署与验收记录有效，但目前不能确认板端仍在线；以下板端状态均为断线前最后一次成功核验。** [连接证据](final_connectivity.json)\n\n' if link_down else '')
if reconnected:
 link_notice=f'**用户重新连接后已复核：有线直连恢复 1Gbps；板卡重启为 boot `{current_boot}`，自动进入原已提交入口。277 项源码校验、相机/MCP01、Windows 语音与设备服务通过，待机送显快照约 {reconnect["ui"]["avatar_display"]["fps"]:.2f}fps。监听/麦克风/跟随仍关闭，机械保护保持。** [重连核验](reconnect_status.json)、[网络证据](final_connectivity.json)。此前断线记录保留在 [历史证据](connectivity_before_reconnect.json)。\n\n'

report=f'''# 语音独立与板端外设接入（2026-10-28）

本轮功能已部署到实际板端与 Windows 服务，状态为 **{progress['status']}**。语音无需人入镜；实时视觉问答、定时观察记忆、历史观察回忆、声纹登记流程以及入镜招呼均已接入。整机最终验收尚未完成，下面保留通过项、失败项及现场待验项。

{link_notice}## 最近一次核验的入口与运行状态

- 板端正式根：`{deployment['runtime']}`；当前 boot `{current_boot}`（原部署 boot `{release['boot']}`）。
- Windows 语音服务：`{last['service_revision']}`；已加载源码指纹 `{last['source_fingerprint']}`。
- 板端 277 项启动校验通过；部署验收时 245 个未改 Python 文件与基线一致。准备阶段按计划刷新了一个框架测试文件，单独逐字节核验，未绕过运行源码或机械配置校验。
- 当前相机 PID {current_camera}、epoch `{current_epoch}`。监听和跟随关闭，麦克风关闭，`IDLE_READY`；音量 70、静音 false。机械仍为 `FAULT` / 位置 null，不能靠改 boot 或放宽绑定恢复。
- ASR 8791、对话/TTS 8792、音频前端 8795、画面 8796、CPU 视觉模型 8810、设备服务 8812 已就绪。其他 Ollama 进程 22848、556 保留，未卸载其他模型。
- LLM 权重与 Ollama 数据仍在 D 盘；新增视觉/声纹/KWS 评估资源也在 D 盘。ASR/TTS 继续使用现有明确授权路径，无 LLM 数据复制到共享目录。

## 实际分工

| 位置 | 已执行职责 |
| --- | --- |
| 板卡 PS | 单一音频采集、语音会话/插话状态、播放与口型时钟、现有相机帧引用、15 秒观察调度、人脸登记确认、唯一显示 sink |
| Windows CPU | ASR、音频前端、画面合成、SFace、Qwen3-VL 视觉回答、ECAPA 声纹与设备记忆服务 |
| Windows 对话/TTS服务 | 现有 27B 对话模型、选定 OmniVoice 音色、设备摘要上下文及确定性指令路由 |

此次将外设调用与交互接到了板端。27B、VLM、ECAPA 和 TTS 推理仍在 Windows，未宣称这些模型已迁入板卡。

## 已接通的交互

1. **语音独立**：开启监听后以“汐蓝”进入会话，接话和插话不要求相机、人脸或说话者视觉绑定。名字已复用先前确认过的保守同音容错；不把“西兰花”或陌生名字改成唤醒词。30 秒无声后回到等唤醒状态。
2. **视觉补充**：稳定入镜约 0.6 秒可触发“嗯？”，约 4 秒无发言再主动邀请；30 秒冷却，普通对话忙时让路。两条实际选定音色缓存分别 1.16 / 2.08 秒，哈希及取回检查通过。真人入镜、噪声和可听打断效果仍待验。
3. **即时视觉问答**：板端按同一 request/token/boot/epoch 获取现有相机的新鲜 JPEG，Windows CPU VLM 回答并用原音色合成。画面不作为动作指令，不能用于猜人名或声画归属。
4. **观察记忆**：监听开启时每 15 秒生成一条短摘要；最多 1000 条、24 小时、按同一 boot 隔离。只存摘要及时间/帧引用；超过 20 秒标为历史。“刚才看到了什么”已修为读取历史摘要，“清除画面记忆”清除本次开机记录并阻止在途旧结果写回。
5. **人脸**：沿用已有板端明确登记与固定目标流程，不因普通入镜自动入库；SFace 主机服务健康通过。本轮未创建真人身份，也没有用 VLM 猜身份。
6. **声纹**：已接通“登记我的声纹，我叫某某”→三段不同语音→“确认保存声纹”，以及取消、重复样本拒绝、版本检查、查询和二次确认删除。只保存模型专属模板，库与人脸分离。尚无现场标定证据，不自动据此确认个人身份或解锁个人记忆。
7. **模型能力约定**：[SKILL.md](../../aura/skills/aura-devices/SKILL.md) 与[接口表](../../aura/skills/aura-devices/references/capabilities.md)已保存；运行时由 Python 适配器路由，并把设备来源/时效约束写入对话提示。模型不具有任意 Shell、HTTP 或 MMIO 权限。

## 验收证据

| 检查 | 结果与范围 | 证据 |
| --- | --- | --- |
| Windows 回归 | {passed} 通过，{skipped} 项 Linux 原生依赖跳过 | [日志](tests_final.log)、[JUnit](voice_first_tests.xml) |
| ARM 回归 | 71 通过；6 个主机 HTTP 项排除，在 Windows 单独测 | [板端结果](board_tests.json) |
| 最终 r6 公开录音链路 | 7 项通过：ASR→27B→TTS、取消、解锁、下一轮与实时音频前端；首 PCM {first_pcm[0]/1000:.3f} / {first_pcm[1]/1000:.3f} 秒 | [真实链路](live_voice_acceptance.json) |
| 合成语音板端实测 | 8 项中 6 过；“汐蓝”单呼/带问句、两条误唤醒拒绝、视觉问答、声纹查询通过；哎/欸两项失败 | [完整结果](spoken_devices_acceptance.json) |
| 实际视觉问答语音链路 | 实际 ARM 客户端→ASR→相机帧→VLM→TTS，首 PCM {visual['first_audio_ms']/1000:.3f} 秒；无实际播放 | [结果](spoken_devices_acceptance.json) |
| 周期观察与独立视觉回答 | 35 秒内两次定时提交并存摘要；共享相机保持；独立视觉回答 7.609 秒 | [设备集成](devices_live_acceptance.json) |
| 历史观察语音问答 | r6 实际合成问题，经 ASR 和 27B 读取已有历史；无当前画面请求，有过去时表述 | [历史问答](visual_history_acceptance.json) |
| 真实声纹 CPU 服务 | 3.15 秒公开录音经 VAD/ECAPA 约 0.266 秒；重复拒绝与取消通过，身份库 0→0 | [声纹结果](speaker_live_acceptance.json) |
| 原生待机显示 | {deployment['sample']['fps']:.3f}fps，P95 {deployment['sample']['p95_ms']:.2f}ms，P99 {deployment['sample']['p99_ms']:.2f}ms；部署采样门槛通过 | [部署](deployment.json) |
| 实际静音 PCM / 口型 | 口型变化、播放时钟、暂停/恢复、取消后新轮通过，取消到空闲约 0.315 秒 | [静音测试](muted_speech_probe.json) |
| 说话时显示 | {speaking['native_fps']:.3f}fps，P95 {speaking['p95_ms_median']:.2f}ms，P99 {speaking['p99_ms_median']:.2f}ms；严格 16fps 长帧门槛**未通过** | [同一静音测试](muted_speech_probe.json) |
| 最终源及状态 | 277 项校验、源版本、相机/机械/音量及服务健康通过 | [完整核验](release_verification.json)、[健康](windows_health_final.json) |

Windows/ARM 回归互有重叠，不能简单相加。合成输入、公开录音及硬件静音测试均不代替真人听音/声学延迟和长期稳定性验收。固定短答或缓存招呼的速度也不能作为自由对话的延迟成绩。

## 未通过及现场待验

- “哎”合成输入被 ASR 识别为 `i`，“欸”被识别为“喂”，正式入口拒绝，不能称全部唤醒词已验收。现阶段可靠的自动测试入口是“汐蓝”。专用流式 KWS 已作隔离评估，识别了名字却漏掉短呼唤，并把“西兰花”触发为名字，因此未上线，也未降低阈值来填通过。
- KWS 使用[官方模型与格式说明](https://k2-fsa.github.io/sherpa/onnx/kws/pretrained_models/index.html)中的小型模型；下载 SHA256 与官方 release digest 一致。原始结果在 [kws_evaluation.json](kws_evaluation.json)，路径/哈希在 [kws_model_manifest.json](kws_model_manifest.json)。这只是候选评估，当前依旧 VAD+ASR，未实现已验收的即时流式唤醒。
- 说话时仍有长帧；本次约 6.56 秒的 PCM 负载样本不能当长稳。严格门槛保持平均 ≥15.2fps、P95 ≤78.125ms、P99 ≤125ms，没有放宽。
- 需要一次现场验收：无人在镜头中的唤醒与连续接话、真实“哎/欸”发音和环境噪声、入镜“嗯？”及静默后主动邀请、真人插话、声纹三次录入/标定、人脸确认、声画归属、长时间声画一致性。
- TalkNet/声画归属仍是此前候选，未被当作正式说话人确认。机械仍属并行绑定问题，本轮保持 FAULT，不更新精确绑定、不恢复运动。

## 运行与接续

启动 Windows 使用项目 [start_voice.ps1](../../start_voice.ps1)，它会复用/启动设备 CPU 服务及现有语音、画面服务。主源码已包含 `tools/device_hub.py` / `speaker_device.py`；两个文件与已测运行代码逐字节一致，下次启动从主源码加载。当前已运行实例继续提供同样的代码逻辑。

板端进入玩偶交互页、手动开启监听后，可先用“汐蓝”验收。例句：“汐蓝，你好”“你现在看见了什么”“刚才看到了什么”“登记我的声纹，我叫小林”。声纹和人脸的最终保存均须对应确认流程；观察记忆与个人事实记忆分开。

接续必读 [CONTINUE.md](CONTINUE.md)、[PROGRESS.json](PROGRESS.json)。当前入口已经提交，不能直接重跑早期 `prepare_board.py` / `deploy_board.py`。任何下一次切换都先重读实际 boot、入口、源码及运动/监听状态，保护并行机械更新。

首轮部署因错误地比较整个 UI 状态（唯一变化为 revision）自动回退；随后改为逐项核对实际持久设置、相机、机械和音量，显示门槛保持不变，再提交成功。证据保留在 [首次回退](deployment_first_rollback.json)、[最终部署](deployment.json)。主机两次小修分别记录于 [唤醒容错](host_hotfix.json)、[历史记忆](host_memory_hotfix.json)。

源码包 [verified_source.zip](verified_source.zip) 只含本轮运行源码、测试、启动脚本及设备约定，不含权重、虚拟环境、密钥、身份库、视觉摘要库、现场录音或相机截图。观察程序不保存原图；单独人工验收截图 `native_screen.png` 包含当时的相机预览，留在本地交付目录且不加入源码包。
'''
(H/'README.md').write_text(report,encoding='utf-8')
continuation=f'''# 接续规则

先读 README.md / PROGRESS.json。正式板端 `{deployment['runtime']}`，Windows `{last['service_revision']}`。本轮已部署，整机最终验收未完成。

{link_notice}

1. 不按旧历史入口或旧 boot 执行操作。重新核对实际 systemd 入口、当前 boot、源 SHA、监听/播放/机械状态；当前相机 PID {current_camera} 仅为本次证据，后续必须动态读取。
2. 用户已授权停止跟随后部署，无需再次询问同一授权。实际停止必须走已有 UI 入口并确认无活动运动；部署仍要求监听关闭、IDLE/IDLE_READY。不要主动开启跟随、麦克风或放宽机械精确绑定。
3. 其他模型保留；LLM/Ollama 只在 D 盘，严禁复制权重、缓存分段或权重目录联接到共享树。身份数据库/原始现场录音不入源码包。
4. 本轮下一步是现场样本与短呼唤词方案、说话长帧诊断及一次集中真人验收。KWS 候选有漏检和“西兰花”误报，禁止直接启用或仅降低阈值。不能把离线文本测试当实际唤醒成功。
5. 不直接重跑本目录 prepare/deploy/restart 旧脚本：它们绑定旧入口或 r4/r5 前置条件。部署脚本保留为证据和可参考流程。回退也只处理自己新增的覆盖，不能删除其他 systemd drop-in 或覆盖并行机械更新。
6. 若声纹现场校准，保存模型指纹、同人/异人/噪声数据的评价证据，再决定阈值；未校准不自动访问个人记忆。人脸与声音不能仅凭同屏关联。

核验工具：windows_health.py / read_board_state.py / reconnect_check.py 为只读检查。verify_release.py 保留原部署时的 boot、相机 PID 与既定状态，重启后不要盲改断言填通过；reconnect_check.py 按实际入口核对原部署源码/配置并记录新 boot，不更新机械绑定。原部署证据 release_verification.json 保留。

已删除的旧等待心跳无需重建。本轮没有创建自动任务。
'''
(H/'CONTINUE.md').write_text(continuation,encoding='utf-8')

files={}
for n in manifest:files['windows/aura/'+n]=(A/n).read_bytes()
for p in (A/'skills/aura-devices').rglob('*'):
 if p.is_file():files['windows/aura/'+p.relative_to(A).as_posix()]=p.read_bytes()
for p in (H/'board_deployed_source').rglob('*.py'):files['board/aura/'+p.relative_to(H/'board_deployed_source').as_posix()]=p.read_bytes()
for p in H.glob('*.py'):files['delivery/'+p.name]=p.read_bytes()
for n in ('start_devices.ps1','make_wake_fixtures.ps1','wake_phrases.json','kws_keywords.txt'):
 files['delivery/'+n]=(H/n).read_bytes()
files['windows/start_voice.ps1']=(P/'start_voice.ps1').read_bytes()
files['windows/aura/config/model_storage.local.json']=(A/'config/model_storage.local.json').read_bytes()
source_manifest={'scope':'selected source only; not a self-contained model/runtime distribution','board_runtime':deployment['runtime'],
 'host_revision':last['service_revision'],'host_source_fingerprint':last['source_fingerprint'],
 'files':{n:hashlib.sha256(raw).hexdigest() for n,raw in sorted(files.items())}}
write('source_manifest.json',source_manifest)
with zipfile.ZipFile(H/'verified_source.zip','w',zipfile.ZIP_DEFLATED) as z:
 for n,raw in sorted(files.items()):z.writestr(n,raw)
 z.writestr('MANIFEST.json',json.dumps(source_manifest,ensure_ascii=False,indent=2))
progress['source_archive_sha256']=hashlib.sha256((H/'verified_source.zip').read_bytes()).hexdigest();write('PROGRESS.json',progress)

marker='<!-- device-skills-deployed-20261028 -->'
note=f'''{marker}
- 最新部署与接续：deliverables/2026-10-28_device_skills/README.md、CONTINUE.md、PROGRESS.json。板端正式根 `{deployment['runtime']}`；Windows `{last['service_revision']}`，下方“候选未部署”等均为历史。
- 最后连接状态：{'有线网卡Disconnected、SSH握手超时，路由转入singbox_tun；Windows服务正常。断线前核验已通过，下述板端状态是最后成功记录，收到已连接后须重新确认实时入口及boot。' if link_down else '板端与Windows已只读核验。'}
- 语音独立于视觉；汐蓝实测唤醒通过。15秒观察摘要、实时视觉问答、历史回忆、原人脸确认入口、三段声纹确认/取消以及入镜招呼已接通。220 Windows/71 ARM 回归互有重叠不能累加；真实ASR/LLM/TTS与取消恢复通过。哎/欸合成输入失败，独立KWS也漏检/误报，未启用；即时唤醒未最终验收。
- 待机约15.93fps门槛通过；说话15.85fps/P95 113.69ms/P99 168.91ms仍未过严格门槛。声纹未现场标定、无自动个人记忆解锁；真人听音/插话/入镜社交、声画归属和长稳待验，不能称整机全部完成。
- 当前boot `{current_boot}`，相机PID {current_camera}、epoch `{current_epoch}`；原部署boot/PID保留在历史证据。监听/麦克风/跟随关闭、IDLE_READY、音量70；机械FAULT/位置null保持。用户已有停止跟随后部署授权；后续须重新读实际状态并保护并行机械更新，禁止只改boot放宽绑定。
- 其他模型和D盘LLM/Ollama存储保持。外设数据库位于用户私有目录；源码包不含模型/密钥/身份库或现场影像。没有创建新心跳；旧等待心跳已删除。
<!-- /device-skills-deployed-20261028 -->

'''
agents=P/'AGENTS.md';old=agents.read_text(encoding='utf-8')
if marker not in old:agents.write_text(note+old,encoding='utf-8')
else:
 start=old.index(marker);end_marker='<!-- /device-skills-deployed-20261028 -->';end=old.index(end_marker,start)+len(end_marker)
 agents.write_text(old[:start]+note.rstrip()+old[end:],encoding='utf-8')
index=P.parent/'语言模型分析/README.md';old=index.read_text(encoding='utf-8')
if marker not in old:index.write_text(marker+'\n[语音独立与板端外设接入](../语音共享文件/deliverables/2026-10-28_device_skills/README.md)：新版已部署；实际语音/视觉问答/定时观察与历史回忆/声纹流程通过相应自动验证。短呼唤词、说话长帧、现场声纹标定与整机真人验收仍开放。\n\n'+old,encoding='utf-8')
print(json.dumps({'status':progress['status'],'windows_tests':passed,'arm_tests':71,'source_files':len(files),
 'archive_sha256':progress['source_archive_sha256'],'first_pcm_ms':first_pcm,'report':str(H/'README.md')},ensure_ascii=True))
