from common import *
from copy import deepcopy
import re
names=['command_guard_validation','perception_freshness_benchmark','llm_voice_runtime_optimization']
texts={names[0]:'''---
name: command-guard-validation
description: 核对 FPGA 执行器命令轨迹中的重复序号、目标越界、STOP、QUIESCE 与租约到期，或用已冻结的 KV260 wide RTL 复跑保护逻辑仿真。
---

在本技能目录执行 python3 -B scripts/run_checks.py。它顺序验证合同指纹和正常、违规、证据不足三类轨迹。审核新日志时，用 scripts/validate_trace.py 传入 --trace 和 --profile，按一次开机的单调时钟对齐。记录缺少提交决策或主动停止回读时保留 UNKNOWN。

需要 RTL 时序证据时，按[复跑说明](readme.md)的“四套 RTL 仿真”运行 scripts/run_rtl.py，保留每个测试台的成功标志与具体参数。将结果区分为提交轨迹、仿真脉冲和物理引脚读数。报告机构是否真正停止，需要现场观测覆盖相同时间段。
''',names[2]:'''---
name: llm-voice-runtime-optimization
description: 分析本地 LLM 与 TTS 请求时延、缓存和有效样本，或核对语音播放回执与可撤销记忆的提交顺序。
---

在本技能目录运行 python3 -B scripts/check.py。用 scripts/verify_measured_run.py examples/measured 复算模型主机的逐次记录与汇总。比较方案时固定模型、量化、输出上限和 TTS 步数，将冷热状态、TTS 缓存、跳过的请求和语义审核分开记录。分别报告 LLM 首个内容、完整响应、TTS 返回，以及有实物采样时的扬声器首声。

核对播放与记忆时，用 scripts/validate_delivery_trace.py --input 读入归一化轨迹，匹配请求、代次、段号、PCM 指纹和有效时限。完整播放回执才允许提交已播记忆。缺失的时点和无法判定的样本保留 UNKNOWN。示例字段与五对实测数据见[复算说明](readme.md)。
'''}
for n,s in texts.items():
    q=ROOT/'skill'/n/'SKILL.md';q.write_bytes(s.encode())
f=ROOT/'skill'/names[0]/'checksums.sha256'
lines=[x for x in f.read_text(encoding='utf8').splitlines() if x.split('  ',1)[1]!='SKILL.md']
lines.append(sha(f.parent/'SKILL.md')+'  SKILL.md')
f.write_bytes(('\n'.join(sorted(lines,key=lambda x:x.split('  ',1)[1]))+'\n').encode())
for n in names:
    d=ROOT/'skill'/n;validator=Path.home()/'.codex/skills/.system/skill-creator/scripts/quick_validate.py'
    proc=subprocess.run([sys.executable,'-B','-X','utf8',str(validator),str(d)],check=True,capture_output=True,env=dict(os.environ,PYTHONIOENCODING='utf8'))
    print(n,proc.stdout.decode().strip())
    entries=[x.split('  ',1) for x in f.read_text(encoding='utf8').splitlines()]
assert all(sha(f.parent/path)==h for h,path in entries)
save(QA/'skill_entry_validation.json',dict(status='PASS',validated_frontmatter=[x.replace('_','-') for x in names],standard='skill-creator/scripts/quick_validate.py',all_command_guard_checksums_verified=True))
f=ROOT/'skill/readme.md';s=f.read_text(encoding='utf8')
if 'SKILL.md' not in s:
    f.write_bytes((s+'\n独立 ZIP 中保留同样的目录和示例。三套项目技能均有 SKILL.md 入口。供支持该格式的助手发现时，将相应的完整目录复制到技能搜索路径，并分别将目录命名为 command-guard-validation、perception-freshness-benchmark、llm-voice-runtime-optimization。也可直接从原目录运行 Python 命令。\n').encode())
f=ROOT/'build/readme.md';s=f.read_text(encoding='utf8')
if 'auar_wide_source_routed.dcp' not in s:
    f.write_bytes((s+'\n低核工作站可直接使用主 RAR 旁的 auar_wide_source_routed.dcp，其 SHA-256 为 933c712d30fd6aa549eb785a21dc6ca360ce179b24b9d3fb76a777d662d96007。进入解压后的 aura 并载入 Vivado 2022.2 后执行以下命令。\n\n~~~sh\npython3 -B build/scripts/fpga.py export --checkpoint ../auar_wide_source_routed.dcp --out "$HOME/auar-xsa-01"\n~~~\n').encode())
