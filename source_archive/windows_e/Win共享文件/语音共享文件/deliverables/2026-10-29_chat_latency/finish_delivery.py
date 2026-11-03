"""Publish a verified, reproducible delivery; no runtime state changes."""
import datetime,hashlib,json,zipfile
from pathlib import Path
H=Path(__file__).resolve().parent;P=H.parents[1]
def read(name):return json.loads((H/name).read_text(encoding='utf-8'))
verified=read('release_verification.json');assert verified['status']=='PASS'
performance=read('performance_summary.json');assert performance['status']=='FINAL'
plan=read('source_plan_r8.json');assert plan['candidate_fingerprint']==verified['fingerprint']
lines=[]
for key,label in [('original','原r6'),('rejected_r7','已撤回的r7格式提示'),('final_r8','最终r8')]:
 row=performance['phases'][key]
 uncached='—' if row['uncached_first_pcm_median_ms'] is None else f"{row['uncached_first_pcm_median_ms']/1000:.3f}秒"
 lines.append(f"| {label} | {row['trials']} | {row['tts_cache_hits']} | {row['first_pcm_median_ms']/1000:.3f}秒 | {uncached} |")
counts=verified['final_database_counts'];conv=counts['conversation'];obs=counts['observation']
readme=f'''# 普通聊天与时间轴记忆分流 r8

已部署 voice-chat-context-20261029-r8，指纹 `{verified['fingerprint']}`。本轮修复“今天有点累”等普通聊天被误当历史查询的问题，保留时间轴、视觉补充、事实更正/遗忘及r6取消交接修复。格式提示的性能试验没有证明整条语音提速，已经撤回。板卡迁移继续暂缓。

## 修改与验证

语音调用增加独立的历史意图判断：普通聊天中的日期不再自动触发时间轴检索；“今天我们聊了什么”“昨天下午杯子在哪”等明确回忆保留原入口。日期查询API、删除范围解析、个人权限、历史容量和来源保护保持原语义。视觉继续只作可选补充，语音无需入镜。

LLM请求增加完整请求SHA256和JSON格式空白数诊断；仅记录摘要/计数，不在诊断里复制原话、记忆、图像或录音。撤回格式提示后，实际模型请求与r6逐项相同，未减少上下文、改变音色、降低16步合成或启用不稳定的原生grammar路径。历史意图仍是保守规则，并非所有自然表达都已经验证。

- 347项相关回归通过，包含此前285项及记忆与上下文边界专项，不能把历史数量相加。见[日志](tests_r8_retest_final.log)、[JUnit](tests_r8.xml)。最初受限环境本地HTTP回归挂起已终止；包装重跑首次遗漏模块路径失败，修正后完整通过，原记录保留。
- 14步实际ASR/TTS记忆验收通过：录入、更正、旧值查询、删除预览/确认、中文索引、当前事实直答、遗忘、不虚构已遗忘值、普通日期聊天/真实历史分流及普通持久问答。仅清理精确公开测试会话，并核验真实来源覆盖。见[验收](live_controls_acceptance.json)、[清理](public_probe_cleanup.json)。
- 板端现有ARM客户端经网线完成文字、活动TTS、首PCM三种取消后立即接新问，以及单独唤醒/非唤醒拒绝，共5项通过。PCM仅在RAM接收，未开麦、实体播放或发送成功播放ACK。见[板端链路](live_handoff_r8_final.json)。
- 独立隐藏WMI进程检查真实私有数据库，用户原始来源逐表SHA256不变：最终{conv['conversations']}会话/{conv['turns']}轮、{obs['observations']}观察/{obs['visual_timeline']}视觉事件。声纹源表同样保持。备份留在用户私有目录，未导出身份库。见[数据核验](physical_database_check.json)。

## 实际延迟结果

同4份公开16kHz录音，每版两轮8次，另有一次不计分预热；真实ASR、27B、OmniVoice16和原语音协议。测试使用独立匿名boot/session，无持久对话或现场开麦/播放。

| 版本 | 样本 | TTS缓存命中次数 | 全样本首PCM中位数 | 未缓存样本首PCM中位数 |
| --- | ---: | ---: | ---: | ---: |
'''+ '\n'.join(lines)+'''

r7虽然更早给出文字，但语音合成和后续解码变慢，首PCM由4.052秒变为4.353秒，因此撤回。相同固定台词的反向顺序对照中，两种请求本来都没有格式空白，且有提示缓存混杂，不能用它证明格式提示提速。原始及失败试验全部保留。

最终r8的结果见上表和[完整性能汇总](performance_summary.json)。普通“今天”聊天的额外历史消息已从1条降为0条，实际历史问题仍走原时间轴。自由回答内容、测试顺序和共享机器负载都有波动；以上小样本不足以宣称普通聊天稳定提速或通过延迟验收。缓存命中也不能当作27B速度。网络供给间隙模拟不代表实体播放没有长帧。

共享GPU观测约15.7/16GB占用及系统内存压力；并发争用可能影响结果，尚未通过受控实验确定因果。没有卸载或停止其他模型。原版和r7这两组测量开始时，默认Ollama模型已经自然不在驻留列表中，两组前后列表各自一致；不是本任务卸载模型来换速度。

## 运行状态与边界

只重载Windows8792及其所属TTS。其他模型/端口保持，compact_grammar=false、其余五项开关true；LLM权重与Ollama数据仍在D盘。板端实际根、UI/相机PID、279项精确绑定与READY/1604µs保持，未更新板端代码或启用运动。最终检查见[release_verification](release_verification.json)。监听/麦克风保持关闭，需要用户在原界面手动开启后现场复测；本任务不自动打开。

整个玩偶仍未最终验收：普通聊天延迟长尾、短词“欸/哎”即时唤醒、实体说话长帧、声画归属与现场声纹标定、跨天记忆体验和长稳均待验证。用户先完善Windows对话和记忆、再考虑迁移的顺序保持。后续操作见[CONTINUE](CONTINUE.md)，状态见[PROGRESS](PROGRESS.json)。
'''
(H/'README.md').write_text(readme,encoding='utf-8')
continuation=f'''# 接续约束

现役Windows为 voice-chat-context-20261029-r8 / {verified['fingerprint']}，正式回执deployment_r8.json及release_verification.json。r6交接修复、r4记忆功能完整保留；r7紧凑格式提示已因整链路未提速撤回。旧source_plan.json、deployment.json、candidate_source及before是原r7试验记录；不得重跑旧部署。当前源在candidate_r8_source，部署前r7备份before_r8，最初r6原文件在before，不能直接覆盖新版本。

347回归、14项真实记忆、5项ARM语音协议及8样本最终测量完成；详见README与performance_summary。不得称整体提速、现场播放通过或整机完成。语音独立于视觉，日期检索/删除API仍用historical，语音路由用recall_requested。完整请求摘要仅用于比对，不替代来源、个人授权或原请求时限。

板卡迁移后置，其他模型运行及D盘LLM/Ollama存储保持。最终监听/麦克风/跟随关闭；测试没有开麦、实体播放、成功播放ACK或运动。现场复测应由用户在原界面手动开始，自动化不能自行开麦或恢复跟随。

每次部署前重新读实际入口/源码、boot、绑定、UI/相机PID和机械状态，并双重确认静止空闲、监听/麦克风关闭且IDLE_READY。当前记录仅为本次证据：boot55152f95-ea3a-4c6c-82e6-51bd553d96fd，根/home/root/aura-boundary-nav-20261029/gui-page-sync-v2/runtime，279绑定，UI114923/相机21824，READY/1604µs；不能据此重写后续并行更新。

用户数据库真实文件视图需要独立隐藏WMI进程。original_database_checkpoint.json为本轮144会话/276轮、77观察/73视觉事件基线，私有备份位于AppData，不能复制进共享树；最终逐表SHA核验通过，不要恢复旧143/273、141/269或6/2快照。只可按cleanup_public_probe.py的精确随机测试CID及请求归属清理公开探针，不能删除用户会话/视觉/身份数据。

后续建议先收集用户开启后的同一句现场转写、请求结果码与各阶段计时，检查长尾是在说完判定、27B还是TTS；本轮没有证明串行调度更快，不应未经对照上线。2026-10-18_gpu_scheduling已有同台词串行更慢的拒绝证据。不得重新缩短取消时对正在运行TTS的等待而使暖进程退出，不放宽原请求/worker时限，不自动卸载其他模型。没有新建心跳或自动任务。
'''
(H/'CONTINUE.md').write_text(continuation,encoding='utf-8')
progress={'status':'COMMITTED_VERIFIED_WINDOWS_R8','complete':True,'scope':'precise timeline voice routing and performance investigation',
 'revision':verified['revision'],'fingerprint':verified['fingerprint'],'tests_passed':347,
 'actual_memory_checks':14,'arm_handoff_checks':5,'voice_samples':8,
 'latency_performance_accepted':False,'rejected_candidate':'r7 compact serialization hint',
 'full_project_complete':False,'board_migration':False,'listening_remains_off':True,
 'original_sources_unchanged':True,'other_models_stopped':False,
 'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
(H/'PROGRESS.json').write_text(json.dumps(progress,ensure_ascii=False,indent=2),encoding='utf-8')
marker='chat-context-r8-20261029'
brief=f'''<!-- {marker} -->
- 现役Windows已更新voice-chat-context-20261029-r8，指纹{verified['fingerprint']}。最新接续deliverables/2026-10-29_chat_latency/README.md、CONTINUE.md、PROGRESS.json；下方r6/r4为保留功能的历史版本，不得按旧指纹覆盖现役。
- 普通“我今天有点累”不再误触时间轴，真正历史查询保留；日期API/删除/个人权限/记忆容量/来源链和r6取消交接不变。增加完整请求摘要和格式计数诊断，不存原文。r7格式提示首PCM中位数4.052→4.353秒未提速，已撤回；最终数据见报告，不能宣称普通聊天延迟验收通过。
- 347相关回归、14项实际记忆、板端5项取消接话/唤醒及8次最终录音测量通过。公开探针精确清理，原144会话/276轮、77观察/73视觉事件及声纹来源逐表SHA保持；私有WMI数据库视图约定保留。
- 仅重载8792/TTS，其他模型和服务保持；板端代码/279绑定/UI114923/相机21824/READY1604µs不改。监听已由本轮原UI暂停，最终关闭，不能按下方旧“监听已开启”自动开麦。迁移继续暂缓，LLM数据留D盘。普通聊天长尾、短词、说话长帧、声画归属/现场声纹及跨天长稳仍待验；整机未完成，无新自动任务。
<!-- /{marker} -->

'''
path=P/'AGENTS.md';source=path.read_text(encoding='utf-8');assert marker not in source;path.write_text(brief+source,encoding='utf-8')
links=[(P/'README.md','deliverables/2026-10-29_chat_latency/README.md'),
 (P.parent/'语言模型分析/README.md','../语音共享文件/deliverables/2026-10-29_chat_latency/README.md')]
for path,url in links:
 source=path.read_text(encoding='utf-8');assert marker not in source
 intro=f'<!-- {marker} -->\n[当前Windows对话/记忆分流r8及实测]({url})：普通日期聊天不再误触历史检索；347回归、14项真实记忆、5项ARM协议检查通过。格式提示未证明提速已撤回，用户数据/其他模型/板端保持；当前监听关闭，迁移继续暂缓，整机与延迟验收未完成。\n<!-- /{marker} -->\n\n'
 path.write_text(intro+source,encoding='utf-8')
files=[]
for name in ['README.md','CONTINUE.md','PROGRESS.json','release_verification.json','performance_summary.json',
 'source_plan.json','source_plan_r8.json','deployment.json','deployment_r8.json','physical_database_check.json',
 'live_controls_acceptance.json','public_probe_cleanup.json','live_handoff_r8_final.json',
 'voice_before.json','voice_after.json','voice_refined.json','voice_before_initial_contract_fail.json',
 'tests_r8.xml','tests_r8_retest_final.log','tests_r8_retest.log','tests_context_final.log',
 'tests_context.log','format_only_tests_final.log']:
 files.append(H/name)
files+=list(H.glob('*.py'))+list(H.glob('*.ps1'))+list(H.glob('llm_*.json'))
for directory in ('before','before_r8','candidate_source','candidate_r8_source'):files+=list((H/directory).rglob('*.py'))
files=sorted(set(files));assert all(path.is_file() for path in files)
assert not any(path.suffix.lower() in ('.sqlite3','.db','.wav','.mp3','.safetensors','.gguf') for path in files)
archive=H/'voice-chat-context-r8-source-evidence.zip';assert not archive.exists()
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as output:
 for path in files:output.write(path,path.relative_to(H).as_posix())
with zipfile.ZipFile(archive) as output:assert output.testzip() is None
manifest={'file':archive.name,'files':len(files),'bytes':archive.stat().st_size,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
 'no_models_environments_raw_media_keys_or_private_databases':True}
(H/'archive_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(json.dumps({'status':progress['status'],'archive':manifest,'full_project_complete':False}))
