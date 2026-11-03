"""Write the consolidated acceptance record, preserving unresolved items."""
import json,hashlib,zipfile,xml.etree.ElementTree as ET
from pathlib import Path
HERE=Path(__file__).resolve().parent
def read(n):return json.loads((HERE/n).read_text(encoding='utf-8'))
c=read('candidate.json');d=read('layout_deployment.json');s=read('muted_speech_probe.json');v=read('final_state.json');voice=read('live_voice_acceptance.json');before=read('baseline_speech.json')
outage=read('live_ui_outage.json');health=read('windows_health_final.json')
assert d['status']=='COMMITTED' and s['status']=='PASS' and v['status']=='PASS' and voice['status']=='PASS'
assert outage['status']=='PASS' and outage['ui_pid_unchanged'] and outage['remote_recovered']
assert all(health[n]['reachable'] and health[n]['health']['ready'] for n in ('asr','dialogue','frontend','portrait'))
testroot=ET.parse(HERE/'tests.xml').getroot()
assert sum(int(n.get('tests',0)) for n in testroot.iter('testsuite'))==50
assert all(int(n.get(k,0))==0 for n in testroot.iter('testsuite') for k in ('failures','errors'))
assert s['pause_resume_cancel']['passed'] and s['new_turn_after_cancel'] and s['original_mixer_restored']
spoken=s['speaking'];idle=d['sample']
speech_gate=spoken['native_fps']>=15.2 and spoken['p95_ms_median']<=78.125 and spoken['p99_ms_median']<=125
status={'status':'DEPLOYED_AUTOMATIC_CHECKS_RECORDED_REMAINING_WORK_OPEN','runtime':c['runtime'],'boot':v['boot'],
'checked_at_utc':v['checked_at_utc'],'idle':idle,'muted_speech':spoken,'strict_speech_16fps_gate':speech_gate,
'voice_chain':'PASS','pause_resume_cancel':'PASS','new_turn_after_cancel':'PASS','actual_ui_outage_recovery':'PASS','windows_services_ready':True,'windows_regressions':50,
'arm_focused_regressions':69,'microphone':False,'following':False,'mechanical':'FAULT: exact boot/firmware context mismatch; no MMIO',
'whole_project_complete':False,'remaining':['Mechanical context and field acceptance','User-present listening and interruption',
'Sustained real conversation latency and frame timing','Speaker/visual attribution and visual Q&A']}
(HERE/'PROGRESS.json').write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding='utf-8')
first=[r['result']['first_ms']['audio'] for r in voice['checks'] if r['name'] in ('actual_public_asr_llm_tts_receive','actual_recovery_next_turn')]
text=f"""# 玩偶集中自动验收记录（2026-10-27—28）

本轮恢复Windows语音/画面服务、修复远端画面提交被界面快照延后、修正动态帧率日志，并完成本轮集中自动验证。**整个玩偶尚未最终通过**：说话时严格帧间隔和响应时延目标仍未达到，机械绑定、声画归属/视觉问答和现场项目仍有缺口。最终核对时间：{v['checked_at_utc']}。

正式入口：{c['startup']}/launcher.py。当前boot：{v['boot']}。跟随与麦克风关闭、访客、音频IDLE_READY、音量70%且未静音。板卡在本轮开始前重启，旧1400/1422位置均不可当作当前读回；机械因精确board/boot/firmware/VART不匹配处于FAULT，没有执行MMIO或修改绑定。

## 本轮改变

1. Windows四项服务最初均未运行，板卡自动回退约8fps；复用既有后台启动器恢复，保留其他模型及D盘LLM存储，没有设系统自启动。
2. 远端RGB准备好后先交给现有单一native sink，再整理完整UI快照，避免快照开销额外延迟当前帧。取消代次、期限、最新帧和单sink保护继续生效。
3. 性能日志按实际8/16fps分组，记录对应长帧预算与超限次数，模式变化不混用帧间隔；保留历史over_187_5ms字段。预提交日志的public=0表示完整UI快照在提交之后，不表示其实际成本消失。
4. 仅修改board_avatar_worker.py和render_performance.py；其余Python及全部配置与上一正式版一致，GUI仍保留上一轮状态提示修复。

## 集中结果

| 范围 | 结果 |
| --- | --- |
| Windows隔离回归 | 50通过，包括慢快照不阻塞送显、取消/过期保护、分模式日志 |
| ARM专项 | 69通过；两组有重叠，不相加 |
| 实际待机送显 | {idle['fps']:.3f}fps，P95中位{idle['p95_ms']:.2f}ms，P99中位{idle['p99_ms']:.2f}ms；原门槛通过 |
| 静音真实PCM与口型 | {spoken['native_fps']:.3f}fps，P95中位{spoken['p95_ms_median']:.2f}ms，P99中位{spoken['p99_ms_median']:.2f}ms；嘴型/PCM变化及原音量恢复通过 |
| 严格SPEAKING 16fps观察门槛 | {'通过本次短样本，非持续真人对话证明' if speech_gate else '本次短样本未通过，不能宣称稳定16fps'} |
| 暂停/继续/取消 | 暂停时PCM停止推进、继续后恢复、取消回到IDLE_READY；取消至空闲{s['pause_resume_cancel']['cancel_to_idle_seconds']:.3f}秒 |
| 取消后新一轮 | 启动成功并再次取消到空闲 |
| 真实公开录音ASR→LLM→TTS | 七项通过，完整接收/CRC、取消、释放占用、下一轮恢复与音频前端均完成 |
| 两轮首PCM | {first[0]/1000:.3f}秒、{first[1]/1000:.3f}秒，非声学延迟，未达1秒目标 |
| 实际UI断线与恢复 | 本任务画面服务停止后本地{outage['local_fallback_fps']:.3f}fps、{outage['changing_local_preview_images']}张变化预览；恢复16fps，UI进程不变 |
| 最终服务/入口核对 | 四项服务ready；{v['component_hashes_verified']}项组件哈希一致；主屏与设置页截图检查通过且恢复原页面 |
| 机械 | FAULT保护保持；没有恢复参考、运动或越过绑定检查 |

静音前同台词基线约{before['speaking']['native_fps']:.3f}fps/P95 {before['speaking']['p95_ms_median']:.2f}ms/P99 {before['speaking']['p99_ms_median']:.2f}ms。均为短样本、窗口分位数中位数，不是全轮合并分位数；不以一次改善证明长期性能。native提交也不是面板光学扫描测量。公开录音测试只接收PCM、不开麦、不播放、不发送播放ACK，不创建个人档案。

首次部署因就绪超时回退，保留deployment_first_timeout.json和startup_failure.json。重试补充诊断并把有界初始化等待从115秒调整到150秒，独立300秒守护和原性能/空闲/机械保护条件保持；后续提交结果见layout_deployment.json。

最终收集器首次仅查看当前日志，未找到先前说话记录；核对当前进程公开的日志路径后，确认记录已正常轮转到.jsonl.1。收集器现同时读取同一进程的当前及轮转文件，保留原有说话阶段断言，未放宽验收。设置页截图瞬时帧率包含页面切换/故障回退之后的窗口，不能作为稳定性能结论。

## 最后一次现场验收

待机械精确上下文恢复且用户在玩偶旁，再集中完成：
- 正常对话、停顿续说、说话时插话/取消，检查听感和回应关联；
- 选档与返回访客、记忆归属、更正/遗忘，确认不会串人；
- 多人/背景声场景、视觉目标确认、声画归属与视觉问答；尚未实现或未通过项不能勾选完成；
- 机械参考与限位核对通过后再验实体跟随；当前FAULT不允许运动；
- 较长时间连续实聊，观察声音、帧间隔、恢复能力和温度/负载。

本轮没有请求逐项人工确认，也没有提前开启麦克风或恢复运动。等待心跳此前已删除，本轮没有创建。

## 证据与接续

[真实语音](live_voice_acceptance.json)、[静音/控制](muted_speech_probe.json)、[实际断线恢复](live_ui_outage.json)、[四项服务](windows_health_final.json)、[最终状态及分阶段日志](final_state.json)、[主屏](native_screen.png)、[设置页](native_settings.png)、[源码包](source_and_evidence.zip)、[清单](SOURCE_MANIFEST.json)。

后续先读最新AGENTS和本轮PROGRESS，核对实际入口、boot和设备状态。候选只替换原画面任务32z覆盖，上一入口保存在stage/previous_override.conf；回退需先确认空闲、监听/跟随关闭，只恢复该覆盖，保留其他覆盖及机械保护。不能直接重跑已提交的部署脚本。模型数据仍D盘；无权重/缓存复制、无密钥/录音/数据库打包。
"""
(HERE/'README.md').write_text(text,encoding='utf-8')
project=HERE.parents[1];marker='<!-- consolidated-interaction-20261027 -->'
entry=f"""{marker}
- 最新正式根{c['stage']}。报告deliverables/2026-10-27_final_interaction/README.md：恢复Windows服务，远端RGB先送显后UI快照、按实际fps记录性能；50 Windows/69 ARM专项互有重叠，实际待机16fps、静音PCM/暂停恢复取消/新轮与公开录音真实链路通过。SPEAKING严格门槛：{speech_gate}，不能当长期真人验收。
- 当前boot {v['boot']}，机械FAULT为精确board/boot/firmware/VART不匹配，no MMIO，位置null；禁止按旧boot或旧1400/1422更新绑定、恢复运动。跟随/麦克风关闭、访客、音量70恢复，其他模型与D盘存储保持。用户要求最后集中验收，全部项目尚未完成；现场听音插话/机械/声画归属/视觉问答与长稳仍待处理。

"""
path=project/'AGENTS.md';old=path.read_text(encoding='utf-8');assert marker not in old;path.write_text(entry+old,encoding='utf-8')
path=project.parent/'语言模型分析/README.md';old=path.read_text(encoding='utf-8')
path.write_text(marker+'\n[玩偶集中自动验收与待验事项](../语音共享文件/deliverables/2026-10-27_final_interaction/README.md)：软件回归、真实公开录音链路、静音PCM/暂停取消恢复完成；机械因重启绑定不匹配保持FAULT，整个玩偶尚未最终通过。\n\n'+old,encoding='utf-8')
names=['README.md','PROGRESS.json','candidate.json','baseline_candidate.json','candidate_initial.json',
'candidate_source/tools/board_avatar_worker.py','candidate_source/tools/render_performance.py',
'test_remote_handoff.py','run_tests.py','prepare_candidate.py','deploy_candidate.py','verify_board.py','muted_acceptance.py',
'baseline_speech.py','collect_final.py','finish_report.py','live_voice_acceptance.py','windows_health.py',
'capture_board.py','capture_settings.py','outage_probe.py','live_ui_outage_remote.py','live_ui_outage.json','outage.log','performance_diagnostic.json','tests.xml','tests_final.log','board_focused.json','baseline_speech.json',
'muted_speech_probe.json','live_voice_acceptance.json','final_state.json','layout_deployment.json',
'deployment_first_timeout.json','startup_failure.json','native_screen.png','native_avatar.jpg','native_settings.png','windows_health_final.json']
manifest={}
for name in names:
 data=(HERE/name).read_bytes();assert len(data)<2_000_000,name
 manifest[name]={'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)}
(HERE/'SOURCE_MANIFEST.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
with zipfile.ZipFile(HERE/'source_and_evidence.zip','w',zipfile.ZIP_DEFLATED) as z:
 for name in names+['SOURCE_MANIFEST.json']:z.write(HERE/name,name)
with zipfile.ZipFile(HERE/'source_and_evidence.zip') as z:assert z.testzip() is None
print(json.dumps(status))

