"""Current deployment handoff, bounded evidence and source identities."""
import datetime,hashlib,json,shutil,zipfile
from pathlib import Path
H=Path(__file__).resolve().parent;P=H.parents[1];A=P/'aura';W=P.parent
def read(name):return json.loads((H/name).read_text(encoding='utf-8-sig'))
v=read('verification.json');assert v['status']=='PASS';c=read('candidate.json');db=read('database_verification.json')
native=read('native_ipc_comparison.json');muted=read('muted_live_probe.json');outage=read('live_ui_outage.json')
counts=db['databases']['conversation']['counts'];observations=db['databases']['observation']['counts']
original_continue=H/'CONTINUE.pre_deployment.md'
if not original_continue.exists():shutil.copy2(H/'CONTINUE.md',original_continue)
report=f'''# 句中断续与动作素材：已部署，自动验收通过

最后核对：{v['checked_utc']}。本轮软件部署和自动验证完成，真人听感待复测，整机未最终验收。

用户明确当前自打断已不再出现；本轮处理“声音断断续续、句子中间停顿”和“动作素材丰富性没体现”。没有修改插话识别阈值、27B、OmniVoice声线/16步、记忆策略或机械绑定。

## 播放链路

现役音频worker原来在GLib供音线程同步print/flush，每秒输出状态及回声参考；接收管道背压可以直接阻塞供音。候选改为有界非阻塞IPC，合并状态、保留部分写入包的完整性及参考序号；内容PCM逐字节保持。过期参考不用于插话，出现参考间隙时仅退出本轮插话监视，保留当前播报并允许之后正常聆听，禁止回退原始能量触发。

受控ARM/GStreamer appsrc→fakesink、自建4096字节管道并施加240ms读端停顿，两版相同144000字节公开正弦PCM：

| 指标 | 原版 | 修复版 |
| --- | ---: | ---: |
| 最大供音间隔 | 199.98ms | 24.57ms |
| 超过80ms的供音间隔 | 9 | 0 |
| PTS缺口 | 180ms | 0 |

这是可复现背压路径的修复证据，不是用户原现场声学A/B。原生试验没有打开ALSA、麦克风或显示设备。首次fcntl常量导出失败的记录保留。

现役唯一界面另做约11.85秒公开缓存长句测试：先由UI及直接ALSA读回确认音量0/静音，再播放实际PCM。最大供音调度间隔18.28ms，缺料填静音0包、晚调度重排0次，20种变化画面，测试后音量70/未静音恢复。未打开麦克风，没有可听播报。见muted_live_probe.json。空闲启动时丢弃的13份过期参考在这轮测试中没有增长。

## 现有动作素材

此前RealtimeFacials把所有复用说话素材的完整身体替换成IDLE，开心、低落的身体动作因此被遮盖；每轮池游标又被重置，短回答来不及达到6秒轮换。

现在保留idle_normal、idle_present、talking_normal、talking_low四套已有身体，开心可出现原举手动作；同语义嘴池按对话代次稳定选择，长句仍保留原6秒轮换。嘴部始终按PCM绘制，包括静音闭口；眼层与嘴层使用当前身体的原39帧跟踪几何。点头、摇头、惊讶、疑惑素材保持原动作，不加入转轴动作或额外模型调用。没有新生成或下载位图。

visual_preview.png为四套真实资源离屏预览；actual_avatar.png为部署后现有界面的玩偶画面，未保存相机、人物或完整屏幕。资源manifest继续严格校验676项原资源，旧81fd快照完整保留。

## 验证范围

- 音频58通过、1个Windows平台跳过；15项真实素材像素/闭口/眨眼/短轮/取消检查通过；41项画面协议归属/取消/过期检查通过。组间不与历史总数累加。
- 原生ARM离屏192帧通过，四身体及4种动作保持；合成P95约97.27ms，适用于8fps回退预算，不能称板端稳定16fps。
- Windows前后各432帧离屏合成P95约4.008→4.035ms，未见明显额外开销；不是物理帧率。新版预热约3.10秒。
- 实际UI断开所属Windows8796后，界面PID保持、约{outage['local_fallback_fps']:.3f}fps本地回退、15种变化画面；恢复后接回16fps目标，最大显示年龄约146.35ms。无第二显示/音频sink。
- 说话观测约15.445fps、P95中位79.99ms、P99中位158.12ms，仍未通过严格16fps间隔目标。没有降低门槛，也不把本次声音修复称作长帧已解决。
- 七项Windows服务健康；现有其他模型与非8796服务PID全部保持，voice r9源码指纹不变。未卸载其他模型，LLM数据继续D盘。
- 独立隐藏WMI核对真实私有库，原始来源逐表严格相等：{counts['conversations']}会话/{counts['turns']}轮，视觉历史{observations.get('visual_timeline','见报告')}条及声纹来源保持；备份留私有目录，没有回滚旧库。

旧audio_tests.log、audio_tests_effective.log及原生准备失败记录保留；最终结果看audio_tests_verified.xml、visual_tests.xml、portrait_tests.xml和verification.json。FakeSource仅补现机已有get_property接口，原断言AST不变；原生appsrc满队列/无效值保护保留。

## 当前入口与状态

- Windows入口：项目start_portrait.ps1 → 本目录start_host.ps1；正常start_voice.ps1已指向aura/config/portrait_host.local.json。旧历史启动器/验证脚本不作为当前恢复入口。
- CPU画面revision：{c['revision']}，快照renderer_snapshot；其676项资源及项目源码SHA均严格校验。
- 板端实际根：{c['runtime']}；实际配置：{c['startup']}/config.json；279项绑定通过。
- UI监督器PID {v['board']['ui']['MainPID']}，相机PID {v['board']['camera']['MainPID']}及epoch不变。保留并行startup-speed启动器全部字节与参数，以及所有旧systemd覆盖；仅新增本次覆盖。
- 最终IDLE_READY，监听/麦克风/跟随关闭，音量恢复70/未静音。原benchmark/wide平台不匹配导致的机械FAULT保护保留，位置null；未MMIO、切固件、改boot绑定或启用运动。

## 集中真人复测

手动开启语音聆听后，不入镜呼叫“汐蓝”并让她说一段较长回答，先听句中是否仍断续；再用开心、安慰话题观察身体姿态与原有动作，最后在说话中提出新问题检查正常插话。请反馈断续是否消失及发生位置。此项没有代填通过；短词即时唤醒、声画归属、现场声纹、长帧及跨天长稳仍按原项目待验项管理。迁移继续后置。
'''
(H/'README.md').write_text(report,encoding='utf-8')
continuation=f'''# 当前接续：已部署，等待本版集中真人听音

先读README.md、verification.json、PROGRESS.json。不要按CONTINUE.pre_deployment.md的“尚未部署”继续重跑准备或切换。

现役板端根{c['runtime']}，配置{c['startup']}/config.json，279组件；CPU画面revision {c['revision']}；Windows语音仍r9/{v['voice_fingerprint']}。本轮只重启所属CPU8796和单板端UI；其他模型、相机进程/epoch、机械字节和已有systemd覆盖保留。

软件与自动验证已通过，听音/真人动作观感待用户反馈。当前监听、麦克风、跟随关闭；不得自动开麦、播放有声内容或启用运动。下一步按README最后的三项集中复测处理实际反馈，不重复无人测试来冒充真人验收。

任何后续变更都重新从/proc/MainPID/cmdline发现实际配置，核对279精确pin和当前pending unit；禁止只看daemon-reload后的unit。修改前两次确认IDLE/IDLE_READY、监听/麦克风false、跟随false且无活动运动，保护其他聊天的并行更新。新root采用startup/config.json布局以保持manual_live_config自己的校验路径。

保留原机械FAULT和null位置。board boot仍{v['board']['boot']}；benchmark FPGA/VART与wide驱动不匹配，禁止照抄旧boot/1604µs或“修正”绑定来恢复运动。LLM数据只在D盘，不卸载其他模型，不复制私有身份库、原始PCM/现场照片到E盘。

数据基线需每次重新通过独立隐藏WMI备份和对比，真实AppData视图与工具视图可能不同。当前153/311等仅本轮时点，不得覆盖用户后续新增资料。原始来源逐表严格相等；前一service_recovery的过期缓存解释属于旧轮，不套用来忽略本轮新变化。

正常重启画面用项目start_portrait.ps1或本目录start_host.ps1，只复用健康且PID/创建时间/启动命令匹配的所属8796。旧2026-10-27画面/2026-10-29_service_recovery脚本仍验证81fd历史revision，不能直接重跑覆盖本版。start_voice.ps1只检查新的canonical host config，其余语音启动行为保持。

回退必须协调两端，先读deployment.json/source_installation.json并再次核对实际入口、空闲、所有源SHA和无新并行更新。只撤销deployment.json记录的本次systemd覆盖，恢复原pending startup-speed入口，不删除其他覆盖；之后rollback_windows.py仅恢复本次记录的Windows源与原CPU入口。该脚本不是整套板端回退，禁止在新板端UI仍需要763d资源时单独执行。备份在source_backup，旧快照/旧发布完整保留；不回退记忆库或机械绑定。

音频参考出现永久gap时不能退回原能量判定；本次有界非阻塞上报不得改回GLib线程同步print。MAX_APPSRC_BYTES/current-level-bytes保护与PCM时钟/哈希/取消边界保留。空闲起步13份过期参考未在静音长句中增长；声音仍断续时优先检查audio_output与turn.completed中的供音间隔、缺料包、排队时长和IPC指标，不凭感受宣称TTS/LLM已提速。

原生背压199.98→24.57ms、真实静音长句18.28ms/0欠载/0重排、实际UI断线7.934fps并恢复16fps已保存。说话长帧严格门槛仍失败（P95~80/P99~158ms），不可扩大为全项目完成。未创建代理、计划任务或心跳；静音试验临时回退timer已停止。
'''
(H/'CONTINUE.md').write_text(continuation,encoding='utf-8')
progress=dict(status='DEPLOYED_AUTOMATED_VALIDATION_PASSED_HUMAN_PENDING',complete=False,
 software_deployment_complete=True,candidate_deployed=True,checked_utc=v['checked_utc'],
 tasks={'continuous_speech':{'implementation':'DEPLOYED','automatic_validation':'PASS','human_audio':'PENDING'},
        'animation_material_richness':{'implementation':'DEPLOYED','real_asset_and_ARM_validation':'PASS','human_visual':'PENDING'}},
 voice_revision=v['voice_revision'],voice_fingerprint=v['voice_fingerprint'],portrait_revision=c['revision'],
 board_runtime=c['runtime'],component_pins=279,other_models_preserved=True,original_memory_sources_unchanged=True,
 microphone_enabled_by_agent=False,listening_final=False,automatic_following_final=False,
 mechanical_state='FAULT_PROTECTION_PRESERVED',strict_speaking_16fps=False,whole_project_complete=False)
(H/'PROGRESS.json').write_text(json.dumps(progress,indent=2),encoding='utf-8')
marker='audio-animation-polish-20261029'
def prepend(path,text):
    old=path.read_text(encoding='utf-8-sig');start='<!-- '+marker+' -->';end='<!-- /'+marker+' -->'
    if start in old:
        left=old.index(start);right=old.index(end,left)+len(end);old=old[:left]+old[right:].lstrip('\r\n')
    path.write_text(start+'\n'+text+'\n'+end+'\n\n'+old,encoding='utf-8')
prepend(P/'AGENTS.md',f'''- 最新音频/动作交付：deliverables/2026-10-29_audio_animation_polish/README.md、CONTINUE.md、PROGRESS.json；已部署并过自动验证，真人听音待集中复测。原同步GLib stdout阻塞改为有界非阻塞IPC，受控ARM供音199.98→24.57ms且PCM完全相同；真实UI静音长句18.28ms/0欠载/0重排。不能冒作用户原现场声学A/B或整机完成，自打断按用户反馈已不再发生，未调整识别阈值。
- 恢复四套既有身体、同语义短轮素材选择及对应39帧眼嘴几何，点头/摇头/惊讶/疑惑保持。58音频+1平台跳过、15素材、41画面协议分组通过，不与历史总数累加。说话约15.445fps/P95~80/P99~158ms仍未过严格16fps长帧门槛；断线实际7.934fps本地回退并恢复16fps。
- 现役板端{c['runtime']}，startup/config.json布局、279绑定；Windows画面revision {c['revision']}，正常入口start_portrait.ps1及aura/config/portrait_host.local.json。旧81fd/2026-10-27启动与服务恢复脚本为历史，禁止直接覆盖新入口；voice r9/{v['voice_fingerprint']}保持。
- UI监督器{v['board']['ui']['MainPID']}，相机{v['board']['camera']['MainPID']}/epoch保持，并行startup-speed启动器字节/参数及所有旧覆盖保持。仍须每次读/proc实际入口及pending unit、双确认空闲，禁止按旧目录或旧PID切换。机械benchmark/wide不匹配FAULT/null保护保持，不改boot/FDT/固件/VART或MMIO、不恢复旧1604µs。
- 独立WMI逐表原始来源严格相等，153会话/311轮及视觉/声纹保持（仅本轮时点，后续重新备份），没有回滚私有库；其他模型与非8796服务PID保持，LLM仍D盘。监听/麦克风/跟随关闭、音量70/未静音；不自动开麦/有声播放/运动。迁移后置，无新心跳或代理。''')
summary='[最新：句中断续与动作素材修复](deliverables/2026-10-29_audio_animation_polish/README.md)：已部署并通过自动验证。供音IPC阻塞路径修复，真实界面静音长句18.28ms/0欠载；恢复四套现有身体及短轮素材变化。其他模型、记忆、相机和机械保护保持。真人听感待集中复测，说话长帧与整机仍未最终验收；当前监听关闭。'
prepend(P/'README.md',summary)
prepend(W/'语言模型分析/README.md',summary.replace('(deliverables/','(../语音共享文件/deliverables/'))
manifest={'scope':'deployed audio IPC and existing animation materials; human audio pending','files':{}}
for name,item in read('source_installation.json')['files'].items():manifest['files']['project/'+name]={'sha256':item['after'],'bytes':(P/name).stat().st_size}
for path in (H/'renderer_snapshot').rglob('*'):
    if path.is_file():manifest['files'][path.relative_to(H).as_posix()]={'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes':path.stat().st_size}
(H/'SOURCE_MANIFEST.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
with zipfile.ZipFile(H/'reviewed_source_and_reports.zip','w',compression=zipfile.ZIP_DEFLATED) as archive:
    for name in read('source_installation.json')['files']:archive.write(P/name,'source/'+name)
    for name in ('README.md','CONTINUE.md','PROGRESS.json','SOURCE_MANIFEST.json','verification.json','native_ipc_comparison.json',
                 'native_visual.json','muted_live_probe.json','live_ui_outage.json','database_verification.json',
                 'visual_preview.png','actual_avatar.png','host_entry.py','host_health.py','start_host.ps1','stop_owned_portrait.ps1',
                 'board_guard.py','test_audio_flow.py','test_visual_materials.py','fixture_adaptation.json'):
        archive.write(H/name,name)
    for path in (H/'renderer_snapshot').rglob('*'):
        if path.is_file():archive.write(path,path.relative_to(H).as_posix())
print(json.dumps({'status':'DOCUMENTED','software_deployed':True,'human_acceptance':'PENDING','model_weights_or_private_databases_packaged':False,
 'report':str(H/'README.md'),'package_bytes':(H/'reviewed_source_and_reports.zip').stat().st_size}))
