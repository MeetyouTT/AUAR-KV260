"""Add the completed local report entry, preserving the old index verbatim."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
target = Path('E:/Win共享文件/语言模型分析/README.md')
marker = b'<!-- joint-balance-subtitle-complete-20261101 -->'
original = target.read_bytes()
assert marker not in original, 'This entry was already published; do not duplicate it.'
backup = HERE / 'analysis_index_before_subtitle_20261101.md'
with backup.open('xb') as handle:
    handle.write(original)
prefix = '''<!-- joint-balance-subtitle-complete-20261101 -->
2026-11-01本轮最新：状态投影减负和字幕修复已上线，现役startup `22317f79…`、源码 `de04c6cd…`。用户确认人数正确、声音完整，三轮对话后仍记得温水；最终字幕复验确认识别与回答两栏都显示，完整播放ACK已配对。最终保存为暂停聆听、麦克风关闭、无播放、转轴输出关闭。

[本轮优化与验收记录](E:/Win共享文件/语音共享文件/deliverables/2026-10-30_board_owner/integration/dialogue_repair/joint_balance_20261101/优化与验收进度.md) · [完整当前指纹与状态](E:/Win共享文件/语音共享文件/deliverables/2026-10-30_board_owner/integration/dialogue_repair/joint_balance_20261101/joint_balance_status.json)

性能对照来自字幕修复前的两段60秒窗口，属于描述性对照；本轮未重测超过五分钟摘要检索、声纹校准或多小时稳定性。以下旧版本段落保留其原保存时点的含义。
<!-- /joint-balance-subtitle-complete-20261101 -->

'''.encode('utf-8')
assert target.read_bytes() == original, 'Index changed during preparation; preserve the new version first.'
target.write_bytes(prefix + original)
assert target.read_bytes()[len(prefix):] == backup.read_bytes()
record = dict(schema='aura-analysis-index-completed-entry-1', target=str(target), backup=str(backup),
    original_sha256=hashlib.sha256(original).hexdigest(),
    updated_sha256=hashlib.sha256(target.read_bytes()).hexdigest(), old_bytes_preserved=True,
    production_or_model_or_device_access=False)
(HERE/'ANALYSIS_INDEX_PUBLICATION.json').write_text(json.dumps(record, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps(record, ensure_ascii=False))
