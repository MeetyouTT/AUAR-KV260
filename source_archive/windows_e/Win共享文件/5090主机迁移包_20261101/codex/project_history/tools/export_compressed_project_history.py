"""Supplement explicitly selected Codex Zstd rollouts, without copying raw archives."""
import datetime
import hashlib
import json
from pathlib import Path
import shutil
import time
import export_project_history as M
import zstd_local as Z


def main():
    began = time.time()
    selected = json.loads((M.BASE_OUT/'COMPRESSED_SELECTION.json').read_text(encoding='utf-8'))
    out = M.BASE_OUT/'snapshot_compressed_v4'
    out.mkdir(exist_ok=True)
    sources = []
    failures = []
    for number, row in enumerate(selected['selected']):
        source = Path(row['source'])
        assert M.regular(source)
        target = out/'rollouts'/(row['thread_id']+'__'+hashlib.sha256(str(source).casefold().encode()).hexdigest()[:12]+'.jsonl')
        target.parent.mkdir(exist_ok=True)
        before = source.stat()
        raw_hash = M.digest(source)
        decompressed_hash = hashlib.sha256()
        records = 0
        try:
            with target.open('x', encoding='utf-8') as handle:
                for line in Z.lines(source):
                    decompressed_hash.update(line)
                    assert line.endswith(b'\n'), 'INCOMPLETE_COMPRESSED_ROLLOUT_LINE'
                    value = json.loads(line)
                    M.dump_line(handle, M.sanitize(value))
                    records += 1
            assert source.stat().st_size == before.st_size and source.stat().st_mtime_ns == before.st_mtime_ns
            sources.append(dict(source=str(source), thread_id=row['thread_id'], source_compressed_bytes=before.st_size,
                source_compressed_sha256=raw_hash, decompressed_source_sha256=decompressed_hash.hexdigest(),
                output=str(target), output_bytes=target.stat().st_size, output_sha256=M.digest(target), records=records))
        except Exception as error:
            failures.append(dict(source=str(source), output=str(target), error=type(error).__name__, complete=False))
        if number % 20 == 0:
            print(json.dumps(dict(progress='COMPRESSED_EXPORT', done=number+1, total=len(selected['selected']))), flush=True)
    artifacts = []
    missing = []
    for reference in sorted(M.REFERENCES):
        source = Path(reference)
        roots = [M.HOME/'visualizations', M.HOME/'generated_images']
        permitted = any(source.is_relative_to(root) for root in roots)
        permitted = permitted or (source.parent == Path(r'C:\Users\35870\AppData\Local\Temp')
                                 and source.name.lower().startswith(('codex-clipboard-', 'codex-imagegen')))
        if not permitted:
            continue
        if not source.exists():
            missing.append(dict(source=str(source), reason='REFERENCED_ATTACHMENT_NOT_PRESENT'))
            continue
        if not M.regular(source):
            missing.append(dict(source=str(source), reason='NOT_A_REGULAR_NON_REPARSE_FILE'))
            continue
        target = M.ART/'referenced_local'/hashlib.sha256(str(source).casefold().encode()).hexdigest()[:16]/source.name
        target.parent.mkdir(parents=True, exist_ok=True)
        source_sha = M.digest(source)
        if source.suffix.lower() in ('.html', '.svg'):
            clean = M.safe_string(source.read_text(encoding='utf-8'), collect=False)
            target.write_text(clean, encoding='utf-8')
        else:
            shutil.copy2(source, target, follow_symlinks=False)
            assert M.digest(target) == source_sha
        artifacts.append(dict(source=str(source), output=str(target), bytes=target.stat().st_size,
                              source_sha256=source_sha, sha256=M.digest(target),
                              text_credentials_redacted=source_sha != M.digest(target)))
    report = dict(schema='aura-compressed-project-history-migration-1', status='EXPORTED_REFERENCE_HISTORY_NOT_APP_IMPORT' if not failures else 'PARTIAL_COMPRESSED_EXPORT',
        created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), elapsed_seconds=round(time.time()-began, 3),
        selection='session_meta.cwd E workspace or explicit desktop project assignment',
        selected_sources=len(selected['selected']), exported_sources=len(sources), failures=failures,
        records=sum(row['records'] for row in sources), source_compressed_bytes=sum(row['source_compressed_bytes'] for row in sources),
        output_bytes=sum(row['output_bytes'] for row in sources), provenance=sources,
        redaction_counts=dict(M.COUNTS), artifacts=artifacts, missing_referenced_artifacts=missing,
        decoder=dict(dll_source=str(Z.DLL_SOURCE), dll_sha256=M.digest(Z.DLL_SOURCE), method='stdlib_ctypes_existing_git_libzstd'),
        compressed_originals_auth_private_keys_or_global_databases_copied=False,
        source_files_untouched=True, device_network_or_model_access=False)
    manifest = out/'EXPORT_MANIFEST.json'
    manifest.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    index_path = M.BASE_OUT/'EXPORT_MANIFEST.json'
    index = json.loads(index_path.read_text(encoding='utf-8'))
    index['snapshots'].append(dict(manifest=str(manifest), sha256=M.digest(manifest)))
    index['active_manifest'] = str(manifest)
    index['active_manifest_sha256'] = M.digest(manifest)
    index['active_snapshot'] = str(out)
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    artifact_index = M.ART/'ARTIFACT_MANIFEST.json'
    previous = json.loads(artifact_index.read_text(encoding='utf-8'))
    merged = {row['output']: row for row in previous.get('artifacts', [])}
    merged.update({row['output']: row for row in artifacts})
    artifact_index.write_text(json.dumps(dict(artifacts=list(merged.values()), missing=missing), ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    (out/'README.txt').write_text(
        '补充导出旧Codex压缩rollout；仅根据E目录cwd或明确项目归属选择，解压后与其他快照同样脱敏。\n'
        '使用旧机PortableGit已有libzstd，只读解压，不需要联网；没有把未脱敏原压缩文件迁到E。\n'
        '旧state库所列未压缩rollout路径可能已被Codex转换为.jsonl.zst；因此V3的ROLLOUT_NOT_PRESENT要结合本目录已恢复源检查，不等于聊天记录最终缺失。\n'
        '所有多个源版本保留路径哈希，不冒充桌面可直接导入。\n', encoding='utf-8')
    print(json.dumps(dict(status=report['status'], exported_sources=len(sources), records=report['records'],
                         output_bytes=report['output_bytes'], artifacts=len(artifacts), missing=len(missing),
                         manifest=str(manifest)), ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
