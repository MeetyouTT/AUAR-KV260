"""Publish evidence-backed handoff only after the final native trial passes."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
def read(name):
    return json.loads((HERE / name).read_text(encoding='utf-8'))
c = read('candidate.json')
layout = read('layout_deployment.json')
final = read('final_verification.json')
assert layout['status'] == 'COMMITTED' and final['status'] == 'PASS'
assert read('deployment.json')['status'] == 'COMMITTED'
assert read('live_ui_outage.json')['status'] == 'PASS'
assert read('muted_speech_probe.json')['status'] == 'PASS'
health = read('windows_health_final.json')
assert all(health[k]['reachable'] for k in ('asr', 'dialogue', 'frontend', 'portrait'))
progress = read('PROGRESS.json')
progress.update(status='DISPLAY_DEPLOYED_16FPS', candidate=c['stage'],
    physical_native_display_switched=True, native_deployment_committed=True,
    physical_audio='Real MCP01 PCM clock tested while hardware muted; no audible playback',
    last_checked_at_utc=final['checked_at_utc'], final_target_fps=16,
    actual_layout_trial=layout['sample'], idle_24fps_accepted=False,
    full_hidden_gtk='PASS; settings bounds/non-overlap and profile cancel; full_gtk_layout.json',
    native_attempt='12fps committed, 16fps passed and persisted, 24fps failed original timing gates; layout retry committed',
    actual_ui_outage='PASS; local fallback 8.0047fps and remote recovery; live_ui_outage.json',
    muted_speech='PASS PCM/mouth continuity; 15.525fps; strict 16fps interval stability not passed under speech load',
    next=['User-present listening, interruption and profile selection acceptance',
          'Sustained real conversation frame timing and latency optimization',
          'Remaining identity/visual attribution, visual Q&A and mechanical field acceptance'],
    latest_target_work=['This Windows display deployment and automatic acceptance are complete'],
    user_follow_choice='用户授权停止跟随后已安全退出；验收后保持关闭',
    final_verification='final_verification.json')
(HERE / 'PROGRESS.json').write_text(json.dumps(progress, ensure_ascii=False, indent=2), encoding='utf-8')
sample = layout['sample']
readme = f'''# Windows画面合成部署与验收（2026-10-27）

**已部署：Windows CPU合成，板卡现有单一native sink送显，目标16fps；断线自动回退板卡8fps。** 最终仅修复设置页按钮布局的版本也已提交，实测 {sample['fps']:.3f}fps，帧间隔P95中位{sample['p95_ms']:.2f}ms、P99中位{sample['p99_ms']:.2f}ms。24fps未达到原门槛，未保留为生产配置。

用户明确授权“允许停止跟随并继续部署”后，通过既有UI停止入口安全退出持续跟随；最终跟随关闭、转轴读回1422、无活动运动、监听/麦克风关闭、访客模式、IDLE_READY，音量恢复原70%且未静音。只读等待心跳已通过工具删除。整个玩偶项目仍未全部验收，范围与限制见下。

## 当前入口与架构

正式根：`{c['stage']}`；启动器：`{c['startup']}/launcher.py`。本任务只管理32个z前缀的独立systemd覆盖，全部旧覆盖与原UI保留。最终入口、boot、组件哈希与状态见[最终核验](final_verification.json)。不要用历史路径/PID覆盖并行机械更新。

Windows使用有线192.168.50.1:8796，CPU合成423×438 RGB。板卡保留FSM、PCM时钟、口型增益、动作、取消和对话控制。一个进行中请求、一份最新待处理请求，校验会话/代次/状态/音频样本/修订/CRC，接收与送显前均执行150ms期限；仅复用原native sink。断网本地绘制，恢复后切回电脑。设置页“电脑/板卡画面”按钮已调整至可见范围，未覆盖原个人记忆或机械入口。

676份现有视觉资源（188362769字节）两端哈希一致，没有复制素材或模型。所有LLM权重、缓存及Ollama数据保持D盘；未卸载或停止其他模型。`start_portrait.ps1`可独立启动；`start_voice.ps1`在原语音服务就绪后启动画面服务，`-WithoutPortrait`可跳过。未设置Windows登录自启动。

## 实际送显与功能验收

| 检查 | 实测与结论 | 证据 |
| --- | --- | --- |
| 原板端8fps基线 | 8.002fps；P95 165.74ms；UI CPU约139.2% | [原生部署](deployment.json) |
| 首次12fps | 11.922fps；P95 92.83ms；P99 118.48ms；UI CPU约55.55%；COMMITTED | [原生部署](deployment.json) |
| 16fps分级 | 15.868fps；P95 73.86ms；P99 101.96ms；通过 | [分级结果](fps_steps.json) |
| 24fps分级 | 23.414fps；P95 52.17ms > 52.083ms；P99 84.84ms > 83.333ms；未通过并恢复16fps | [分级结果](fps_steps.json) |
| 最终布局版16fps | {sample['fps']:.3f}fps；P95 {sample['p95_ms']:.2f}ms；P99 {sample['p99_ms']:.2f}ms；COMMITTED | [最终部署](layout_deployment.json) |
| 实际UI断线 | 停止本任务持有的Windows画面进程，原UI持续本地8.005fps、16份变化预览；恢复远端16fps，最大显示帧龄124.92ms | [真实断线](live_ui_outage.json)、[主机恢复](host_recovery.json) |
| 静音真实PCM/口型 | 真实MCP01播放时钟，硬件静音直接核实；11.53秒SPEAKING约15.525fps、19份变化预览、口型随PCM变化；恢复原音量 | [静音语音](muted_speech_probe.json) |
| 原生截图与布局 | 主画面/角色完整；设置页按钮可见；隐藏GTK检查控件无越界/重叠，选档取消正常 | [主屏](native_screen.png)、[设置页](native_settings.png)、[布局检查](full_gtk_layout.json) |
| 服务与状态 | 8791/8792 HTTP、8795/8796帧协议均可达；跟随/监听关闭、访客、音频就绪 | [Windows健康](windows_health_final.json)、[最终核验](final_verification.json) |

帧率来自实际native提交计数，P95/P99为采样中滚动帧间隔分位数的中位数，**不是面板光学扫描测量，也不是把所有窗口合并后的全程分位数**。CPU百分比按进程多核口径，不是整机利用率。短时基线比较不能证明所有收益均来自单一改动。

静音SPEAKING的P95/P99中位约99.57/132.04ms，尚不满足待机16fps门槛；本轮只证明真实PCM时钟、口型和远端显示连续。未开麦、未播放可听测试音、未恢复运动，不能代替真人听音/插话或持续实聊验收。设置页截图底部旧“屏幕3.9fps”来自GTK界面刷新采样，不能代表独立native sink的角色送显速率；实际值以avatar_display计数为准。旧`render_performance.py`日志的`target_fps=8`是固定历史字段，远端模式目标应看API/config，实际速率用提交时间戳/计数；该字段未在本轮扩大修改。

## 回归、失败与证据范围

初次ARM完整362通过/1平台跳过；最终核心Windows48通过、ARM专项67通过，互有重叠不能相加。最终GUI仅改两个布局位置/尺寸，核心Python逐文件与通过版本一致；GUI独立通过隐藏GTK布局、截图和实际16fps再验收。包清单明确区分这两种验证，不把旧GUI哈希冒充新GUI回归结果。

真实素材/静音虚拟PCM/网线的动作、口型、暂停、取消和模式切换见[live_headless.json](live_headless.json)；这些隔离测试不等于真人验收。实际断线期间的预期连接失败保留，不能声称全程零网络错误。

历史USB掉线及原音频恢复、远端额外等待导致150ms过期回退、等待持续跟随、首次布局启动检查过早误读旧API等失败均保留。布局首次失败已恢复原通过版本，重试增加新进程及实际启动路径核对，并重新通过完整原门槛；不放宽性能阈值。布局失败日志为`layout_deployment.log`，通过重试为`layout_deployment_retry.log`。

## 回退与后续

接续操作见[CONTINUE.md](CONTINUE.md)。日常可用设置页切回板卡绘制；Windows失联自动回退。完整UI回退脚本[rollback_ui.py](rollback_ui.py)默认只读核验，`--apply`仅在空闲、音频就绪、监听与跟随关闭、原源码/机械绑定一致时移除本任务自己的覆盖；原路径保留，其只读核验见[rollback_check.json](rollback_check.json)。不要为回退放宽硬件校验。

本次Windows画面部署的自动验收已完成。仍需人在场的新版听音、插话、选档、多人噪声、持续实聊，以及声纹/声画归属、视觉问答和机械现场验收；这些不应标为全部完成。其他模型继续运行，板端迁移另按既定方案推进。

[源码及小型证据包](source_and_evidence.zip)由显式白名单[脚本](package_release.py)生成，[逐文件SHA清单](SOURCE_MANIFEST.json)可复核；不含模型权重、视觉素材字节、虚拟环境、私钥、录音或数据库。
'''
(HERE / 'README.md').write_text(readme, encoding='utf-8')
(HERE / 'CONTINUE.md').write_text(f'''# 当前交付接续（2026-10-27）

本轮Windows CPU画面部署已完成，正式目标16fps，实际UI断线回退8fps/恢复、静音真实PCM与口型、设置页布局均有证据。先读README、PROGRESS、final_verification和最新适用AGENTS。正式根 `{c['stage']}`；不得再从历史8fps入口直接覆盖。

1. 用户已授权停止跟随，本轮通过既有入口退出；最终保持跟随、监听、麦克风关闭。没有自动恢复运动。两分钟等待心跳automation已通过工具删除，不重复创建。
2. 先运行check_wait.py只读确认当前boot、入口、空闲、IDLE_READY、跟随/活动运动和监听状态，再核对当前源码/配置，保护之后的并行机械更新。持续跟随duration_s=0没有固定结束时间，SOURCE_HORIZON_ENDED不是整个跟随已退出。
3. 不要重跑deploy_ui.py/prepare_layout.py/step_fps.py来“补做”本轮。它们是历史验收脚本，门槛/入口均固定。16fps已经持久化，24fps因P95/P99未通过而未采用。
4. Windows只管理本任务持有的8796 CPU画面服务。start_portrait.ps1可独立启动，start_voice.ps1接原语音服务，-WithoutPortrait跳过；未设系统自启。不可终止其他模型；LLM数据继续D盘，无共享目录权重或入口。
5. rollback_ui.py默认只读检查；--apply为完整UI回退，仅移除本任务32z覆盖并核对旧源码/机械绑定、空闲、监听和跟随关闭。旧覆盖保留。不要用历史脉宽/PID覆盖当前现场状态，HDMI排查继续暂停。
6. 后续重点：用户在场听音/插话/选档、持续实聊帧间隔与延迟、声纹/声画归属、视觉问答和机械现场验收。本轮静音PCM功能通过，但SPEAKING P95约99.57ms，不能宣称严格稳定16fps。不开麦或自动运动来代替待确认的现场验收。
7. 旧性能日志target_fps固定8，远端模式使用API/config目标及native提交计数；待后续有新性能改动时再单独修正该元数据并回归。

本机解释器：C:\\Users\\35870\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\python\\python.exe。SSH复用相邻2026-10-18_board_dialogue/board_ssh.py；禁止输出或打包私钥。最终包显式排除模型、素材字节、虚拟环境、音频和数据库。
''', encoding='utf-8')
project = HERE.parents[1]
agents = project / 'AGENTS.md'
text = agents.read_text(encoding='utf-8')
marker = '<!-- windows-portrait-final-20261027 -->'
assert marker not in text
agents.write_text(marker + '\n- 本轮Windows CPU画面已正式部署为16fps，最新根`' + c['stage'] + '`；详见deliverables/2026-10-27_windows_portrait/README.md与CONTINUE.md。12/16通过，24的P95/P99未通过，保持16；实际UI断线本地8fps及恢复通过。设置页布局修复已独立隐藏GTK/截图/实际16fps验证。核心旧回归48/67与362互有重叠不得相加。\n- 用户明确授权停止跟随后已安全退出，最终跟随/监听/麦克风关闭，访客，IDLE_READY，音量70恢复；当前脉宽1422仅本次证据，不可覆盖后续更新。automation心跳已工具删除。下文“正式8fps/等待跟随/未部署”均为历史记录，以上述交付为准。\n- 静音真实PCM/口型通过，SPEAKING约15.525fps/P95约99.57ms仍不满足严格16fps间隔，真人听音/插话和持续实聊待验；全部玩偶任务未完成。其他模型保持，LLM数据仍D盘，HDMI排查暂停。\n\n' + text, encoding='utf-8')
index = project.parent / '语言模型分析/README.md'
old = index.read_text(encoding='utf-8')
index.write_text('<!-- windows-portrait-final-20261027 -->\n[Windows画面已部署16fps与验收报告](../语音共享文件/deliverables/2026-10-27_windows_portrait/README.md)：12/16fps原生送显通过，24fps未达间隔门槛而保留16；实际UI断线本地8fps/恢复、静音真实PCM口型和设置页布局通过。跟随/麦克风关闭，等待心跳已删除；其他模型及D盘存储保持。持续实聊稳定性及新版真人验收仍待完成。下列等待部署描述为历史。\n\n' + old, encoding='utf-8')
print('Published final README, CONTINUE, PROGRESS, AGENTS and analysis index')
