import json,datetime
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[1]
def read(name):return json.loads((H/(name+'.json')).read_text(encoding='utf-8-sig'))
v=read('final_verification');fp=read('fingerprint_verification');reload=read('reload');after=read('after');initial=read('initial');proc=read('final_processes')
rows=[]
labels={'test_before':'本机前','test_board_before':'板端前','test_after':'本机后','test_board_after':'板端后'}
for r in v['tests']:
 label=labels[r['group']]+str(r['run'])
 if r['group']=='test_before' and r['run']==1:label+='（27B未驻留起始）'
 fallback=r['fallback'] or '无（开关关闭）'
 rows.append(f"| {label} | {r['preparation_ms']:.2f} | {r['first_clause_ready_ms']:.2f} | {r['client_text_ms']:.2f} | {r['client_first_pcm_ms']:.2f} | {r['tts_generation_ms']:.2f} | {r['backend']} | {fallback} |")
table='\n'.join(rows)
pid_rows='\n'.join(f"| {x['port']} | {x['before']} | {x['after']} |" for x in proc['other_listeners_unchanged'])
receipt=f'''# Windows 执行回执：AURA 语音延迟修复

任务版本：`AURA-VOICE-LATENCY-20261029-r1`。执行日期：2026-10-29（America/Los_Angeles，各项精确时间见JSON）。状态：**目标开关修复及限定重载完成，真实本机/板端链路验证通过；整体稳定提速未证明。**

## 实际入口与交接差异

实际微力共享根为 `E:\\Win共享文件`。已读根目录 `后续任务_先读这里.md` 及项目 `AGENTS.md`。开始及08:11:34Z复查时，指定任务目录的 `README.md`、`Ubuntu_执行回执.md` 均未同步存在；本回执和本目录README由Windows本次创建，不代表已读到或代写Ubuntu回执。Ubuntu改动及目标SHA以用户本轮消息为依据，后续同步冲突须保留双方文件。

实际8792仅绑定 `192.168.50.1:8792`，不是127.0.0.1。原监听PID28004，父包装PID22880，TTS包装PID24252；虚拟环境基础解释器为 `D:\\sd-webui-aki-v4.11.1-cu128\\_py310\\python.exe`。原父进程命令行原样复用如下：

```text
{reload['command']}
```

源码主入口为 `语音共享文件/aura/tools/board_model_host.py`，保留现役 `deliverables/2026-10-28_timeline_summaries/diagnostic_voice_entry.py` 包装；实际数据根为 `deliverables/2026-10-18_board_dialogue/model_host`。该数据根的历史日期不是源码版本。配置由实际源码的AURA根解析到 `E:\\Win共享文件\\语音共享文件\\aura\\config\\voice_latency.json`。

## 唯一业务改动与版本

先备份为本目录 [voice_latency.before.json](voice_latency.before.json)，仅将 `compact_grammar: true` 改成 `false`，其他字节保持。`reply_first`、`early_sentence`、`coalesce_chat`、`reuse_history`、`first_sentence_chat` 全部仍为true。

- 修改前配置SHA256：`{fp['sha_before']}`。
- 本机修改后配置SHA256：`{fp['sha_after']}`（CRLF）。
- 仅将换行规范化为LF后SHA256：`{fp['sha_lf_after']}`，**与Ubuntu提供值完全一致**；没有为凑哈希改写本机换行。
- 重载前后版本均为 `voice-timeline-20261028-r2`。
- 旧服务指纹：`{fp['runtime_before']}`。
- 新服务指纹：`{fp['runtime_after']}`。该指纹包含配置文件；用39项当前源/配置及旧开关备份重建得到旧指纹，用当前文件得到新指纹，均与各自实际health匹配，变化完全由这一个开关解释。详见 [fingerprint_verification.json](fingerprint_verification.json)。没有覆盖现役Python源码。

## 自然空闲、重载与恢复

重载前重新读取板端systemd实际启动入口、源码绑定和UI state。实际GUI根 `/home/root/aura-boundary-nav-20261029/gui-page-sync-v2/runtime`，UI PID114923、相机PID21824；绑定全部匹配，phase=IDLE、playing=false、audio_output_state=IDLE_READY、监听/麦克风关闭、无待处理UI设置。机械READY/1604µs、跟随关闭，未发机械命令。8792 ready=true、busy=false，TTS request_active=false。

执行 [reload_8792.ps1](reload_8792.ps1)，再次核对监听、父进程及TTS归属，备份后只终止24252、28004、22880并以原命令、原AURA工作目录通过隐藏WMI进程创建恢复。未批量终止Python。旧TTS后代已退出，无旧所属进程残留。重载起点 `{reload['utc']}`，后台首次观测READY为 `{v['startup_observation']['first_ready_utc']}`，约 **150.08秒**（轮询观测时间，不是精确内部预热时长，未超原300秒启动限额）。后续主动检查约179秒，仅是较晚观察，不能替代首次READY记录。原诊断包装就绪后取消周期调用栈转储。

新8792实际监听PID25768，父包装26788，TTS包装32224/基础解释器30552。原有启动预热实际完成：startup_warmup_complete=true，ASR/LLM/TTS dependencies ready=true。板端通过网线直接读health也确认ready=true、compact_grammar=false。完整重载前后health/板端状态见 [before.json](before.json)、[after.json](after.json)、[reload.json](reload.json)、[final_verification.json](final_verification.json)。

其他监听PID保持：

| 端口 | 重载前PID | 重载后PID |
| --- | ---: | ---: |
{pid_rows}

UI、相机PID、实际启动配置哈希和全部绑定保持；转轴仍READY/1604µs/跟随关闭，FPGA及相机未操作。没有开麦、声音播放、播放ACK或运动。

27B仍为 `aura-qwen3.8-27b-abliterated:iq4_xs`、IQ4_XS、2048上下文，摘要 `3befcf2aaf47a728e93437766b1d79d1449601c9d4b407f3a93779ee350da575`；Paraformer model_id仍 `{after['health']['asr_model']}`；OmniVoice仍16步。音色selection文件哈希保持，实际参考音频SHA匹配既有selection：`{v['voice_reference_sha256']}`。权重及Ollama路径配置仍在D盘，没有复制/移动模型。

记忆、权限、时间轴及日摘要能力位保持，后台摘要运行且无错误；持久会话141、轮次269与重载前一致。未读取/修改真实个人档案或重放私人记忆。进程内临时会话缓存随正常重载重建，私人档案授权/回忆的端到端行为本次未实测。

## 既有预热及30分钟驻留

现役源码已包含Paraformer固定WAV初始化探针、OmniVoice worker warmup、LLM同系统前缀及序列化预热、提示资产准备。本次startup_warmup_complete及之后真实链路证明这些启动步骤已执行，无重复新增预热代码。

实际项目Ollama是 **11435**（11434不是本服务模型库）。首次只读 `api/ps` 无驻留模型，因此修改前本机第1轮单列为“27B未驻留起始”，不能与修改后暖态相减。现有 `dialogue_host_ollama.chat_body(fast=True)` 设置 `keep_alive='30m'`，正常流式路径复用它；原生路径另有无prompt保活。请求后api/ps显示相同27B驻留，size_vram=14403496864、context_length=2048，expires_at随请求更新为约请求完成后30分钟；重载预热后亦可见驻留。详见 initial/before/after/test JSON。

**30m是请求续期的驻留时限，不是无限期后台保活。** 本次未等待完整30分钟无请求来验证到期行为，未新增定时轮询/加载逻辑；初始无驻留不能单凭此认定已有30m配置失效。

## 固定WAV前后实测

公开Paraformer随包 `test_wavs/0.wav`，16kHz/单声道/PCM16；WAV SHA256：`1a6bf94091d9c35e11aea5d494d05e3287b8f5c767f6de3bfd796d91b637500c`。两端使用完全相同字节；每次独立匿名boot/session/request上下文，无conversation/profile，history_messages=0，不提交ACK。8次实际ASR输入哈希和系统提示哈希分别一致；未改变模型采样参数，回复因此不保证相同。所有TTS均未命中缓存。

表内单位均毫秒。“准备”为服务端 `llm.request_preparation_ms`；“首句就绪”为现有服务端 `first_clause_ready_ms`（聊天首句缓冲提交给TTS时刻，从服务端流处理起点计）；“首text/PCM”为各客户端同一请求本地单调时钟的首帧耗时。本机及板端计时分别使用各自进程时钟，**没有直接相减跨机时间戳，也不将两列之差当网线延迟**。启动150秒与这些暖态请求分开。

| 样本 | 准备 | 首句就绪 | 客户端首text | 客户端首PCM | 首TTS生成 | backend | fallback |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
{table}

原始数据：[本机前](test_before.json)、[板端前](test_board_before.json)、[本机后](test_after.json)、[板端后](test_board_after.json)。实际请求均完整收取PCM；未做声音播放或听音验收。测试客户端使用既有VoiceChannel协议和实际板端部署模块，无板端部署/源码改写；WAV仅通过SSH内存传送，没有复制模型。

观察：修改前原生通道先超时，后因runner模型/模板/build/context未通过兼容核查而回退Ollama；其中一次命中已有兼容重试退避，准备阶段也只有0.01ms。关闭开关后四次均直接Ollama，准备记录0.00ms、无compact fallback，达成本次移除该检查路径的目标。

**不据此声称稳定整体提速。** 修改后本机首PCM6.594/17.281秒，板端6.485/5.222秒；样本少、生成文本/长度不同、GPU并行业务与缓存/频率未受控，本机仍有明显长尾。不是同PCM的严格因果A/B，不能拿最冷的109.203秒首PCM与暖态相减或给出稳定加速百分比。

## 实际执行命令与证据

以下命令均在本机PowerShell执行；系统进程/SSH/真实网络核查使用本机权限，未运行历史整包部署或回退程序。

```powershell
Get-NetTCPConnection -State Listen -LocalPort 8792
Get-CimInstance Win32_Process
Invoke-RestMethod 'http://192.168.50.1:8792/health' -TimeoutSec 10
Invoke-RestMethod 'http://127.0.0.1:11435/api/ps' -TimeoutSec 10
& 'C:\\Users\\35870\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\python\\python.exe' -B '{H / 'latency_probe.py'}' before
& 'D:\\sd-webui-aki-v4.11.1-cu128\\_py310\\python.exe' -B '{H / 'latency_probe.py'}' test_before
& 'C:\\Users\\35870\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\python\\python.exe' -B '{H / 'board_test.py'}' test_board_before
# 再跑before核查自然空闲，保留initial.json及文件哈希；随后仅执行本轮限定重载：
& '{H / 'reload_8792.ps1'}'
# 2秒间隔、有限时长health轮询等待READY；再after、test_after、test_board_after及最终验证：
& 'C:\\Users\\35870\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\python\\python.exe' -B '{H / 'latency_probe.py'}' after
& 'D:\\sd-webui-aki-v4.11.1-cu128\\_py310\\python.exe' -B '{H / 'latency_probe.py'}' test_after
& 'C:\\Users\\35870\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\python\\python.exe' -B '{H / 'board_test.py'}' test_board_after
& 'C:\\Users\\35870\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\python\\python.exe' -B '{H / 'final_checks.py'}'
```

板端只读命令由既有 `board_ssh.py` 使用本机密钥和StrictHostKeyChecking发送；只查systemctl show、真实配置/绑定SHA、8783/api/state、Windows8792/health及运行内存中的公开WAV测试。没有打印密钥或复制环境。

## 结论与剩余项

最小开关修复已生效，限定重载成功，最终19项检查全部通过；版本/模型/音色/记忆能力及保留服务/板端状态得到上述范围内验证，无本轮失败回退。启动预热仍约150秒，本机TTS生成及LLM耗时仍波动；稳定时延、实际声音/听音、真人多轮、30分钟完整空闲驻留均未验收。未新增任何业务功能或预热机制。若后续发现本轮开关导致失败，只恢复本目录开关备份并重新核对自然空闲、当前PID/命令再限定重载，不回退r2源码、私人数据库或其他服务；不能盲用历史PID。
'''
(H/'Windows_执行回执.md').write_text(receipt,encoding='utf-8')
readme='''# AURA 语音延迟修复

任务版本：`AURA-VOICE-LATENCY-20261029-r1`。

本机Windows已完成唯一开关修改及8792/TTS限定重载，板端实读READY、compact_grammar=false，其余五项保持true，现役仍voice-timeline-20261028-r2。已补同公开WAV的Windows本机与板端网线前后各两次实测；整体稳定提速未证明。

- [Windows执行回执：实际命令、版本、health、测量与限制](Windows_执行回执.md)
- [最终19项核验及8个测量摘要](final_verification.json)
- [新旧39项源/配置指纹及Ubuntu哈希对齐](fingerprint_verification.json)
- [重载范围与原命令](reload.json)、[最终进程归属](final_processes.json)
- [配置备份](voice_latency.before.json)

指定Ubuntu回执与原README在本机开始及再次检查时尚未同步存在。本README为Windows本次补建，不代填Ubuntu回执；Ubuntu原件同步到达时保留双方内容。Windows保留CRLF，配置规范化LF后的SHA与用户提供的Ubuntu SHA完全一致。

保留8791、8795、8796、项目Ollama及其余模型，板端UI/相机PID和配置、FPGA/转轴保持，未开麦、播放、运动或改真实个人档案。启动约150秒与暖态请求分开；30m是既有请求续期驻留时限，未做完整30分钟无请求观察。
'''
(H/'README.md').write_text(readme,encoding='utf-8')
marker='<!-- voice-latency-repaired-20261029 -->'
root_note=marker+'''\n**2026-10-29语音延迟开关修复已生效：** [Windows实际回执与本机/板端前后对照](协作任务/2026-10-29_语音延迟修复/Windows_执行回执.md)。现役r2只关闭compact_grammar，其余五项保持；自然空闲限定重载8792/TTS后板端实读READY/false，39项指纹变化仅配置。启动首次READY约150秒，暖态四次直接Ollama/无fallback，但本机首PCM仍6.59–17.28秒，不能宣称整体稳定提速。既有预热与30m请求驻留保留；8791/8795/8796/Ollama、GUI/相机/FPGA/转轴保持，无开麦播放运动或个人档案变更。Ubuntu任务原件本机尚未同步，LF配置SHA已与用户提供值核同。\n<!-- /voice-latency-repaired-20261029 -->\n\n'''
target=R/'后续任务_先读这里.md';text=target.read_text(encoding='utf-8-sig')
if marker not in text:
 first,rest=text.split('\n',1);target.write_text(first+'\n\n'+root_note+rest,encoding='utf-8')
target=R/'语言模型分析/README.md';text=target.read_text(encoding='utf-8-sig')
if marker not in text:
 note=marker+'''\n[语音延迟修复实际回执及两端前后实测](../协作任务/2026-10-29_语音延迟修复/Windows_执行回执.md)：r2仅关闭compact_grammar，限定重载已READY、板端实读false。LF配置SHA与Ubuntu一致；其余开关、27B/Paraformer/OmniVoice16、音色和记忆能力保持。启动约150秒；原生fallback检查路径已移除，本机暖态首PCM仍有长尾，未声称稳定整体提速。其他服务及板端保持。\n<!-- /voice-latency-repaired-20261029 -->\n\n'''
 target.write_text(note+text,encoding='utf-8')
print('Wrote Windows receipt, task README, shared entrance and analysis index.')
