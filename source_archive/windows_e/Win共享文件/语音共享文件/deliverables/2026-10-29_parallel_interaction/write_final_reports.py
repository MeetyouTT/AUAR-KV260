"""Publish evidence-backed reports; no service or private-data operations."""
import datetime,json,re
from pathlib import Path
H=Path(__file__).resolve().parent;P=H.parents[1];W=P.parent
def read(name):return json.loads((H/name).read_text(encoding='utf-8-sig'))
def save(name,value):(H/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
v=read('verification.json');gpu=read('public_gpu_final_adaptive.json');arm=read('arm_transport_verification.json')
assert v['status']=='PASS' and gpu['status']=='PASS' and arm['status']=='PASS'
assert read('approval_pending.json')['status']=='AWAITING_EXPLICIT_APPROVAL'
rev=v['voice_revision'];fp=v['voice_fingerprint'];runtime=v['board']['actual_runtime']
ready=read('final_ready_fixed.json');assert ready['status']=='READY'

calibration=dict(status='MEASURED_LIMITED_PUBLIC_INPUTS',checked_utc=v['checked_utc'],
 gpu_uuid='GPU-fd752a2e-1923-22d0-63af-4e3d8e6f17b8',total_mib=16311,
 model='aura-qwen3.8-27b-abliterated:iq4_xs',num_ctx=2048,tts_steps=16,
 ollama_version='0.40.13',project_fit_target_mib=4096,
 original_short_observed_min_free_mib=210,layout_trial_observed_min_free_mib=1932,
 final_observed_min_free_mib=gpu['observed_min_free_mib'],
 original_llm_gpu_bytes=13874694716,layout_llm_gpu_bytes=11579215051,
 final_first_pcm_ms={c['label']:c['first_pcm_ms'] for c in gpu['checks']},
 all_final_tts_cache_hits_zero=all(c['tts_cache_hits']==0 for c in gpu['checks']),
 actual_arm_first_pcm_ms=arm['first_pcm_ms'],
 warmup_reserved_peak_bytes=4972347392,
 thresholds=dict(reserve_mib=768,tts_extra_mib=384,tts_cold_extra_mib=5120,llm_extra_mib=512,llm_cold_extra_mib=12032),
 max_wait_seconds=5,other_models_preserved=True,
 quality_settings_preserved=True,automatic_unload_enabled=False,
 limitations=['Not identical-content paired latency A/B','Device samples do not guarantee true peak',
 'External programs can allocate after sampling','Project admission is not physical GPU isolation',
 'Single cold-start readiness observation, original 300-second deadline retained'],
 evidence=['public_gpu_baseline.json','public_gpu_layout4g.json','public_gpu_final_adaptive.json',
 'final_ready_fixed.json','arm_transport_verification.json','verification.json'])
save('gpu_calibration.json',calibration)

progress=dict(status='DEPLOYED_AUTOMATED_CHECKS_PASSED_IDENTITY_NETWORK_APPROVAL_PENDING',complete=False,
 checked_utc=v['checked_utc'],implementation_deployed=True,available_non_biometric_automated_checks_passed=True,
 full_project_complete=False,agents_finished=['speaker_visual_collaboration','windows_gpu_runtime','conversation_research','anonymous_identity_binding'],
 voice_revision=rev,fingerprint=fp,source_files_verified=46,board_runtime=runtime,board_component_pins=286,
 combined_tests_passed=637,actual_public_uncached_voice_tests_passed=3,actual_arm_public_only_transport='PASS',
 actual_face_metadata_network_acceptance='AWAITING_EXPLICIT_APPROVAL',automatic_review_rejected_before_execution=True,
 approval_details='approval_pending.json',identity_human_acceptance='PENDING',speaker_calibrated=False,
 automatic_profile_access=False,gpu_mode='adaptive',gpu_enforcing=True,gpu_observed_min_free_mib=gpu['observed_min_free_mib'],
 other_models_preserved=True,unrelated_service_pids_preserved=True,model_storage_unchanged=True,
 llm_storage='D:/AIModels',strict_original_data_equality=True,preserved_conversations=153,preserved_turns=311,
 microphone_enabled_by_agent=False,audible_playback_by_agent=False,motion_command_sent=False,
 mechanical_state='ORIGINAL_FAULT_NULL_PROTECTION_PRESERVED',voice_independent_of_visual=True,
 camera_restarted=False,new_automations_created=False,
 automatic_readback_repin_after_board_reboot='NOT_IMPLEMENTED_FAIL_CLOSED',human_audio_acceptance='PENDING',
 strict_speaking_16fps='NOT_PASSED_IN_PRIOR_MEASUREMENT',verification_report='verification.json')
save('PROGRESS.json',progress)

readme=f'''# 渐进身份记录、持续对话归属与 Windows 显存协调

本轮代码已经集成并部署：Windows `{rev}`，板端身份桥 286 项组件校验通过。637 项合并回归、三组真实非缓存语音、实际 ARM 静音语音通道及原始数据库严格比较通过。**真实人脸摘要的跨设备验收被自动审批拦截，等待用户明确授权；真人登记、识别精度和整机验收尚未完成。**

目录名沿用任务开始日期。最终核对时间见 [verification.json](verification.json) 的 UTC 时间，客户端本地日期可能不同。

## 对用户方案的结论

先用 a1、a2 记录陌生声音，再在本人明确登记时关联姓名、人脸和声纹，逻辑合理。它能保留不入镜照常对话的体验，也避免每遇到访客就询问姓名。本轮已补齐以下行为：

| 环节 | 实际规则 |
| --- | --- |
| 临时声音 | aN 是显示代号，内部使用不可复用 UUID；默认 24 小时、最多 32 个活动簇，不保存原始 PCM。首次锚点固定，避免不确定匹配逐渐混入别人的声音。 |
| 记住本人 | 明确“记住我，我叫小明”启动统一登记；只说“记住我”会先问称呼。普通聊天提到姓名不会绑定，同名也不会合并。 |
| 关联采集 | 复用原人脸登记/确认流程，再进入三段声纹采集与最终“确认保存身份关联”；已有人脸须当前明确确认才能复用。 |
| 真实保存 | 人脸、声纹两方原始保存回执齐全且校验通过，私有关联索引才成为 ACTIVE。单方完成、掉线、取消均如实保留未完成状态。 |
| 后续认人 | 新鲜的已知人脸或合格声纹证据可提供关联身份；两者冲突则标记冲突。短“嗯/欸”可正常对话，声音不足时身份保持未知。 |
| 未标定声纹 | 当前仍 speaker_calibrated=false。三次独立采集及有效模板可形成明确标注的姓名候选，不能称已确认身份。 |
| 对话时间轴 | 普通对话轮次与归属证据分开记录，迟到分析只能回填原轮次。新一轮开始不误取消上一轮已提交的分析；撤销、删除及过期阻止迟到回写。 |
| 记忆权限 | 识别姓名不自动解锁个人长期记忆，也不将历史匿名聊天自动改归本人。 |

单人入镜仍不能证明声音来自这个人，画外人、电视和重放需现场负样本检验。本轮没有新增主动说话者检测或活体防伪模型。视觉缺席、证据过期和读库失败都允许普通语音继续。

实现复用现有 ECAPA CPU 编码器和一个分析 worker，没有为每轮另载模型。生产私有库与备份保留 AppData；共享目录只保存源码、配置、哈希和报告。匿名清理是逻辑过期删除，不承诺磁盘取证级擦除；保留代号墓碑防止复用。

## 已部署的版本

- Windows 源码指纹 `{fp}`，46 份最终源码/配置按 [final_manifest.json](final_manifest.json) 核对。清单的 STAGED 是冻结时历史；安装状态见 [final_installation.json](final_installation.json)。
- 板端实际根 `{runtime}`，配置在同级 startup/config.json。原 279 项仅更新两个语音薄客户端，新增 7 项，共 286 项；[部署事务](board_deployment.json) 为 COMMITTED。
- 最后核对 UI PID {v['board']['ui']['MainPID']}、相机 PID {v['board']['camera']['MainPID']}，boot/相机 epoch 未变。这些仅是证据时点，不能作为以后停止进程的依据。
- 画面服务 revision `763d0b05a67a79ff6f8a6d9d5e2a67cc9cc060181499cef7a416bccdf7315bac` 保持，上一轮音频非阻塞供给与四套身体素材修复保留。
- 并行启动优化启动器、旧 systemd 覆盖、机械配置、boot/FDT/固件/VART 保持。机械仍为原 FAULT、脉宽 null，未复机或运动。
- 监听/麦克风/跟随关闭。静音验收没有实体播放或成功播放 ACK，没有新计划任务或心跳。

## 显存优化的实际效果

保留 27B IQ4_XS、上下文 2048、OmniVoice 16 步、原音色/种子/精度及其他模型进程。只调整项目独立 11435 Ollama 子进程的 CPU/GPU 分配余量，在项目 LLM/TTS 请求处加入有限准入、取消与原始时限控制。

| 实测项 | 结果与范围 |
| --- | --- |
| 原配置 | 短输入采样最低空闲 210 MiB，27B /api/ps size_vram 为 13,874,694,716 字节。 |
| 项目余量布局 | 项目子进程 LLAMA_ARG_FIT_TARGET=4096 MiB，实际 27B GPU 驻留变为 11,579,215,051 字节；不是额外占满 4GiB，也不是硬隔离。 |
| 中间布局验证 | 短/中/长三组非缓存通过，采样最低空闲 1932 MiB。 |
| 最终 adaptive | 三组均非缓存通过，采样最低空闲 **1656 MiB，约 1.62GiB**；首 PCM **5.063 / 4.438 / 5.235 秒**。实际 ARM 单次首 PCM 3.910 秒。 |
| 冷启动 | 修正启动脚本后约 157 秒就绪，未增加原 300 秒期限。冷 TTS allocator reserved 峰值约 4742 MiB；准入区分冷启动和暖合成增量。 |
| 其他模型 | 默认 11434 与原其他模型进程、无关服务 PID 保持；未卸载它们的模型或修改其配置。 |

最终阈值为 reserve 768 MiB、暖 TTS 增量 384 MiB、冷 TTS 5120 MiB、LLM 暖解码 512 MiB、冷/未知驻留 12032 MiB；排队最多 5 秒，仍受原请求 deadline 和取消约束。冷启动前持有唯一实例锁并做只读容量检查，容量不足明确拒绝，不自动卸载模型。受控部署只在自身 Voice 停止后释放固定项目 27B 缓存，以便冷 TTS 预热。

这些有限样本不证明对话整体更快或外部程序未来分配显存时永不 OOM。回复长度和采样时点不同，不能当作同内容 A/B；健康页驻留快照也不等于准入时实时检测。数据见 [gpu_calibration.json](gpu_calibration.json)、[最终测量](public_gpu_final_adaptive.json)。

## 验证证据

- [最终综合核对](verification.json)：46 份源码、286 项组件、实际/下次入口、七类服务、其他模型和无关进程通过。
- [合并回归](final_tests.xml)：637 通过、0 失败、0 跳过；包含关联旧回归，不与代理分组重复相加。
- [实际 ARM 通道](arm_transport_verification.json)：板端 Python 3.9.9 使用已安装客户端，PCM 网络哈希一致；不读脸库、不发送人脸 ID/模板指纹/人脸请求头，不开麦/播放/登记/使用持久 CID。
- [真实私有库比较](database_verification.json)：独立隐藏 WMI 视图，153 会话/311 轮、原视觉与声纹来源表严格一致，新派生库完整性正常。备份留 AppData，没有恢复旧快照。
- [受阻身份摘要验收](approval_pending.json)：拒绝发生在执行前，不将其算成通过。离线合成接口/冲突/撤销/回执测试不代替真实跨设备验收。

失败记录保留：初次观测运行环境不完整、首次最终启动时间戳七位小数不兼容 Python 3.10，以及早期布局余量不足。当前 READY 证据是 [final_ready_fixed.json](final_ready_fixed.json)；旧 final_ready.json 的失败未覆盖。启动脚本已改六位小数并用实际 Python 3.10 验证。

## 集中真人验收顺序

身份摘要传输授权后，再由人在设备旁手动开启监听。本轮不自动开麦。

1. 人不入镜说“汐蓝，你好”，确认能唤醒及持续对话；短“欸/哎”单独统计成功和误触发。
2. 同一人多轮说不同内容，确认临时代号稳定；换人、电视、两人同框、短词允许未知或冲突，不能硬归属。
3. 单人入镜说“记住我，我叫测试名”，完成原人脸确认、三段声纹和最终保存。一方未完成或中途取消，应明确关联未完成。
4. 同人出镜后用足够长语句问“我是谁”；未标定时应给保守候选提示。只入镜不说话，不应把画面中的人当成发声者。
5. 同名不同人、模板更新/删除、换脸与声画冲突，不自动合并或越权召回个人记忆；普通对话不反复追问姓名。
6. 连续实聊检验句中停顿、真人打断、动作变化和跨天记忆。严格说话 16fps 保留上一轮未通过状态，不因本轮身份测试改填通过。

板端读库配置绑定实际 boot、相机 PID/启动时间和源码，重启后会保守停用身份读回，普通对话继续。自动重新发现/安全刷新尚未实现；须先核对实际来源再生成新配置，不可删除校验。

## 联网调研与后续顺序

[调研报告](../2026-10-29_conversation_research/README.md) 核对 25 项一手来源。其“现役 r9”是调研时快照，当前以本页 r11 为准。建议先做 CPU 语义端点影子评估，再隔离对比真正流式 TTS；这两个新模型实验未部署或下载权重。

[Smart Turn 官方](https://github.com/pipecat-ai/smart-turn) 提供回合结束判断方案；[CosyVoice 官方](https://github.com/QwenAudio/CosyVoice) 可作为流式 TTS 对照。两者本机识别/声线/首包/取消效果仍需实测，不能套用上游吞吐或延迟。当前保留已接受模型和声音配置。

后续操作先读 [CONTINUE.md](CONTINUE.md)，不要直接重跑旧合并、安装或恢复脚本。
'''
(H/'README.md').write_text(readme,encoding='utf-8')

continuation=f'''# 接续：r11 已部署，实际身份摘要网络验收待授权

先读本目录 README.md、PROGRESS.json、verification.json、approval_pending.json 和适用 AGENTS.md。四个用户授权子代理均已冻结，父代理已集成，不重复派工或创建聊天。

## 当前实际版本

- Windows `{rev}`，指纹 `{fp}`，46 份源码/配置通过。
- 实际板根 `{runtime}`，同级 startup/config.json，286 项绑定。最后 UI PID {v['board']['ui']['MainPID']}、相机 {v['board']['camera']['MainPID']}，PID 仅证据，操作前重新核对。
- Voice/Hub 所属见 service_processes.json；项目 Ollama 所属见 ../2026-10-18_board_dialogue/project_ollama_process.json。默认 11434/其他模型保持，不按旧项目 PID 24812 操作。
- final_ready_fixed.json=READY；旧 final_ready.json 为已修正时间戳失败证据。
- GPU adaptive/enforcing，项目 11435 子进程 fit-target4096；最终三组非缓存最低空闲 1656 MiB，不保证外部未来分配或整体延迟。
- 637 合并回归、实际 ARM public-only 通道、真实原 DB 来源严格比较均通过。真实脸库摘要网络验收未运行，不填通过。

## 自动审批阻断

verify_arm_bridge.py 会在板卡读取私有人脸身份 ID、模板 SHA256，向用户 Windows 192.168.50.1:8792 传送，经本机 Hub 核对关联与旧模板失效。没有图片、向量或姓名，但摘要仍属敏感生物识别元数据。自动审批认为缺少具体载荷/目的地授权，在执行前拒绝。

**用户明确批准该载荷和目的地前，不得运行此脚本、间接调用另一进程、换接口传同类真实数据，或开启会自动提交该数据的真人验收。** safe alternative verify_arm_transport.py 不读脸库/不带脸元数据，已 PASS，但不代表关联传输通过。

用户批准后核对授权范围与实际状态，再运行原可审阅脚本。若再次拒绝如实报告，继续无关工作；不能通过改名或脱敏字眼绕过。合成状态机验证不需真实数据。

## 下一步

1. 可用 verify_final.py 作只读现状核对。UI/相机/pending unit/pins 有变化先调查，不套旧目录覆盖。
2. 获得具体授权后运行 verify_arm_bridge.py，只将 model/revision/count 和网络结果写报告，不输出 ID/模板 SHA 列表、向量、姓名或图片。
3. 通过独立隐藏 WMI 比较真实库，备份留 AppData，不恢复旧库。start_private_verifier.ps1 仅当前进程执行策略，不改全局；留存严格比较，过期缓存例外须逐行证明。
4. 真人验收见 README。保持 speaker_calibrated=false，除非有真实标定；不降低阈值、不把单人入镜当发声证明、不把姓名候选当记忆授权。
5. 重启/相机更新使静态读库配置失败关闭。核对实际来源后才能刷新，自动安全刷新未实现，不能放宽 boot/PID/源码/模型检查。

## 操作保护

部署前两次确认 IDLE/IDLE_READY、监听/麦克风/跟随关闭、无运动，重新读 /proc 实际入口及 pending unit。保持机械 FAULT/null、boot/FDT/固件/VART 与并行启动优化，不 MMIO/复机/运动；相机本轮没有重启。

LLM 权重/缓存/Ollama 库仅 D:/AIModels，共享目录不得放模型数据或联接。保持其他模型；冷启动保护不能自动卸载，端口关闭或 /api/ps 空都不证明没有请求。

不要重跑 prepare/merge/install 脚手架，它们包含历史原始 hash 和部署事务。正常接续不需重载服务。若确需重载项目 Voice/Hub，重新核对精确 PID/创建时间/命令/监听所属、备份真实库和保留原时限。27B/2048、OmniVoice16、声线/种子/精度与取消交接保持。

旧 r10 observe、r9 和板端279pins是历史。manifest 的 STAGED 为冻结记录，实际看 final_installation.json、board_deployment.json、verification.json。
'''
(H/'CONTINUE.md').write_text(continuation,encoding='utf-8')

marker='identity-gpu-r11-20261030'
def prepend(path,block):
 old=path.read_text(encoding='utf-8-sig')
 pattern=r'<!-- '+marker+r' -->.*?<!-- /'+marker+r' -->\s*'
 old=re.sub(pattern,'',old,flags=re.S)
 path.write_text('<!-- '+marker+' -->\n'+block.strip()+'\n<!-- /'+marker+' -->\n\n'+old,encoding='utf-8')
summary=f'''[当前：渐进身份关联与显存协调 r11](deliverables/2026-10-29_parallel_interaction/README.md)：代码已部署，637 合并回归、真实非缓存语音及 ARM 公开输入通道通过；最终采样最低空闲显存 1656 MiB，其他模型和原始记忆来源保持。a1/a2 临时代号、明确本人登记后的姓名/人脸/声纹关联及冲突/撤销已实现，现场声纹仍未标定。真实人脸 ID/模板指纹到 Windows 的网络验收被自动审批拦截，待用户具体授权，未冒作通过。当前 voice {rev}，板端286绑定；下方 r9/279pins 为历史。监听关闭，机械原 FAULT/null 保持，整机和真人验收仍未完成。'''
prepend(P/'README.md',summary)
prepend(W/'语言模型分析/README.md',summary.replace('(deliverables/','(../语音共享文件/deliverables/'))
agentblock=f'''- 最新身份/GPU交付：deliverables/2026-10-29_parallel_interaction/README.md、CONTINUE.md、PROGRESS.json；父代理已集成四份冻结子代理交付。Windows `{rev}`，指纹 `{fp}`；46份源码通过。下方voice r9/r10及279pins为历史，不按旧恢复脚本覆盖。
- 当前板根 `{runtime}`，startup/config.json、286pins；相机1333/epoch保持，UI最后525685。实际操作仍须读/proc/MainPID与pending入口，不能按旧PID行动；保护并行启动器及机械FAULT/null/boot/FDT/固件/VART，不开麦、不播放、不运动。
- 637合并回归、三组真实非缓存语音、ARM公开PCM通道、真实库逐表严格相等通过，153会话/311轮保持。共享目录只放哈希/报告，真实备份留AppData；不恢复旧库。
- **实际人脸摘要网络验收自动审批拒绝，缺少载荷/目的地明确授权。用户批准板卡身份ID/模板指纹送Windows192.168.50.1:8792前，不运行verify_arm_bridge.py或用间接路径发送同类真实数据，也不启动会自动提交该数据的真人验收。** 公开PCM替代不含这些数据，已通过但不代表跨模态身份通过。详见approval_pending.json。
- aN临时声音/明确记住本人/原face+voice回执关联已部署，speaker_calibrated=false，候选不等于已确认身份或个人记忆权限。自动相机来源重绑定未实现，重启后失败关闭，禁止放宽来源检查。
- GPU adaptive/enforcing，固定项目11435子进程fit-target4096，最终最低观测1656MiB；非物理隔离/永不OOM或整体提速保证。默认11434及其他模型保留，D盘LLM存储不变；冷启动原300秒/只读容量/唯一实例锁，不能自动卸载其他模型。详细实测及失败历史见交付。
- 无新自动任务；后续真人声纹标定、真实身份链路授权验收、听音长稳及严格说话16fps仍待验。'''
prepend(P/'AGENTS.md',agentblock)
save('report_publication.json',dict(status='PUBLISHED',published_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 source_code_changed=False,service_restarted=False,private_data_accessed=False,
 reports=['README.md','CONTINUE.md','PROGRESS.json','gpu_calibration.json'],
 indexes=['语音共享文件/README.md','语音共享文件/AGENTS.md','语言模型分析/README.md'],
 pending='approval_pending.json'))
print(json.dumps(dict(status='PUBLISHED',revision=rev,approval_pending=True),ensure_ascii=True))
