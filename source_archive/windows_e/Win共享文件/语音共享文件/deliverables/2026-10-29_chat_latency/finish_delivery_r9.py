"""Publish only verified r9 receipts; no runtime changes or private data export."""
import datetime,hashlib,json,zipfile
from pathlib import Path
H=Path(__file__).resolve().parent;P=H.parents[1]
def read(name):return json.loads((H/name).read_text(encoding='utf-8'))
verified=read('release_verification.json');assert verified['status']=='PASS'
plan=read('source_plan_r9.json');assert plan['candidate_fingerprint']==verified['fingerprint']
perf=read('performance_summary.json');assert perf['status']=='FINAL'
phases=perf['phases'];gpu=phases['final_r9']['tts_idle_cuda_cache']['first_ready_observation']
assert gpu['available'] and gpu['released_bytes']>0
GiB=1024**3
table=[]
for key,label in [('original','原r6'),('rejected_r7','已撤回r7格式提示'),('intermediate_r8','中间r8'),('final_r9','最终r9')]:
 row=phases[key];uncached=row['uncached_first_pcm_median_ms']
 table.append(f"| {label} | {row['trials']} | {row['tts_cache_hits']} | {row['first_pcm_median_ms']/1000:.3f}秒 | {uncached/1000:.3f}秒 |")
long=[]
for key,label in [('intermediate_r8','r8'),('final_r9','r9')]:
 for row in perf['long_conversation_model_turns'][key]:
  long.append(f"| {label} | {row['label']} | {row['history_messages']} | {row['first_pcm_ms']/1000:.3f}秒 | {row['tts_cache_hits'] if row['tts_cache_hits'] is not None else '未记录'} |")
counts=verified['final_database_counts'];conv=counts['conversation'];obs=counts['observation']
readme=f'''# 对话/时间轴分流与TTS空闲显存管理 r9

已部署 `{verified['revision']}`，指纹 `{verified['fingerprint']}`。本轮完成普通日期聊天与历史查询分流，并归还TTS未使用的显存缓存；原记忆与取消接话修复保留。355项回归、14步实际记忆和板端5项协议检查通过，原始用户数据核验保持。板卡迁移继续暂缓，整机与普通聊天延迟验收尚未完成。

## 具体变化

“我今天有点累，陪我聊聊”原先仅因出现“今天”就触发时间轴检索，额外加入历史上下文。现在语音路由单独判断回忆意图：普通日期聊天不再自动查询历史；“今天我们聊了什么”“昨天下午杯子在哪”等明确回忆保留原流程。日期查询API、删除范围解析、个人权限、历史容量、来源保护不变；语音无需入镜，视觉继续作可选补充。这是保守规则，尚未覆盖所有自然表达。

TTS在完成预热或生成并保存WAV后，若未使用的CUDA分配器缓存达到64MiB，则调用本进程empty_cache归还空闲块。保持活动张量、已加载权重、参考音色、seed8701、SDPA/FP16、16步合成及原请求/worker时限；不在合成中途释放，不退出暖态进程，不卸载其他模型。可选缓存整理失败不覆盖已经完成的有效WAV，真实推理故障仍走原错误路径。

服务就绪后的首次分配器观察显示，本进程保留的显存从约{gpu['reserved_before_bytes']/GiB:.2f}GiB降至{gpu['reserved_after_bytes']/GiB:.2f}GiB，归还{gpu['released_bytes']/GiB:.2f}GiB，整理耗时{gpu['trim_ms']:.2f}ms，活动张量仍保留。这是直接测得的空闲缓存占用变化，不能直接换算成对话提速。该计数来自首轮测量开始时；该轮后续的延迟统计因模型驻留变化失效，独立的分配器计数仍保留。每次未缓存请求的释放量与整理耗时见[性能汇总](performance_summary.json)。

另新增完整模型请求SHA256及JSON格式空白数诊断，只记录摘要/计数，不复制原话、记忆、图像或PCM。早先r7紧凑格式提示未改善整链路延迟，已经撤回；对相同输入和历史，r8/r9的LLM请求与r6一致，字段、人设和容量不变，未重新启用compact_grammar。普通日期聊天只因路由修复而避免了额外的时间轴消息。

## 验证结果

- 355项相关回归全部通过，包含原347项和8个缓存管理专项；数量互有包含，不能累加。覆盖上下文近容量边界、来源与个人权限、更正/遗忘/删除、取消交接、缓存释放时机、活动内存保留、可选整理失败、合成参数/缓存身份相同。见[日志](tests_r9_final.log)、[JUnit](tests_r9.xml)。
- 最终r9的14步实际ASR/TTS记忆验收通过：录入、更正、历史值、删除预览/确认、中文编号、当前事实直答、遗忘与拒绝虚构、普通日期聊天/真实历史分流、普通持久问答。精确公开探针会话已清理，并验证真实来源覆盖；见[验收](live_controls_acceptance_r9.json)、[清理](public_probe_r9_cleanup.json)。r8此前同一套14步证据保留。
- 真实板端已有ARM客户端经网线完成文字、活动TTS、首PCM三种取消后立即新问，以及单独唤醒/非唤醒拒绝，共5项通过。PCM在内存中接收，无开麦、实体播放、成功播放ACK或持久测试对话；见[板端检查](live_handoff_r9_final.json)。
- 独立隐藏WMI进程从真实生产文件视图做私有备份和逐表SHA比较，用户原始来源不变：{conv['conversations']}会话/{conv['turns']}轮、{obs['observations']}观察/{obs['visual_timeline']}视觉事件，声纹源表同样保持。私有数据库、模板和备份未复制进交付包；见[数据核验](physical_database_check.json)。
- 只重载8792及其所属TTS。其他模型及服务端口保持，板端实际根、279精确绑定、UI/相机PID及READY/1604µs保持，未重启板端或启用运动。完整结果见[release_verification](release_verification.json)。

## 延迟实测与局限

每版同4份公开16kHz录音两轮8次，另有一次不计分预热；走实际ASR、27B、OmniVoice16及原网线语音协议。使用独立匿名boot/session，无持久会话和现场麦克风/播放。下表区分缓存命中和未缓存结果。

| 版本 | 样本 | TTS缓存命中次数 | 全样本首PCM中位数 | 未缓存样本首PCM中位数 |
| --- | ---: | ---: | ---: | ---: |
'''+ '\n'.join(table)+'''

r7文字更早但TTS和后续解码更慢，首PCM4.052→4.353秒，因此撤回格式提示。相同固定台词的反向顺序实验本来均无格式空白，且受提示缓存混杂，不能据此主张格式提速。

r9首轮8个语音回复均完整返回，但途中其他模型自然改变驻留状态，严格性能校验失败。这组保留在[失效测量](voice_trimmed.json)，不计入最终性能统计。重新测量仍执行相同驻留校验，没有放宽条件、删除坏样本或卸载其他模型。最终8次见[测量](voice_trimmed_final.json)。其中1轮两段回答出现约0.494秒的模拟网络供给缺口，连续说话仍待优化。前后驻留列表稳定也不等于共享机器负载恒定；自由回答内容与顺序不同，因此最终数字只表示本次实测，不能当成稳定延迟保证或严格的因果A/B。

14步记忆验收序列中的最后三轮模型回答另列结果。它们实际仅携带0/1/2条历史消息，不代表长历史压力或跨天记忆体验验收，也不与前述8次测量混为一组：

| 版本 | 公开验收序列模型轮 | 历史消息 | 首PCM | TTS缓存命中 |
| --- | --- | ---: | ---: | ---: |
'''+ '\n'.join(long)+'''

普通日期聊天额外历史上下文已由1条降为0条；真实历史问题仍使用时间轴。仍有慢轮，普通聊天延迟及长尾未最终通过。首PCM是网络内存到达时间，不含现场说完判定和物理声学起音；供给间隙模拟也不代表实体播放无长帧。

## 现场状态与后续

最终监听、麦克风、跟随保持关闭，音频IDLE_READY。测试期间未自动开麦/播放/运动；用户可在原界面手动开启后用完整“汐蓝，你好”复测。单独叫名后回聆听属于正常唤醒等待，不能一概认作旧503故障。

语音/记忆继续在Windows完善，LLM权重、Ollama数据留D盘。后续仍需处理普通聊天长尾、短词“欸/哎”即时唤醒、实体说话长帧、声画归属与现场声纹标定、跨天记忆体验和整机长稳。当前完成的是本轮软件修复及自动验证，不是整个玩偶最终验收。状态见[PROGRESS](PROGRESS.json)，接续约束见[CONTINUE](CONTINUE.md)。
'''
(H/'README.md').write_text(readme,encoding='utf-8')
continuation=f'''# 接续

现役 {verified['revision']} / {verified['fingerprint']}。以source_plan_r9.json、deployment_r9.json、candidate_r9_source和release_verification.json为当前依据；before_r9是部署前r8。r7/r8源和回执均是历史，旧部署与finish_delivery.py不得重跑；不能按r6旧指纹覆盖。r6取消时保留已运行TTS、原时限内完成丢弃旧结果的规则保持，不能重新提前退出导致暖进程退役。r4记忆/来源/个人权限能力保留。

355相关回归、最终14步实际记忆、5项ARM协议及8次最终语音测量完成。r7格式提示已撤回；r9第一组因其他模型驻留变化严格失败的8次保留在voice_trimmed.json，最终有效组voice_trimmed_final.json，不能把失效组混入统计或放宽校验。TTS只归还完成合成后的空闲分配器缓存，保留活动张量/权重，64MiB门槛；整理耗时属于真实请求成本，不能隐去。普通聊天稳定延迟/整机未验收，不能将显存释放量直接换算成提速。长期记忆仍以来源为准，接收时间不是事实实际生效时间。

用户要求Windows对话/记忆优先，板端迁移继续暂缓。保留其他模型运行、D盘LLM/Ollama存储；不复制权重、下载分段、虚拟环境或目录联接进入共享树。ASR/TTS既有明确授权配置保持。语音独立于视觉；历史语音路由用recall_requested，日期API/删除解析保留historical。

最终监听/麦克风/跟随关闭、IDLE_READY。禁止自动开麦、实体播放、启用运动或恢复跟随；现场复测由用户原UI手动开启。每次新部署须动态双重核对实际入口/源码、boot/绑定、UI/相机PID、静止空闲和监听关闭，保护并行机械更新，不重写绑定适配旧环境。本轮仅作证据：boot55152f95-ea3a-4c6c-82e6-51bd553d96fd，根/home/root/aura-boundary-nav-20261029/gui-page-sync-v2/runtime，279绑定，UI114923/相机21824，READY1604µs，不能当永久配置。

原始数据本轮基线144会话/276轮、77观察/73视觉事件，声纹来源同样逐表SHA保持。真实AppData视图须独立隐藏WMI进程，当前工具同名路径可能是影子副本；私有备份在AppData，不得复制到共享目录或恢复旧143/273、141/269、6/2快照。公开探针只能按精确新CID、request归属清理，r8/r9回执和清理脚本分开。

下一步优先采集用户现场同一句话的转写、请求结果和分段计时，区分说完判定、27B解码、TTS与板端播放长帧，再做负载匹配对照。不得为测试自行卸载其他模型/重启板端或改变合成质量。串行LLM/TTS在2026-10-18_gpu_scheduling有更慢的拒绝证据，不直接上线。没有新建心跳或自动任务。
'''
(H/'CONTINUE.md').write_text(continuation,encoding='utf-8')
progress={'status':'COMMITTED_VERIFIED_WINDOWS_R9','complete':True,'scope':'precise voice memory routing and idle TTS GPU cache release',
 'revision':verified['revision'],'fingerprint':verified['fingerprint'],'tests_passed':355,'actual_memory_checks':14,
 'arm_handoff_checks':5,'final_voice_samples':8,'first_ready_gpu_cache_released_bytes':gpu['released_bytes'],
 'final_first_pcm_median_ms':phases['final_r9']['first_pcm_median_ms'],
 'final_uncached_first_pcm_median_ms':phases['final_r9']['uncached_first_pcm_median_ms'],
 'stable_latency_accepted':False,'full_project_complete':False,'board_migration':False,'listening_remains_off':True,
 'original_sources_unchanged':True,'other_models_stopped':False,'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
(H/'PROGRESS.json').write_text(json.dumps(progress,ensure_ascii=False,indent=2),encoding='utf-8')
marker='chat-memory-r9-20261029'
intro=f'''<!-- {marker} -->
- 现役Windows {verified['revision']}，指纹{verified['fingerprint']}。最新接续deliverables/2026-10-29_chat_latency/README.md、CONTINUE.md、PROGRESS.json。下方r6/r4等为保留功能的历史，禁止按旧指纹覆盖；r7格式提示未提速已撤回，r8中间版已升级。
- 普通“今天有点累”不误触时间轴，明确历史查询保留；日期API/删除/个人权限/记忆容量/来源保护与r6取消交接不变。新增完整请求摘要及格式计数，不记录原文。TTS完成后归还空闲CUDA缓存，首次就绪观测约{gpu['released_bytes']/GiB:.2f}GiB，活动张量/模型、音色/16步/原超时保持；不能直接称整体提速。
- 355相关回归、最终14步实际记忆、5项ARM取消接话/唤醒及8次最终语音测量通过。首轮r9模型驻留变化导致性能失败的8次保留不计入最终统计；缓存/未缓存及长会话单列。普通聊天稳定延迟和长尾仍未验收。
- 精确公开测试CID已清理，原144会话/276轮、77观察/73视觉事件及声纹来源逐表SHA保持；独立隐藏WMI真实私有库视图约定继续。只重载8792/TTS，其他模型/端口、板端代码/279绑定/UI114923/相机21824/READY1604µs保持，迁移暂缓，LLM数据留D盘。
- 本轮经原UI暂停监听，最终监听/麦克风/跟随关闭；不要按下方旧“监听已开启”自动开麦。实体听音/说话长帧、短词即时唤醒、声画归属/现场声纹、跨天长稳和整机仍待验，无新自动任务。
<!-- /{marker} -->

'''
path=P/'AGENTS.md';text=path.read_text(encoding='utf-8');assert marker not in text;path.write_text(intro+text,encoding='utf-8')
for path,url in [(P/'README.md','deliverables/2026-10-29_chat_latency/README.md'),
 (P.parent/'语言模型分析/README.md','../语音共享文件/deliverables/2026-10-29_chat_latency/README.md')]:
 text=path.read_text(encoding='utf-8');assert marker not in text
 head=f'<!-- {marker} -->\n[当前：对话/记忆分流与TTS空闲显存管理r9]({url})：355回归、14步真实记忆、5项ARM检查通过。普通日期聊天不再误触历史，TTS首次就绪观测归还约{gpu["released_bytes"]/GiB:.2f}GiB空闲缓存且模型保持驻留。原数据/其他模型/板端保持，监听关闭、迁移暂缓；延迟长尾及整机仍未验收。\n<!-- /{marker} -->\n\n'
 path.write_text(head+text,encoding='utf-8')
files=[]
for name in ['README.md','CONTINUE.md','PROGRESS.json','release_verification.json','performance_summary.json',
 'source_plan.json','source_plan_r8.json','source_plan_r9.json','deployment.json','deployment_r8.json','deployment_r9.json',
 'physical_database_check.json','live_controls_acceptance.json','live_controls_acceptance_r9.json',
 'public_probe_cleanup.json','public_probe_r9_cleanup.json','live_handoff_r8_final.json','live_handoff_r9_final.json',
 'voice_before.json','voice_after.json','voice_refined.json','voice_trimmed.json','voice_trimmed_final.json',
 'voice_before_initial_contract_fail.json','tests_r9.xml','tests_r9_final.log','tests_r8.xml','tests_r8_retest_final.log',
 'tests_r8_retest.log','tests_context_final.log','tests_context.log','format_only_tests_final.log']:
 files.append(H/name)
files+=list(H.glob('*.py'))+list(H.glob('*.ps1'))+list(H.glob('llm_*.json'))
for directory in ('before','before_r8','before_r9','candidate_source','candidate_r8_source','candidate_r9_source'):
 files+=list((H/directory).rglob('*.py'))
files=sorted(set(files));assert all(path.is_file() for path in files)
assert not any(path.suffix.lower() in ('.sqlite3','.db','.wav','.mp3','.safetensors','.gguf') for path in files)
archive=H/'voice-chat-memory-r9-source-evidence.zip';assert not archive.exists()
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as output:
 for path in files:output.write(path,path.relative_to(H).as_posix())
with zipfile.ZipFile(archive) as output:assert output.testzip() is None
manifest={'file':archive.name,'files':len(files),'bytes':archive.stat().st_size,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
 'no_models_environments_raw_media_keys_or_private_databases':True}
(H/'archive_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(json.dumps({'status':progress['status'],'archive':manifest,'full_project_complete':False}))
