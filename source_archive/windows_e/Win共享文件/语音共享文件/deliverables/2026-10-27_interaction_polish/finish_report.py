"""Finalize evidence-backed repository handoff after successful deployment."""
import hashlib,json,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
def read(n):return json.loads((HERE/n).read_text(encoding='utf-8'))
c=read('candidate.json');d=read('layout_deployment.json');v=read('final_verification.json')
assert d['status']=='COMMITTED' and v['status']=='PASS' and read('full_gtk_layout.json')['passed']
assert c['gui_text_sha256']==hashlib.sha256((HERE/'candidate_source/tools/board_avatar_gtk.py').read_text(encoding='utf-8').encode()).hexdigest()
h=read('windows_health_final.json')
assert all(h[k]['reachable'] for k in ('asr','dialogue','frontend','portrait'))
s=d['sample']
status=dict(status='INTERACTION_UI_DEPLOYED',checked_at_utc=v['checked_at_utc'],runtime=c['runtime'],
 changed=['tools/board_avatar_gtk.py'],core_files_unchanged=v['core_python_files_unchanged'],target_fps=16,
 measured=s,pan_us=v['pan_us'],following=False,microphone=False,audio='IDLE_READY',profile='guest',
 windows_services_ready=True,whole_project_complete=False,
 next=['User-present listening/interruption/profile selection','Sustained conversational frame timing',
 'Speaker/visual attribution and mechanical field acceptance'])
(HERE/'PROGRESS.json').write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding='utf-8')
text=f"""# 玩偶交互完善与当前进度（2026-10-27）

本轮交互界面修复已部署，目标16fps；实测{s['fps']:.3f}fps，滚动帧间隔P95中位{s['p95_ms']:.2f}ms、P99中位{s['p99_ms']:.2f}ms，原门槛未放宽。正式入口：{c['startup']}/launcher.py。

## 本轮修改

- 麦克风关闭且没有历史转写时，主画面明确提示“麦克风已关闭，恢复免点击后再说话”。
- 免点击暂停提示不再覆盖正在播放、转写或准备回答的状态。
- 独立语音服务卡片和页脚使用实际语音配置及错误状态；配置存在只显示“已配置”，不误报“待接入”，也不把配置等同于实时健康。
- 帧率读取实际native sink送显统计；过期时显示“画面待更新”，不再把GTK标签刷新约4fps误报为角色帧率。

仅修改GUI一个文件，见[差异](gui_changes.diff)。{v['core_python_files_unchanged']}份核心Python与上一版一致，{v['startup_pins_verified']}项组件哈希通过；语音推理、PCM、渲染、机械代码/绑定/配置保持。模型仍在D盘，未停止其他模型。

## 当前进度

| 范围 | 已确认 | 待完成 |
| --- | --- | --- |
| 动画 | Windows CPU、16fps单sink正式运行；上一版实际UI断线回退8fps及恢复通过 | 语音负载长帧、持续实聊 |
| 语音 | 8791/8792 HTTP、8795/8796帧协议健康 | 新版真人听音、插话与现场噪声 |
| 界面 | 本轮状态提示、麦克风引导、送显帧率及布局验证通过 | 完整现场体验 |
| 视觉 | 只读观察相机/检测/DPU READY，当前无确认目标，身份UNKNOWN | 实际目标确认、声画归属、视觉问答 |
| 跟随 | 用户本轮授权停止，通过现有UI退出，读回{v['pan_us']}保持 | 机械现场验收；未恢复运动 |
| 个人记忆 | 入口及取消返回保留，默认访客 | 新版选档体验、声纹标定与真实使用 |

最终音频IDLE_READY、监听/麦克风关闭、访客、音量70%且未静音。检查开始时跟随被重新开启，不能沿用上一轮“关闭”或1422位置；本轮停止位置{v['pan_us']}仅为证据，不可覆盖后续现场更新。

## 验证与限制

[隐藏GTK结果](full_gtk_layout.json)覆盖暂停/播放/处理提示、语音配置/错误、帧率缺失/无效/过期、控件边界/重叠和选档取消；ALSA null、假机械、无第二native sink、无麦克风或可听播放。初次测试输入缺少ui_settings的失败保留，补齐实际refresh_settings路径后通过；未修改正式程序掩盖失败。

[部署](layout_deployment.json)核验新进程及真实启动路径、原16fps门槛、独立300秒回退守护、相机/位置/监听偏好/音量保持。[最终核验](final_verification.json)、[Windows健康](windows_health_final.json)、[视觉状态](visual_readiness.json)、[主屏](native_screen.png)、[设置页](native_settings.png)可复核。

本轮是GUI交互修复，不代表整个玩偶完成。上轮静音真实PCM约15.525fps/P95约99.57ms，仍不满足严格16fps间隔；本轮未改性能核心，未重测真人或声学效果。24fps仍未采用。旧性能日志target_fps固定8尚未修改；远端帧率以API/native统计为准。

## 接续与回退

接续先读最新AGENTS及本轮PROGRESS，再核对实际入口、boot、源码、空闲、音频、跟随/运动和监听状态。不可恢复历史脉宽或按旧入口覆盖。其他模型与D盘存储保持，HDMI排查暂停，等待心跳先前已删除、本轮未新建。

本轮仅替换原画面任务自己的32z覆盖；上一正式版本为{c['previous_candidate']['stage']}，当前stage的previous_override.conf为切换前原文。deploy_layout.py是一次性验收脚本，不重跑已提交候选。完整回退前须重新确认无跟随/活动运动/监听/对话，只恢复该备份覆盖并保留其他覆盖，不能放宽硬件校验。

[源码及证据包](source_and_evidence.zip)只含本轮GUI、部署验证脚本、小型状态和截图；无模型、素材目录、虚拟环境、录音、身份库或密钥。[逐文件SHA](SOURCE_MANIFEST.json)。
"""
(HERE/'README.md').write_text(text,encoding='utf-8')
project=HERE.parents[1];marker='<!-- interaction-polish-final-20261027 -->'
entry=f"""{marker}
- 最新交互GUI：{c['stage']}，报告deliverables/2026-10-27_interaction_polish/README.md。只改状态/麦克风引导/实际送显帧率/独立语音配置显示，隐藏GTK与原16fps门槛通过，核心和机械配置保持。不能按下方旧入口覆盖。
- 用户本轮再次授权停止跟随后已通过UI退出，当前位置{v['pan_us']}保持；跟随/监听/麦克风关闭、访客、音频就绪。相机/检测就绪但无确认目标。其他模型及D盘存储保持，整个玩偶未全部完成，持续实聊和新版真人验收仍待进行。

"""
path=project/'AGENTS.md';old=path.read_text(encoding='utf-8');assert marker not in old
path.write_text(entry+old,encoding='utf-8')
path=project.parent/'语言模型分析/README.md';old=path.read_text(encoding='utf-8');assert marker not in old
path.write_text(marker+'\n[玩偶交互提示修复与当前进度](../语音共享文件/deliverables/2026-10-27_interaction_polish/README.md)：GUI正式部署，16fps门槛通过；麦克风引导、播放/处理提示、语音配置提示及送显帧率修复。跟随按授权停止，现场验收仍未全部完成。\n\n'+old,encoding='utf-8')
names=['README.md','PROGRESS.json','candidate.json','candidate_initial.json','baseline_state.json','baseline_gui.py',
'candidate_source/tools/board_avatar_gtk.py','gui_changes.diff','follow_pause.json','visual_readiness.json',
'layout_preparation.json','full_gtk_layout.json','layout_deployment.json','final_verification.json','windows_health_final.json',
'native_screen.png','native_avatar.jpg','native_settings.png','prepare_layout.py','smoke_layout.py','deploy_layout.py',
'capture_board.py','capture_settings.py','verify_final.py','finish_report.py','smoke_initial_fixture_failure.log',
'smoke_layout.log','deployment.log']
manifest={}
for name in names:
 data=(HERE/name).read_bytes();assert len(data)<2_000_000,name
 manifest[name]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
(HERE/'SOURCE_MANIFEST.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
with zipfile.ZipFile(HERE/'source_and_evidence.zip','w',zipfile.ZIP_DEFLATED) as z:
 for name in names+['SOURCE_MANIFEST.json']:z.write(HERE/name,name)
with zipfile.ZipFile(HERE/'source_and_evidence.zip') as z:assert z.testzip() is None
print(json.dumps(status))

