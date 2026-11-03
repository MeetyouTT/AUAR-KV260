"""Prepend one current migration pointer while preserving every prior document byte."""
import hashlib
import json
from pathlib import Path

package=Path(__file__).resolve().parents[1]
root=package.parent
archive=package/'verification/entry_backups'
archive.mkdir(parents=True,exist_ok=True)
marker='<!-- 5090-migration-current-20261101 -->'
text=f'''{marker}
2026-11-01最新接续：后续工作与Windows模型服务迁往5090 Laptop主机，旧机可能不再启用。先读[5090换机入口]({(package/'00_先读.md').as_posix()})与[新主机Codex提示词]({(package/'01_给新主机Codex的提示词.txt').as_posix()})。完整载荷是整个Win共享文件目录。

转轴接入优先、记忆验收后置。最新设备状态以axis_priority_20261101/HANDOFF_5090.txt为准：只完成一次两秒初始化及STOP，实物未观察清楚；重复/方向/本boot跟随未完成。迁移末次SSH未连通，当前在线/boot/输出不能新鲜确认。ec12文件已应用但GUI因MCP01尚未READY；重启回benchmark的持久接入仍待处理。以下旧READY、PID、时间窗和性能段落按历史理解，不代替新机核验。

LLM权重/Ollama仍按原约定在共享目录外，下载/恢复记录随包；登录凭证、SSH私钥、不可移植venv不复制。已补存的普通资源、环境清单、配置、会话导出及校验报告见迁移包清单。
<!-- /5090-migration-current-20261101 -->

'''.encode('utf-8')
targets=['AGENTS.md','README.md','后续任务_先读这里.md','语音共享文件/AGENTS.md','语音共享文件/README.md','语言模型分析/README.md']
records=[]
for relative in targets:
    path=root/relative
    old=path.read_bytes()
    if marker.encode() in old:
        raise RuntimeError('Migration entry already exists; do not duplicate.')
    saved=archive/relative
    saved.parent.mkdir(parents=True,exist_ok=True)
    with saved.open('xb') as f:
        f.write(old)
    assert path.read_bytes()==old
    path.write_bytes(text+old)
    assert path.read_bytes()[len(text):]==saved.read_bytes()
    records.append(dict(path=relative,before_sha256=hashlib.sha256(old).hexdigest(),
                        after_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),old_bytes_preserved=True))
(package/'verification/ENTRY_UPDATES.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(updated=len(records),original_bytes_archived=True)))
