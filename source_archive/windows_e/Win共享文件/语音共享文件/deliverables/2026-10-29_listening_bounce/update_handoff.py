"""Point current project handoffs at verified r6 without rewriting historical reports."""
import json
from pathlib import Path
H=Path(__file__).resolve().parent;P=H.parents[1];root=P.parent
v=json.loads((H/'release_verification.json').read_text(encoding='utf-8'));assert v['status']=='PASS'
def insert(path,anchor,block):
 data=path.read_bytes();marker=block.strip().splitlines()[0].encode()
 assert marker not in data
 at=data.index(anchor.encode());nl=b'\r\n' if b'\r\n' in data else b'\n'
 path.write_bytes(data[:at]+block.strip().encode('utf-8').replace(b'\n',nl)+nl+nl+data[at:])
insert(P/'AGENTS.md','<!-- memory-first-user-direction-20261029 -->',r'''
<!-- voice-handoff-fixed-20261029 -->
- 现役Windows已更新为voice-turn-handoff-20261029-r6，指纹b991e72050af52d86e947594303fc30e5a5675aa2a95140ff7910ba8a0d582a8。最新故障交付入口deliverables/2026-10-29_listening_bounce/README.md、CONTINUE.md、PROGRESS.json；下方r4是此前记忆交付历史，r4功能完整保留，不能按其旧指纹/脚本覆盖r6。
- 用户报告识别后回聆听：查到取消清理期间503立即拒绝。r6受原请求预算约束，最多等待5秒交接；已开始的OmniVoice合成在原时限内完成后丢弃旧结果，保留暖态进程。不要重新提前退出TTS等待而触发所属进程退役，也不放宽TTS时限。r5首次实机失败与恢复助手uuid遗漏均已保留，最终r6通过285项回归（含旧267）、板端3种取消接新问及2项唤醒协议检查。
- 初次暂停时原143会话/273轮、77观察/73视觉事件及声纹来源逐表哈希保持；保留用户此前现场新增数据，不能恢复旧141/269或6/2快照。私有WMI文件视图与备份约定保持，公开PCM仅RAM接收、无CID/成功ACK，不需清理用户记录。
- 只重载8792/TTS，其他6个模型所属进程与其他端口、compact_grammar=false/其余五项true保持。板端代码/279绑定/界面/相机不改不重启；READY/1604µs、跟随关闭。监听已通过原UI暂停，交付时仍关闭；不自动开麦/播放/运动。用户手动开启后用完整“汐蓝，你好”复测；单独叫名回聆听是正常唤醒，未命中唤醒也会回聆听，不能将所有情况都算503。
- 实测下一轮首PCM4.842/8.085/4.690秒，未证明聊天提速。真人原话复测、短词唤醒、说话长帧、声画归属/声纹标定与整机长稳仍待验。Windows对话/记忆优先、迁移后置，LLM数据留D盘。没有新自动任务。
<!-- /voice-handoff-fixed-20261029 -->
''')
insert(P/'README.md','<!-- windows-dialogue-memory-polish-20261029 -->',r'''
<!-- voice-handoff-fixed-20261029 -->
**当前Windows语音服务r6已修复识别后退回聆听的503交接路径。** [故障、修复与实机验证](deliverables/2026-10-29_listening_bounce/README.md)。285项相关回归、板端文字/TTS/PCM三种取消后立即接话及两项唤醒协议检查通过，原数据/其他模型/板端保持。r4记忆功能保留；监听部署时暂停，现场需手动重开，用“汐蓝，你好”整句复测。普通聊天长尾和真人同一句验收仍开放，迁移继续暂缓；下方r4为前一阶段记录。
<!-- /voice-handoff-fixed-20261029 -->
''')
insert(root/'后续任务_先读这里.md','<!-- windows-dialogue-memory-polish-20261029 -->',r'''
<!-- voice-handoff-fixed-20261029 -->
**Windows现役r6：识别后回聆听的503交接修复已部署。** [最新故障修复、实测和接续](语音共享文件/deliverables/2026-10-29_listening_bounce/README.md)。受原时限约束的5秒交接等待、取消结果丢弃与暖态TTS保留已验证；285项回归（含旧267）及板端三种取消接新问/两项唤醒检查通过。原用户数据与其他模型/板端保持，r4记忆功能保留；监听交付时关闭，待现场手动开启并用原话复测。单独叫名回聆听是正常唤醒；普通聊天提速与整机验收未完成，迁移继续后置。下方r4/r3/r2为各阶段历史。
<!-- /voice-handoff-fixed-20261029 -->
''')
insert(root/'语言模型分析/README.md','<!-- windows-dialogue-memory-polish-20261029 -->',r'''
<!-- voice-handoff-fixed-20261029 -->
[当前：识别后回聆听的503交接修复r6](../语音共享文件/deliverables/2026-10-29_listening_bounce/README.md)：285相关回归、真实板端三种取消后立即接话及两项唤醒检查通过。取消时保留已运行TTS、丢弃旧结果，交接最多5秒且不增加原预算；其他模型、用户记忆与板端保持。下方r4记忆功能保留，普通聊天长尾和真人原话复测待验，迁移暂缓。
<!-- /voice-handoff-fixed-20261029 -->
''')
p=P/'aura/skills/aura-devices/references/capabilities.md';data=p.read_bytes()
old='当前Windows记忆版本为voice-dialogue-memory-20261029-r4'.encode()
new='当前Windows语音服务为voice-turn-handoff-20261029-r6，保留r4记忆功能'.encode()
assert data.count(old)==1;data=data.replace(old,new)
text='\n\n语音请求交接最多等待5秒，始终受原请求总时限约束；客户端断开时，已开始的OmniVoice合成在原时限内完成后丢弃旧结果，保留暖态模型，不发旧PCM或提示音。服务健康含最多16条RAM请求结果码/字数/等待元数据，不保存原话。单独“汐蓝”返回唤醒聆听，不代表完整问题已作答；实际修复见deliverables/2026-10-29_listening_bounce/README.md。\n'
data+=text.encode('utf-8');p.write_bytes(data)
plan=json.loads((H/'source_plan.json').read_text())
plan.update(status='RECOVERY_DEPLOYED_AND_VERIFIED',tests_passed=285)
(H/'source_plan.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
print('Updated verified r6 handoffs; historical archives retained.')
