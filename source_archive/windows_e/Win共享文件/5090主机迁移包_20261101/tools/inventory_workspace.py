"""Inventory the in-place workspace payload without following junctions or reading databases."""
import hashlib
import json
import os
from pathlib import Path
import stat
import time

PACKAGE = Path(__file__).resolve().parents[1]
ROOT = PACKAGE.parent
DEST = PACKAGE/'verification'
DEST.mkdir(parents=True, exist_ok=True)
text_extensions = {'.py','.ps1','.sh','.json','.jsonl','.md','.txt','.toml','.yaml','.yml',
                   '.c','.h','.cpp','.hpp','.v','.sv','.xdc','.tcl','.ini','.cfg','.bat','.cmd'}
manifest = DEST/'WORKSPACE_FILES.jsonl'
counts = dict(files=0,bytes=0,hashed_files=0,hashed_bytes=0,changed_during_read=0)
links, errors, excluded = [], [], []
stack = [ROOT]
with manifest.open('w',encoding='utf-8') as output:
    while stack:
        directory = stack.pop()
        try:
            entries = list(os.scandir(directory))
        except OSError as exc:
            errors.append(dict(path=str(directory),error=type(exc).__name__))
            continue
        for entry in entries:
            path = Path(entry.path)
            relative = str(path.relative_to(ROOT))
            try:
                info = entry.stat(follow_symlinks=False)
                reparse = bool(getattr(info,'st_file_attributes',0)&0x400)
                if reparse or entry.is_symlink():
                    links.append(dict(path=relative,followed=False))
                    continue
                if entry.is_dir(follow_symlinks=False):
                    if path == PACKAGE or entry.name == '.verysync':
                        excluded.append(relative)
                    else:
                        stack.append(path)
                    continue
                if not stat.S_ISREG(info.st_mode):
                    continue
                row = dict(path=relative,bytes=info.st_size,mtime_ns=info.st_mtime_ns)
                counts['files'] += 1
                counts['bytes'] += info.st_size
                if path.suffix.lower() in text_extensions and info.st_size <= 4*1024*1024:
                    raw = path.read_bytes()
                    after = path.stat()
                    if (info.st_size,info.st_mtime_ns) == (after.st_size,after.st_mtime_ns):
                        row['sha256'] = hashlib.sha256(raw).hexdigest()
                        counts['hashed_files'] += 1
                        counts['hashed_bytes'] += len(raw)
                    else:
                        row['changed_during_read'] = True
                        counts['changed_during_read'] += 1
                output.write(json.dumps(row,ensure_ascii=False)+'\n')
            except OSError as exc:
                errors.append(dict(path=relative,error=type(exc).__name__))
required = ['AGENTS.md','语音共享文件/AGENTS.md','语音共享文件/start_inference.ps1',
            '语音共享文件/aura/config/model_storage.local.json',
            '语音共享文件/aura/config/model_inference.local.json','语言模型分析/README.md',
            '协作任务/2026-10-30_Codex跨机协作/windows-connection.json',
            '语音共享文件/deliverables/2026-10-31_visual_axis_maintenance/reviews/axis_priority_20261101/CURRENT_MIGRATION_STATE.json']
critical = []
for name in required:
    path=ROOT/name
    row=dict(path=name,exists=path.is_file())
    if row['exists']:
        raw=path.read_bytes()
        row.update(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
    critical.append(row)
report = dict(schema='aura-inplace-workspace-inventory-1',root=str(ROOT),
    status='INVENTORIED' if not errors and all(r['exists'] for r in critical) else 'INVENTORIED_WITH_GAPS',
    counts=counts, critical_files=critical, reparse_entries_not_followed=links,
    skipped_directories=excluded, errors=errors,
    manifest=str(manifest), manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),
    entire_workspace_is_payload_not_only_migration_subfolder=True,
    large_files_are_size_mtime_only_unless_separately_hashed=True,
    database_payloads_not_read=True, files_deleted_or_moved=False)
(DEST/'WORKSPACE_INVENTORY.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(status=report['status'],counts=counts,errors=len(errors),reparse_entries=len(links),
                     critical_missing=[r['path'] for r in critical if not r['exists']]),ensure_ascii=False))
