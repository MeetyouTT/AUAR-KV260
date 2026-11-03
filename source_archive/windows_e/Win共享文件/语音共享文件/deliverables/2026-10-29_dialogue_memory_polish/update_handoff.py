"""Update current handoff pointers while preserving all historical evidence."""
from pathlib import Path
P=Path(__file__).resolve().parents[2]
root=P.parent
def replace_block(path,start,end,new):
 data=path.read_bytes();a=data.index(start.encode());b=data.index(end.encode(),a)+len(end.encode())
 newline=b'\r\n' if b'\r\n' in data else b'\n'
 data=data[:a]+new.strip().encode('utf-8').replace(b'\n',newline)+data[b:]
 path.write_bytes(data)
def insert_before(path,old,new):
 data=path.read_bytes();assert new.strip().splitlines()[0].encode() not in data
 at=data.index(old.encode());newline=b'\r\n' if b'\r\n' in data else b'\n'
 path.write_bytes(data[:at]+new.strip().encode('utf-8').replace(b'\n',newline)+newline+newline+data[at:])
replace_block(P/'AGENTS.md','<!-- memory-first-user-direction-20261029 -->','<!-- /memory-first-user-direction-20261029 -->',r'''
<!-- memory-first-user-direction-20261029 -->
- 用户最新明确：先不要将这些功能迁到板卡，继续完善Windows对话和记忆并验证效果。迁移暂缓；保留当前板端部署、人脸DPU/机械及其他模型，不能自行接管PS数据或重启板端。
- 当前交付入口：deliverables/2026-10-29_dialogue_memory_polish/README.md、CONTINUE.md、PROGRESS.json。Windows r4已部署：自然当前事实直答、中文/数字1—32条历史完整浏览、旧写入/导入来源自动保守保护；267项Windows相关回归（含旧210）、12步实际记忆、7项普通语音功能、板端已有ARM客户端两轮网线请求通过。无ARM pytest、开麦/实体播放/成功ACK；整机未完成。
- 保留并行compact_grammar=false与其他五项true，当前voice-dialogue-memory-20261029-r4指纹1ed519dc5d287a344019beca4212f588aa9d41dcafebabf867466232346b3de2。只重启8792及TTS，其他模型/端口、板端279绑定及READY/1604µs保持。人脸主链仍板卡DPU。原141会话/269轮、6观察/2视觉事件和声纹来源逐表哈希保持，公开测试行清理完毕；独立WMI读取真实私有库。
- 同录音/同会话同明确事实，重复查询首PCM中位数2.656→0.110秒（改后3次TTS缓存命中）；首次双方未命中缓存的单次4.641→1.453秒。仅证明当前事实路径收益，不能称27B或普通聊天提速。普通聊天对照改前4.640/3.109、改后5.593/6.625秒，原因未确认；前端1/330帧>20ms，严格门槛未通过。
- 版本历史为录入时间，非实际生效时间；默认语音列最近两条摘录，索引读取完整存储值。删除默认当前会话，个人范围须授权，预览60秒确认及原上限保持；不删除视觉/备份。r4完整来源标记包含空上下文，缺标记且无边的旧/导入/回退写入回复自动保守停用相关召回，不再仅依赖legacy_cutoff；这替代r3需人工重建旧截止的要求，不能给未知旧行伪造来源。
- 整个记忆路线与整机真人验收尚未完成。普通聊天长尾、实际生效日期、跨天真人体验、短词唤醒、说话长帧、声画归属和现场声纹标定待后续，迁移继续暂缓。r3历史证据仍在deliverables/2026-10-29_memory_controls，不重跑其部署脚本。
<!-- /memory-first-user-direction-20261029 -->
''')
insert_before(root/'后续任务_先读这里.md','<!-- windows-memory-controls-20261029 -->',r'''
<!-- windows-dialogue-memory-polish-20261029 -->
**当前Windows对话与记忆为r4，已部署并完成本轮自动验收：** [实现、可比测量及接续](语音共享文件/deliverables/2026-10-29_dialogue_memory_polish/README.md)。自然明确事实直答、中文编号历史浏览和旧写入来源保护已补齐；267项相关回归（包含旧210）、12步实际记忆、7项语音功能和板端网线两轮通过。重复事实首PCM中位数2.656→0.110秒，改后有TTS缓存；普通聊天对照未提速，不能作全局收益。原始记忆来源逐表哈希、其他模型和板端279绑定保持，未开麦/发声/运动，未迁库。用户要求继续Windows完善后再考虑迁移；本轮交付完成，整机/记忆路线未全部完成。下方r3/r2按各自历史理解。
<!-- /windows-dialogue-memory-polish-20261029 -->
''')
insert_before(root/'语言模型分析/README.md','<!-- windows-memory-controls-20261029 -->',r'''
<!-- windows-dialogue-memory-polish-20261029 -->
[当前：Windows对话与记忆r4实现及效果验证](../语音共享文件/deliverables/2026-10-29_dialogue_memory_polish/README.md)：明确事实自然直答、1—32中文/数字索引历史和旧写入来源保护已部署。267相关回归（含旧210）、12步实际记忆、7项语音功能及板端网线两轮通过。重复事实首PCM中位数2.656→0.110秒，后三次TTS缓存命中；首次双方未命中缓存的单次4.641→1.453秒。普通聊天对照未提速，长尾仍开放。原记忆/视觉/声纹来源哈希、其他模型与板端保持，迁移暂缓；整机与跨天真人验收未完成。
<!-- /windows-dialogue-memory-polish-20261029 -->
''')
insert_before(P/'README.md','<!-- avatar-performance-20261020 -->',r'''
<!-- windows-dialogue-memory-polish-20261029 -->
**当前：Windows对话与记忆r4已部署并完成本轮自动验收。** [实现、优化效果与接续](deliverables/2026-10-29_dialogue_memory_polish/README.md)。语音独立于视觉，视觉只作补充；本轮补齐自然明确事实直答、中文编号历史浏览和旧写入来源保护。267相关回归、12步实际记忆、7项语音功能及板端网线两轮通过；重复事实首PCM中位数2.656→0.110秒（后三次命中TTS缓存），普通聊天仍有长尾，未证明整体提速。保留其他模型、原数据与板端，迁移按用户要求暂缓。未开麦/实体播放，整机和跨天真人验收未完成；下方旧视觉绑定接话与旧进度按历史理解。
<!-- /windows-dialogue-memory-polish-20261029 -->
''')
print('Updated four current handoff pointers; historical records retained.')
