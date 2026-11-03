"""Save migration acceptance and current project entry points in the destination."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
NOTES=ROOT/'迁移记录'
NOTES.mkdir(exist_ok=True)
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,obj): p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
copy=read(HERE/'copy_result.json')
assert copy['status']=='PASS_ALL_COPIED_FILES_SHA256'
assert ROOT.resolve()==Path(copy['destination']).resolve()
assert 'PASS: 31 saved files' in (HERE/'accepted_baseline_check.log').read_text(encoding='utf-8-sig')
asr=read(HERE/'asr_files_check.json')
differences=[r for r in asr['files'] if r['status']!='MATCH']
assert len(differences)==1 and differences[0]['path']=='tools/asr_server.py'
live=read(ROOT/'deliverables/2026-10-18_board_dialogue/live_source_snapshot.json')
latest=next(r for r in live['files'] if r['path']=='aura/tools/asr_server.py')
assert sha(ROOT/latest['path'])==latest['sha256']==differences[0]['sha256']
assert next(r for r in copy['files'] if r['path']==latest['path'])['sha256']==latest['sha256']
save(HERE/'asr_manifest_resolution.json',{'status':'PASS_CURRENT_LIVE_VERSION','legacy_manifest_matches':asr['matched'],'legacy_manifest_total':asr['required_files'],'explanation':'10-17 manifest predates 10-18 shared HTTP handler change. Sole difference asr_server.py matches 10-18 live accepted source snapshot and the verified copied source. Original historical manifest retained.','current_asr_server':latest})
before=read(HERE/'board_before_switch.json'); after=read(HERE/'board_after_probe.json')
assert before['boot_id']==after['boot_id']
assert before['camera']['value']['pid']==after['camera']['value']['pid']==976
assert before['ui_unit']==after['ui_unit']
assert after['ui']['value']['phase']=='IDLE' and not after['ui']['value']['error']
for service in ('host_asr','host_voice'):
    assert after[service]['status']==200 and after[service]['value']['ready']
assert after['host_voice']['value']['num_step']==16
probe=read(HERE/'board_client_probe.json')
assert probe['status']=='PASS_BOARD_CLIENT_ACTUAL_MODELS' and not probe['physical_playback']
process=read(HERE/'processes_after_switch.json')
listeners={r['LocalPort']:r['OwningProcess'] for r in process['listeners']}
assert set(listeners)=={8791,8792}
for port,pid in listeners.items():
    row=next(r for r in process['processes'] if r['ProcessId']==pid)
    assert str(ROOT) in row['CommandLine']
worker=next(r for r in process['processes'] if 'omnivoice_voice.py' in r['CommandLine'])
assert str(ROOT/'aura/models/tts/OmniVoice') in worker['CommandLine']
report={'status':'PASS_MIGRATION_AND_E_DRIVE_SERVICES','completed_utc':datetime.now(timezone.utc).isoformat(),'project_root':str(ROOT),'source':copy['source'],'source_preserved':True,'files_verified_during_copy':copy['total_files'],'bytes_verified_during_copy':copy['total_bytes'],'accepted_model_reference_files_verified':31,'asr_manifest_resolution':'PASS_CURRENT_LIVE_VERSION','ports':listeners,'processes':process['processes'],'board_health':{n:after[n] for n in ('host_asr','host_voice')},'board_camera_pid_unchanged':976,'board_rebooted':False,'board_ui_unit_unchanged':True,'board_client_probe':{'status':probe['status'],'elapsed_seconds':probe['elapsed_seconds'],'historical_recording':True,'physical_playback':False},'new_live_recording_after_migration':False,'previous_live_acceptance_preserved':True,'host_dialogue_ram_history_reset_at_switch':True,'python_environment_migrated':False,'ssh_private_key_copied':False,'remote_sync_completion_verified':False}
save(HERE/'service_switch.json',report)

old=(ROOT/'README.md').read_text(encoding='utf-8-sig')
backup=NOTES/'迁移前README.md'
if not backup.exists(): backup.write_text(old,encoding='utf-8')
(ROOT/'README.md').write_text('''# 汐蓝语音共享项目

当前工作根目录：`E:\\Win共享文件\\语音共享文件`。后续源码、配置、模型、运行日志、生成音频、测试和交接文件均保存于本目录。D盘原工程保留历史副本；旧文档中的D盘工作路径不再作为默认入口。

当前链路已接通：板端MCP01录音 → 本机Paraformer识别 → Qwen3 4B回答 → OmniVoice 16步 → 板端播放和口型。此前单轮新录音已由用户确认听到自动回答，软件提交至实际开口约1.609秒。16步及“柔亮俏皮”参考保持。

2026-10-18已完成本目录移植：4,468个文件、9,605,308,302字节逐文件SHA256校验；模型、参考和冻结包31项再次通过。8791/8792服务已切换至本目录源码和ASR/OmniVoice模型，日志与生成音频也写入本目录；板端访问与历史录音真实客户端探针通过，相机PID976保持。本次未新增实录播放验收。

## 启动和接手

在本目录打开PowerShell：

```powershell
.\\start_voice.ps1
```

先等两个模型服务完成预热。Windows重启后需要重新启动；本项目未设置开机自启。换主机应按语音交接文档重建Python环境并导入项目内Ollama权重，再用 `.\\start_voice.ps1 -VoicePython '<实际环境Python路径>'`。本机Python环境与SSH私钥属于主机配置，未复制进共享目录。

- [本次移植、验证与限制](迁移记录/移植完成说明.md)
- [最新板端语音链路及实录证据](deliverables/2026-10-18_board_dialogue/README.md)
- [已接受音色、模型和其他主机接手步骤](deliverables/2026-10-11_voice_accepted/HANDOVER.md)
- [迁移校验与运行切换记录](deliverables/2026-10-18_voice_migration/README.md)
- [项目整体进度与未完成模块（10-17历史核查）](aura/report/project_status_20261017/REPORT.md)

主要代码在 `aura/`，完整权重在 `aura/models/`，板端语音服务记录与缓存音频在 `deliverables/2026-10-18_board_dialogue/`。网线仍为Windows `192.168.50.1/24` → 板卡 `192.168.50.2`。

身份识别、视觉说话人、机械联动、全框架收拢、多轮长稳及冷启动仍按各自证据推进；单轮语音通过不代表整机验收。早期整合记录见[迁移前入口归档](迁移记录/迁移前README.md)。本机保存完成不代表其他主机已同步完成。
''',encoding='utf-8')

handover='''> **2026-10-18 当前工作根目录已迁至 `E:\\Win共享文件\\语音共享文件`。** 用户要求后续所有项目文件保存于此，重点是本地大语言模型与板端语音项目。4,468个文件/9.61GB逐文件复制校验通过，已接受31项模型/参考/冻结包复核通过。ASR8791、完整语音8792实际进程均从E盘源码运行，ASR/OmniVoice模型与日志/生成音频使用E盘路径；板端健康与历史录音真实客户端探针通过，相机PID976保持。D盘原工程留作历史。本机Python环境、Ollama现有运行库与SSH私钥继续作为主机依赖；共享目录包含可导入Ollama权重，换机独立配置环境和密钥。重启Windows在新项目根运行 `start_voice.ps1`。先读根README、`迁移记录/移植完成说明.md`、`deliverables/2026-10-18_voice_migration/service_switch.json`。本次未录新音或实际播放，保留此前用户确认的单轮实录证据；没有确认远端同步、长期多轮或冷启动。切换主机模型服务使其RAM对话历史重新开始。下方旧D盘工作路径与迁移前状态只作历史。

'''
for name in ('.cline-handover.md','aura/.cline-handover.md'):
    path=ROOT/name
    text=path.read_text(encoding='utf-8-sig')
    if handover not in text:path.write_text(handover+text,encoding='utf-8')
voice_readme=ROOT/'deliverables/2026-10-18_board_dialogue/README.md'
voice_header='''> **2026-10-18 工作目录更新：** 本项目及后续输出统一保存于 `E:\\Win共享文件\\语音共享文件`。ASR8791/语音8792已从此目录实际启动并经板端验证；根目录 `start_voice.ps1` 为当前入口。[迁移说明](../../迁移记录/移植完成说明.md)。下方实录为迁移前用户确认的真实单轮结果，迁移后另有历史录音客户端探针，不混作新实录。

'''
voice_readme.write_text(voice_header+voice_readme.read_text(encoding='utf-8-sig'),encoding='utf-8')
(NOTES/'移植完成说明.md').write_text('''# 项目移植完成说明

2026-10-18，按用户要求，当前及后续工作根目录统一为 `E:\\Win共享文件\\语音共享文件`。此处保存完整本地大语言模型语音项目、板端接入源码、模型权重、参考音频、配置、生成音频、日志、实录验收、板端备份与历史项目资料。新增工作在此目录进行。D盘原项目保留历史副本。

## 已完成并验证

- 4,468个文件、9,605,308,302字节复制完成，每个文件复制时核对源和目标SHA256。初始清单在 `../deliverables/2026-10-18_voice_migration/copy_result.json`；运行后日志、缓存及导航会继续更新，清单表示复制时点。
- 31项已接受模型、参考、冻结包复核通过，模型完整。10-17的ASR旧清单10/11相同；唯一差异 `asr_server.py` 是10-18接入完整语音服务的已验证版本，其SHA与最新实录源码快照、D盘复制源相同，已保存解释，不覆盖历史清单。
- ASR8791、完整语音8792及OmniVoice工作进程改用E盘项目源码、ASR/OmniVoice权重、缓存、日志与生成音频路径。板卡两个健康接口均200/ready，仍为OmniVoice16。板端客户端用历史真实录音完成实际模型调用、WAV下载和口型任务导入，1.778秒；探针没有实际播放，不能称作迁移后新实录开口时间。
- 板卡未重启，UI服务配置保持，相机PID976保持。原网线与Wi-Fi配置保留。切换主机模型进程使其RAM中的短期对话历史重新开始。

此前用户新录音→自动回答→板端实际播放的单轮验收仍完整保存在 `../deliverables/2026-10-18_board_dialogue/`：软件提交至开口约1.609秒，用户明确确认听到自动回答。多轮长稳、真实播放中取消、冷启动及整机验收仍待后续。

## 当前启动入口

在项目根PowerShell执行：

```powershell
.\\start_voice.ps1
```

需要完成模型预热；没有安装Windows开机自启。主机IP仍为192.168.50.1，板卡192.168.50.2。

本机Python语音环境继续使用原主机路径；Ollama仍使用已有安装与运行模型库。可跨机导入的Qwen3权重副本已完整保存于 `aura/models/dialogue/ollama/`。共享项目不含不可移植虚拟环境或SSH私钥，换主机按照 `deliverables/2026-10-11_voice_accepted/HANDOVER.md` 重建环境、导入Ollama，再传入实际 `-VoicePython`，并单独授权新机SSH公钥。

未复制 `.git`、VerySync元数据、虚拟环境、site-packages、Python字节码等机器状态。本次没有更改同步工具配置，也未核验其他主机同步完成。

详细证据：`../deliverables/2026-10-18_voice_migration/service_switch.json`、`processes_after_switch.json`、`board_after_probe.json`、`board_client_probe.json`、`accepted_baseline_check.log` 和 `asr_manifest_resolution.json`。
''',encoding='utf-8')
readme=HERE/'README.md'
readme.write_text(readme.read_text(encoding='utf-8-sig')+'''\n## 本次完成结果\n\n已完成4,468文件/9,605,308,302字节逐文件复制校验；`service_switch.json` 状态 `PASS_MIGRATION_AND_E_DRIVE_SERVICES`。31项已接受模型/参考文件校验通过。ASR旧清单唯一源码差异已按10-18实录源码清单复核，解释在 `asr_manifest_resolution.json`。板端两个健康接口、历史录音真实客户端探针和E盘进程/模型路径均核对通过。当前以根README和 `../../迁移记录/移植完成说明.md` 接手。\n''',encoding='utf-8')
overlays=[]
original={r['path']:r for r in copy['files']}
for name in ('README.md','.cline-handover.md','aura/.cline-handover.md','deliverables/2026-10-18_board_dialogue/README.md','deliverables/2026-10-18_voice_migration/README.md','AGENTS.md','start_voice.ps1','迁移记录/移植完成说明.md'):
    p=ROOT/name
    overlays.append({'path':name,'copy_snapshot_sha256':original.get(name,{}).get('sha256'),'current_sha256':sha(p),'reason':'Post-copy directory guidance and migration handover; live logs/cache may also change during normal operation'})
save(HERE/'post_migration_files.json',{'files':overlays})
print('PASS_MIGRATION_AND_E_DRIVE_SERVICES')
