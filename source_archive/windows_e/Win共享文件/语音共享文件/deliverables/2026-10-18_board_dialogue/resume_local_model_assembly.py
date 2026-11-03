"""Preserve and resume the migrated partial assembly instead of overwriting it."""
import ast
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
storage=json.loads((ROOT/'aura/config/model_storage.local.json').read_text(encoding='utf-8-sig'))
folder=Path(storage['weights_directory'])
script=folder/'download_model.py'
source=script.read_text(encoding='utf-8')
before="""    with temp.open('wb') as output:
        for part in sorted(PARTS.glob('*.part')):
            with part.open('rb') as source:
                while block := source.read(8 * 1024 * 1024):
                    digest.update(block)
                    output.write(block)
"""
after="""    resume = temp.stat().st_size if temp.exists() else 0
    if resume > SIZE:
        raise RuntimeError('Existing assembly exceeds expected size; preserved for inspection')
    if resume:
        with temp.open('rb') as existing:
            while block := existing.read(8 * 1024 * 1024):
                digest.update(block)
    position = 0
    with temp.open('ab') as output:
        for part in sorted(PARTS.glob('*.part')):
            part_size = part.stat().st_size
            if position + part_size > resume:
                with part.open('rb') as source:
                    source.seek(max(0, resume - position))
                    while block := source.read(8 * 1024 * 1024):
                        digest.update(block)
                        output.write(block)
            position += part_size
"""
if before not in source:
    raise RuntimeError('Unexpected assembly source; no modifications made')
updated=source.replace(before,after,1)
ast.parse(updated)
backup=folder/'download_model.before_local_assembly.py'
if not backup.exists():
    backup.write_text(source,encoding='utf-8')
script.write_text(updated,encoding='utf-8')
note=('大语言模型权重、下载分段和缓存已移出项目，当前目录为 '+str(folder)+
      '。Ollama模型库为 '+storage['ollama_directory']+'。项目只保留代码、路径配置和验证记录。\n')
(folder/'README.md').write_text(note,encoding='utf-8')
print('Local model assembly preserves and resumes existing bytes:',folder)
