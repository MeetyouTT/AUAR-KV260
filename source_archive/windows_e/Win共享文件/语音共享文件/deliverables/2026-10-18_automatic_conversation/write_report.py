"""Archive this release and publish evidence-based acceptance notes; no model files."""
import hashlib
import json
from pathlib import Path
import zipfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
ANALYSIS=ROOT.parent/'语言模型分析'
def read(name):return json.loads((HERE/name).read_text(encoding='utf-8'))
candidate=read('candidate.json');deployment=read('deployment.json');snapshot=read('current_state.json')
live=read('live_playback.json') if (HERE/'live_playback.json').exists() else {}
listening=read('listening.json') if (HERE/'listening.json').exists() else {}
probe=read('preference_27b_probe.json') if (HERE/'preference_27b_probe.json').exists() else {}
post_fix=((HERE/'live_playback.json').exists() and (HERE/'memory_reload_ready.json').exists()
          and (HERE/'live_playback.json').stat().st_mtime_ns>(HERE/'memory_reload_ready.json').stat().st_mtime_ns)
first_retest=read('live_memory_first_retest.json') if (HERE/'live_memory_first_retest.json').exists() else {}
preference_loaded=snapshot['pc_health'].get('session_preference_memory',{})
stop_check=read('final_stop_check.json') if (HERE/'final_stop_check.json').exists() else {}
passed=(live.get('status') in ('PASS_TWO_AUTOMATIC_ROUNDS_AND_USER_STOP','PASS_ONE_AUTOMATIC_ROUND_AND_USER_STOP')
        and post_fix
        and listening.get('memory_fix_retest_accepted') and listening.get('stop_accepted')
        and listening.get('prefix_capture_accepted')
        and first_retest.get('status')=='PASS_TWO_AUTOMATIC_ROUNDS_AND_USER_STOP'
        and preference_loaded.get('parser_revision')==2 and preference_loaded.get('sessions_with_preference',0)>=1
        and probe.get('status')=='PASS_ORIGINAL_27B_AGED_OUT_PREFERENCE_RECALL')
status='PASS_AUTOMATIC_ROUNDS_MEMORY_LISTENING_AND_STOP' if passed else 'DEPLOYED_LIVE_ACCEPTANCE_IN_PROGRESS'
assert snapshot['source_hashes']==candidate['files']
sources=list(candidate['files'])+['aura/tests/framework/test_automatic_conversation.py','aura/tests/framework/test_board_avatar_worker.py',
    'aura/common/session_memory.py','aura/tools/board_model_host.py','aura/tools/voice_channel_source.py',
    'aura/tests/framework/test_session_memory.py']
source_hashes={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in sources}
with zipfile.ZipFile(HERE/'verified_source.zip','w',zipfile.ZIP_DEFLATED) as archive:
    for name in sources:archive.write(ROOT/name,name)
    archive.writestr('source_manifest.json',json.dumps(source_hashes,ensure_ascii=False,indent=2))
(HERE/'source_manifest.json').write_text(json.dumps(source_hashes,ensure_ascii=False,indent=2),encoding='utf-8')
rows=[]
for row in live.get('rounds',{}).values():
    if row.get('turn',{}).get('audio_complete') and row.get('ack',{}).get('committed'):
        turn=row['turn']
        rows.append({'request_id':row['request_id'],'capture_id':row.get('capture_id'),
                     'matching_playback_ack':True,'request_to_answer_seconds':turn.get('request_to_answer_seconds'),
                     'history_messages':turn.get('server_metrics',{}).get('timing',{}).get('history_messages')})
summary={'status':status,'runtime':deployment['runtime'],'backup':deployment['backup'],
         'automatic_turn_taking':True,'full_duplex':False,'voice_barge_in':False,
         'model':'aura-qwen3.8-27b-abliterated:iq4_xs','tts':'omnivoice','tts_steps':16,
         'endpoint_silence_ms':700,'minimum_speech_ms':180,'pre_roll_ms':200,'rearm_guard_ms':500,
         'pc_main_tests':{'passed':65,'skipped':1,'deselected':1,'subtests_passed':26},
         'pc_worker_followup':{'passed':7,'overlaps_main_batch':True},'board_linux_tests':{'passed':53},
         'pc_memory_regression':{'passed':70,'subtests_passed':26,'overlaps_other_batches':True},
         'preference_probe_status':probe.get('status'),
         'live_observation_after_memory_reload':post_fix,
         'postfix_preference_state':preference_loaded,'stop_start_retest_status':first_retest.get('status'),
         'final_stop_check':{'status':stop_check.get('status'),'explicit_agent_cleanup':stop_check.get('explicit_agent_cleanup')},
         'live_status':live.get('status'),'listening':listening,'completed_observed_rounds':rows,
         'source_hashes_match_deployment':True,'source_manifest':source_hashes,
         'camera_same_pid_as_deployment':snapshot['camera']['pid']==deployment['camera_before']['pid'],
         'boot_unchanged':snapshot['boot_id']==deployment['boot_before'],
         'acoustic_onset_measured':False,'stable_three_second_claim':False,
         'models_or_private_keys_in_source_archive':False}
(HERE/'verification_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
outcome=('已通过真实自动接话、结束后重新开始仍记得绿色、用户听音和结束停止验收；原27B已验证颜色偏好超出四轮仍可召回。' if passed else
         '自动轮转已部署且初次听音通过；现场随后发现四轮以外颜色记忆丢失，修复已载入并通过自动测试，修复后的用户复测仍待核对。')
latency='、'.join(f"{row['request_to_answer_seconds']:.3f}秒" for row in rows[:2] if row.get('request_to_answer_seconds') is not None) or '以live_playback.json为准'
report=f'''# 自动轮流对话实现与验收（2026-10-18）

{outcome}

## 实际行为

点击一次“开始对话”，直接说话；检测到至少180ms有效语音后，停顿约700ms自动提交。保留200ms前导声音，闲置监听使用有界缓冲，不持续积累整段PCM。每段最长约20秒；录音、网络、播放或记忆确认出错时停止对话并显示错误，需手动重新开始。

ASR、原27B/IQ4_XS和OmniVoice16仍在电脑端。生成及播放期间关闭麦克风；完整播放并收到本轮匹配的记忆提交ACK后，等待500ms尾音保护，再自动聆听下一轮。按“结束对话”或取消会关闭监听、取消当前请求和播放；过期完成事件不能重新开启会话。

## 现场发现并修复的记忆缺口

第一轮连续聊天已正确记住绿色，但用户随后确认“停止对话，第二轮就不记得我喜欢绿色”。实际记录显示已经聊了七轮，后续仍带8条历史消息，原因是原来只保留最近四轮，颜色那轮被挤出，并非结束按钮清空历史。失败证据保留为memory_failure_state.json及listening.json，最初轮转证据保留为live_automatic_initial.json，不能用初次绿色成功掩盖后续失败。

现增加一个有界的、同boot/session的颜色偏好锚点：只从明确的第一人称颜色陈述中提取，并在匹配完整播放ACK后保存对应原始问答。被取消、未播完、错误ACK、疑问、引述、第三人称、假设或任意附加指令均不写成偏好。新颜色覆盖旧颜色，明确不再喜欢该颜色或要求忘记颜色偏好时移除锚点；不同会话隔离，32个会话淘汰时同步清理。

保留原四轮短期历史；旧颜色信息被窗口挤出时，在原2048上下文预算内额外带入原始确认问答（2条），27B自由生成回复。没有新增模型调用、固定颜色答案、扩大上下文或修改系统人设提示；预算不足则不额外注入，记录context_budget。当前只覆盖明确颜色偏好，不宣称任意事实、人名或长期记忆均已完成。结束/开始保留同一会话，但电脑8792服务重启、板端UI重建会话或boot改变均会清空；没有将偏好落盘。

这版是自动轮流交谈。尚不支持播放时凭声音打断、双向同时说话或回声消除。700ms停顿适合当前第一版，尚未覆盖口音、长犹豫、远场、电视声及噪声的系统测试。

## 验证及时间口径

- 电脑端主批次65项通过，1项Linux生命周期检查跳过、1项POSIX权限检查排除，26个子用例通过；后续worker批次7项通过，与主批次有重叠，不能相加当成独立测试数量。
- KV260 Linux最终53项全部通过，包含真实文件锁/子进程录音生命周期、POSIX权限、静音端点、有界缓冲、短噪声、保留首音、等待播放ACK、取消和过期结果保护。GTK/GStreamer资源检查通过。
- 记忆修复电脑端70项及26子用例通过（与前面协议测试有重叠）。原27B实际文字探针：重放7轮已确认问答后仍答对绿色；偏好改蓝色并再插入5轮后仍答对蓝色；带“你好啊请记住”的现场真实转写再插入5轮后仍答对绿色。该探针使用受控播放ACK重放、实际27B自由生成，不计作新话筒录音/板端听音。
- 当前真实观测状态：`{live.get('status','尚无记录')}`；此文件属于{'修复后' if post_fix else '修复前'}观测。最新用户反馈及修复后复测是否通过以listening.json和verification_summary.json为准。
- 最后一次带“你好啊请记住”的真实转写及匹配完整播放ACK已记录；健康接口parser_revision=2、独立偏好会话计数={preference_loaded.get('sessions_with_preference','待核对')}。用户确认“已说完并结束，回答清楚自然”；结束复核状态={stop_check.get('status','待核对')}，助手是否发送收尾取消命令={stop_check.get('explicit_agent_cleanup','待核对')}。重新开始后绿色召回及自然听音另保留在live_memory_first_retest.json和listening.json。
- 本轮被完整观测、匹配播放ACK的样本，从自动录音提交到正式回答软件播放启动记录为：{latency}。这不包括说话时间和700ms端点判定，亦非外部麦克风测得的声学起音；不是稳定3秒保证。
- 原27B、量化、生成设置、五个延迟开关、OmniVoice16和视觉YOLOX/DPU配置保持，板端源码指纹匹配。部署切换当时相机PID一致，随后另观测到相机服务停止/启动，PID变为199373，来源未确认；当前模型SHA与DPU arch不变且健康，boot未变，不能宣称相机进程全程未变。之后也观测到UI服务另一次停止/启动，路径未换，详情ui_external_restart.json；这种服务重建会更换会话、清空进程内记忆，不能与点击结束/开始等同。
- 额外自由聊天中仍出现专有名词误听及“打错字”式回复，泛化ASR和语音语境表达仍需完善；本轮自动轮转验收不代表这些问题已解决。原界面底部的远端“语音主机待接入”与本地已连接语音通道尚有显示口径不一致，也列为后续界面完善项。

## 运行与回退

活动板端目录：`{deployment['runtime']}`。

旧运行目录：`{deployment['old_runtime']}`。

部署前的systemd unit与启动配置：`{deployment['backup']}`。只切换aura-avatar-ui.service，未改相机服务、DPU或FPGA。

如需恢复之前手动开始/停止录音的正式版本，在板端先结束会话，再执行：

```sh
systemctl stop aura-avatar-ui.service
cp {deployment['backup']}/aura-avatar-ui.service /etc/systemd/system/aura-avatar-ui.service
systemctl daemon-reload
systemctl start aura-avatar-ui.service
```

原目录、资源和历史证据均保留，不删除模型。回退后应检查8783/api/state的IDLE_READY和相机8790/health。正常启动仍使用现有aura-avatar-ui.service；重启后默认停止，不自行开启麦克风。只设置源码automatic_turns=false并不等于已更新板端，后续发布必须同步启动器源码指纹。

颜色记忆修复仅在电脑端加载，不需要重启KV260。电脑端回退需在结束会话后恢复本目录before/aura/tools下的board_model_host.py、voice_channel_source.py，再精准停止8792服务及其OmniVoice子进程，使用原start_background_models.ps1重新启动；不要停止ASR8791、项目Ollama11435或全局Ollama11434。新增session_memory.py无入口时可保留，不做删除。memory_reload_before.json、memory_reload_ready.json记录了本次重载范围及实际加载版本。重启会清空进程内历史与颜色偏好。

## 证据与交付

- `candidate.json`、`tests_board.log`：最终隔离候选、53项Linux测试和资源检查。
- `tests_pc.log`、`tests_pc.xml`、`tests_worker_pc.log`：电脑端测试。
- `deployment.json`、`current_state.json`、`live_screen.png`：实际部署、服务健康、界面与源码指纹。
- `live_playback.json`、`listening.json`、`verification_summary.json`：新录音、多轮状态转换、匹配ACK、听音和停止结果。
- `memory_failure_state.json`、`live_automatic_initial.json`：修复前缺口和初次轮转证据。`tests_memory.log`、`preference_27b_probe.json`：修复回归与原27B文字验证。
- `before/`：改前源码。`verified_source.zip`：本版生产变更与相关测试，带独立SHA256清单；不含模型、虚拟环境或SSH私钥。
- 首次导入/Windows权限/ARM状态发布时序失败日志保留，最终结论只依据最终通过日志。测试修复将worker结果与随后状态发布分别等待，避免假设两者原子发布。

大语言模型数据仍在D:/AIModels；本目录只存代码、设计、配置和运行证据。候选CosyVoice声线本轮没有切入正式服务。
'''
(HERE/'README.md').write_text(report,encoding='utf-8')
(ANALYSIS/'自动轮流对话实现与验收_20261018.md').write_text(report.replace('## 证据与交付','完整原始证据位于 `E:/Win共享文件/语音共享文件/deliverables/2026-10-18_automatic_conversation`。\n\n## 证据与交付'),encoding='utf-8')
def leading_note(path,note):
    text=path.read_text(encoding='utf-8')
    begin='<!-- automatic-conversation-20261018 -->';end='<!-- /automatic-conversation-20261018 -->'
    if begin in text:
        start=text.index(begin);finish=text.index(end,start)+len(end)
        text=text[:start]+text[finish:]
    first,_,rest=text.partition('\n')
    path.write_text(first+'\n\n'+begin+'\n'+note+'\n'+end+'\n'+rest.lstrip('\r\n'),encoding='utf-8')
leading_note(ROOT/'README.md',f'> **2026-10-18 自动轮流对话第一版：** {outcome} 点击一次开始、停顿自动提交、播完确认记忆后继续听，结束按钮取消整轮。原27B/OmniVoice16与视觉保持；不含声音打断和全双工。[实测、范围与回退](deliverables/2026-10-18_automatic_conversation/README.md)。最新活动板端目录以本轮部署记录为准。')
leading_note(ROOT/'AGENTS.md',f'- 2026-10-18 自动轮流对话最新活动目录为 `{deployment["runtime"]}`，取代旧stream-playback活动路径。{outcome} `automatic_turns=true`；700ms静音端点、200ms前导，录音与生成播放互斥，匹配完整播放ACK后500ms再听；结束/取消禁止过期事件重启。PC主批次65通过/26子用例、worker后续7项（重叠）、Linux53项通过；颜色记忆修复最终70项/26子用例通过。board_model_host增加同boot/session的明确颜色偏好，完整播放ACK后确认、超出原四轮时预算内补原问答2条，问候前缀parser_revision=2，支持更改/否定/忘记；不新增模型调用，不修改系统人设提示，尚非通用或落盘长期记忆，8792/UI重建会清空。原27B/IQ4_XS/OmniVoice16与视觉模型配置保持；相机后来另有停止/启动，最终PID应动态查8790，不能称全程相同，另有UI服务重建记录。没有全双工/声音打断，不宣称稳定3秒。证据与回退入口 `deliverables/2026-10-18_automatic_conversation/README.md`；以前验收ZIP指纹不能当成本版源码清单。')
leading_note(ANALYSIS/'README.md',f'## 最新：自动轮流对话\n\n[自动轮流对话实现与验收](自动轮流对话实现与验收_20261018.md)：{outcome} 点击一次开始、停顿自动提交、完整播放及记忆确认后继续聆听；保持原27B与OmniVoice16。尚不支持声音打断或全双工，也未达到稳定3秒。')
print(json.dumps({'status':status,'observed_rounds':len(rows),'source_archive_files':len(sources),'camera_preserved':summary['camera_same_pid_as_deployment']},ensure_ascii=True))
