"""Record recovered services and the separate protected mechanical state."""
import datetime,hashlib,json
from pathlib import Path
from recovery_common import H,P,read,save
verified=read('verification.json');assert verified['status']=='PASS'
baseline=read('baseline.json');motion=read('motion_binding_audit.json');cache=read('cache_retention_verification.json')
database=read('database_verification.json');assert cache['status']=='PASS'
assert not (H/'PROGRESS.json').exists(),'Inspect completed recovery before repeating'
probe=read('voice_probe.json');assert probe['status']=='PASS'
for row in probe['checks']:
 for key in ('first_clause_text','conversation_context'):row.get('timing',{}).pop(key,None)
probe['text_diagnostics_omitted']=True;save('voice_probe.json',probe)
resolution={'status':'RESOLVED_PRESERVING_PARALLEL_UPDATE','initial_receipt':'recovery.json',
 'initial_guard_failure':'Concurrent board change: actual_config',
 'initial_receipt_sha256':hashlib.sha256((H/'recovery.json').read_bytes()).hexdigest(),
 'running_config':verified['board']['running_config'],'configured_next_start':verified['board']['configured_next_start'],
 'same_running_components':verified['board']['next_start_pins_equal_running'],
 'proofs':['running_entry.json','verification.json'],'board_restart_performed':False}
save('recovery_resolution.json',resolution)
board=verified['board'];actual=motion['actual'];expected=motion['expected']
cache_hits=sum(row['tts_cache_hits'] for row in probe['checks'])
timings=' / '.join(f"{row['first_pcm_ms']/1000:.3f}秒" for row in probe['checks'])
body=f'''# Windows现有服务恢复与板卡环境核对

现有r9服务已恢复并完成本轮核对，源码指纹仍为 `{verified['fingerprint']}`。七类服务就绪，两轮真实板端语音请求完整返回。转轴因重启后的四项平台不匹配继续保护停用，未解除保护或执行运动；本次不是整机最终验收或板端功能迁移。

## 服务恢复

恢复前Windows语音、前端、动画、视觉和记忆端口没有监听，Windows本次启动时间为 `{baseline['windows']['last_boot']}`，晚于r9交付。通过原有 `start_voice.ps1` 恢复后台进程；既有Ollama端口复用，没有停止其他模型、修改源码或移动LLM数据。

| 服务 | 端口 | 结果 |
| --- | --- | --- |
| ASR | 8791 | 原协议就绪 |
| 对话/OmniVoice/对话记忆 | 8792 | r9精确源码、依赖就绪 |
| GTCRN/Silero前端 | 8795 | 二进制健康协议通过 |
| Windows CPU画面合成 | 8796 | 二进制健康、原资源版本通过 |
| CPU视觉模型 | 8810，本机 | health正常 |
| 外设/视觉时间轴/声纹 | 8812，本机 | device-timeline-v2、ECAPA就绪 |
| 项目Ollama | 11435，本机 | 原服务复用、模型在线 |

完整检查见[endpoints](endpoints.json)。板端已自动重新选中远端画面合成，目标16fps、回退8fps，错误字段为空；短时画面统计仅为观察，不能算说话或严格16fps验收。

使用当前板端既有ARM客户端发送两份公开16kHz录音，经过真实ASR/27B/OmniVoice16，网络PCM样本和哈希均核对通过，首PCM {timings}。本次共有{cache_hits}次TTS缓存命中，不作为新的优化A/B或稳定延迟保证。没有开麦、实体播放、成功播放ACK或持久测试对话。见[语音探针](voice_probe.json)。没有修改业务源码，因此复用r9此前355项回归，本轮新增的是恢复后的健康和实机链路核验，没有把旧数量再累加。

## 板端实际入口与并行更新

运行中的UI仍为PID `{board['ui_pid']}`，从 `{board['running_config']}` 启动，实际根 `{board['runtime']}`；相机PID `{board['camera_pid']}`，279项组件哈希匹配。本次没有重启UI或相机。

启动器执行结束时，首次收尾校验发现systemd配置变更，拒绝按旧配置继续确认，原结果保留在[recovery](recovery.json)。随后核对 `/proc/<MainPID>/cmdline`，确认并行更新只是把下次启动入口改到 `{board['configured_next_start']}`；当前运行进程、实际根及279组件没有变化。该更新完整保留，解决记录见[recovery_resolution](recovery_resolution.json)。今后须分别核对当前进程和下次启动unit，不能把daemon-reload后的unit配置直接当作当前运行入口。

## 转轴保护原因

| 校验项 | 当前 | 驱动要求 |
| --- | --- | --- |
| boot | `{actual['boot']}` | `{expected['boot']}` |
| FDT SHA256 | `{actual['fdt_sha256']}` | `{expected['fdt_sha256']}` |
| FPGA镜像 | `{actual['firmware']}` | `{expected['firmware']}` |
| VART | benchmark-b4096.xclbin | aura-visual-servo-b4096-wide-v1.xclbin |

架构、板卡身份、FPGA operating和发布清单校验通过，所需已安装固件/驱动文件哈希保持；但上述四项不匹配，因此转轴显示FAULT / no MMIO。当前要求是 **wide-v1** 联合固件，不能沿用早期窄范围v1的恢复方案。

本次只读取驱动源码、配置和内核元数据，没有导入驱动、访问寄存器、重编程FPGA、更新绑定、填写标定或发送运动指令。当前脉宽读回为null，不能恢复历史1604µs或把名义1500µs当实测位置。最初读取fpga_manager的firmware属性被内核拒绝，已记录；最终镜像以驱动实际读取的 `/proc/device-tree/fpga-full/firmware-name` 核对，未写入任何sysfs属性。见[motion_binding_audit](motion_binding_audit.json)、[motion_platform](motion_platform.json)。

后续恢复转轴须与正在使用DPU的相机/并行任务协调，成套恢复匹配的wide固件、设备树和VART，重新核对本次boot及原发布/观察证据，再做现场受控位置、STOP与机械验收。不能只改boot/FDT字符串绕过校验；本次请求的环境核对不等于机械复机授权。

## 数据与最终状态

独立隐藏WMI从真实私有文件视图备份当前数据库，没有回滚旧数据。原144会话/276轮及相关事实/权限/来源表逐表SHA保持，183条视觉历史及其修订/游标、声纹源表同样保持。实时观察缓存从188降为187：唯一移除行已超过原86400秒保留期，其余187行逐行完全相同。这是原缓存策略在召回时自动清理，与长期视觉历史分离。

全表严格相等检查因这1条过期缓存变化而失败，原[database_verification](database_verification.json)结果保留；随后独立证明了只有过期行移除、保留行完全相同及所有历史源表不变，见[cache_retention_verification](cache_retention_verification.json)。没有人工删除、放宽机械校验或恢复旧快照，私有数据库/模板/备份未导出到共享目录。

最终监听、麦克风、跟随关闭，音频IDLE_READY，转轴保护停用。原有模型进程全部保持，LLM路径配置未变，数据仍在D盘。本次没有创建计划任务、自启动或心跳。当前可由用户在原界面开启语音现场复测；连续说话间隙、稳定延迟、短词唤醒、声画归属、声纹现场标定与整机长稳仍待后续。核验见[verification](verification.json)，状态见[PROGRESS](PROGRESS.json)。
'''
(H/'README.md').write_text(body,encoding='utf-8')
(H/'CONTINUE.md').write_text(f'''# 接续约束

本轮恢复现有 {verified['revision']}，没有新部署或改指纹。以verification.json、endpoints.json、voice_probe.json和README为运行状态证据。r9功能与性能报告仍在../2026-10-29_chat_latency；不要重复旧部署或覆盖其数据。

当前板卡boot {board['boot']}，UI1296/相机1333，实际运行配置{board['running_config']}，根{board['runtime']}，279组件匹配。并行任务将下次启动unit配置改为{board['configured_next_start']}，运行进程尚未切换；必须读/proc/MainPID/cmdline及systemd两者，不能回退该并行更新。以后每次动态重查，本文不是永久绑定。

转轴FAULT、脉宽null、跟随/监听/麦克风关闭。当前加载benchmark固件，驱动要求wide-v1，boot/FDT/VART也不匹配；完整对照motion_binding_audit.json。所需安装文件哈希保持不代表已经加载或运动可用。只读核对没有导入驱动/MMIO/改绑定/切固件/运动，不能只写新boot或恢复旧1604脉宽。后续复机必须协调DPU使用者和并行任务，成套恢复正确wide固件与VART、核验本次环境与实体位置/STOP；保留机械保护。

本轮当前基线是144会话/276轮、188实时缓存/183视觉历史，不能按旧77/73或143/273覆盖。恢复后实时缓存187：原24小时策略自动清理1条过期记录，cache_retention_verification.json严格证明，其余源表SHA不变。database_verification.json初次全表相等失败保留，不能删掉该记录或称所有表逐字节相同。真实私有库仍用独立隐藏WMI视图，备份留AppData，不复制身份数据或权重到E盘。

恢复原启动器成功后的首次收尾因并行unit改变而拒绝旧入口确认，recovery.json保留原失败；recovery_resolution.json和verification.json给出后续实际进程核对结果。不应为清掉这条历史记录重跑恢复/结束脚本。业务源码无改动，其他模型运行和D盘LLM存储保持，无新自动任务；板端迁移继续暂缓。
''',encoding='utf-8')
progress={'status':'WINDOWS_SERVICES_RESTORED_PLATFORM_AUDITED','complete':True,
 'scope':'restore existing Windows services and audit current board environment',
 'revision':verified['revision'],'fingerprint':verified['fingerprint'],'source_changed':False,
 'services_ready':7,'actual_arm_voice_checks':2,'first_pcm_ms':verified['first_pcm_ms'],
 'motion_restored':False,'motion_state':'PROTECTED_DISABLED','motion_blockers':verified['motion_blockers'],
 'original_dialogue_visual_archive_speaker_sources_unchanged':True,'expired_live_cache_rows_removed':1,
 'listening':False,'microphone_open':False,'automatic_following':False,'board_restarted':False,
 'parallel_next_start_update_preserved':True,'models_stopped':False,'board_migration':False,
 'full_project_complete':False,'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
save('PROGRESS.json',progress)
marker='windows-services-recovered-20261029'
note=f'''<!-- {marker} -->
- 最新运行恢复与重启后核对：deliverables/2026-10-29_service_recovery/README.md、CONTINUE.md、PROGRESS.json。Windows七类服务已恢复现有r9，源码指纹{verified['fingerprint']}不变；两轮实际ARM语音请求通过，无开麦/实体播放/成功ACK。原模型进程及D盘LLM存储保持，未新建自启/计划任务/心跳。
- 当前board boot {board['boot']}，UI1296/相机1333。实际运行仍{board['running_config']}，运行根{board['runtime']}、279组件匹配；并行任务改了下次启动配置{board['configured_next_start']}，已保留。必须同时读/proc/MainPID/cmdline与systemd，不能仅把daemon-reload的新unit当实际运行入口，不能回退并行更新。
- 板卡重启后为benchmark FPGA/VART，实际驱动要求aura-visual-servo-b4096-wide-v1，boot/FDT/固件/VART四项不匹配，转轴FAULT保护停用/脉宽null，无MMIO。下方旧READY1604/旧boot已是历史，不能照抄恢复；本轮只核对，不改绑定、不切固件、不运动。监听/麦克风/跟随关闭。
- 当前144会话/276轮、183视觉历史及声纹源表SHA保持。实时缓存188→187为原24小时策略自动移除1条过期记录，其余行完全相同；严格相等初次失败及独立过期证明均保留。不可称所有表未变，也不能恢复旧77/73或143/273。真实私有库仍用隐藏WMI，备份留AppData。
- 本轮服务恢复和核对完成，机械未复机，整机仍未最终验收；用户先完善Windows对话/记忆、迁移后置的方向保持。后续机械须协调DPU与并行任务并成套核对wide固件/VART/发布与实体位置，禁止只改boot放宽保护。
<!-- /{marker} -->

'''
path=P/'AGENTS.md';text=path.read_text(encoding='utf-8');assert marker not in text;path.write_text(note+text,encoding='utf-8')
for path,url in [(P/'README.md','deliverables/2026-10-29_service_recovery/README.md'),
 (P.parent/'语言模型分析/README.md','../语音共享文件/deliverables/2026-10-29_service_recovery/README.md')]:
 text=path.read_text(encoding='utf-8');assert marker not in text
 intro=f'<!-- {marker} -->\n[最新：Windows服务恢复与板卡环境核对]({url})：现有r9七类服务恢复，两轮板端真实语音通过；原数据、模型与并行启动优化保留。转轴因boot/FDT/benchmark固件/VART与wide驱动不符保护停用，未复机。当前监听关闭，迁移暂缓；整机尚未最终验收。\n<!-- /{marker} -->\n\n'
 path.write_text(intro+text,encoding='utf-8')
print(json.dumps({'status':progress['status'],'services_ready':7,'voice_checks':2,'motion_restored':False,'full_project_complete':False}))
