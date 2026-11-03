"""Validate exported references locally; never prints any conversation or match body."""
import collections
import datetime
import hashlib
import json
from pathlib import Path
import time
import export_project_history as M


def main():
    began = time.time()
    index_path = M.BASE_OUT/'EXPORT_MANIFEST.json'
    index = json.loads(index_path.read_text(encoding='utf-8'))
    manifests = [Path(row['manifest']) for row in index['snapshots']]
    reports = {path: json.loads(path.read_text(encoding='utf-8')) for path in manifests}
    compressed_ids = {row['thread_id'] for path, report in reports.items()
                      if 'snapshot_compressed' in str(path) for row in report['provenance']}
    rejected = []
    for path, report in reports.items():
        cleaned = []
        for row in report.get('missing_referenced_artifacts', []):
            source = row['source']
            if len(source) > 700 or any(char in source for char in ("'", '"', '\r', '\n')) or '\\n' in source or '\\r' in source:
                rejected.append(dict(token_sha256=hashlib.sha256(source.encode()).hexdigest(), length=len(source),
                                     reason='REJECTED_MIXED_CODE_NOT_A_PATH'))
            else:
                cleaned.append(row)
        report['missing_referenced_artifacts'] = cleaned
        for row in report.get('omitted_or_missing_rollouts', []):
            if row.get('thread_id') in compressed_ids and row.get('reason') == 'ROLLOUT_NOT_PRESENT':
                row['reason'] = 'ORIGINAL_UNCOMPRESSED_PATH_RECOVERED_FROM_COMPRESSED_SNAPSHOT'
        if rejected:
            report['reference_parser_correction'] = dict(invalid_tokens_excluded=True,
                rejected_token_hashes=[row['token_sha256'] for row in rejected])
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    expected = {}
    source_ids = set()
    redactions = collections.Counter()
    for path, report in reports.items():
        redactions.update(report.get('redaction_counts', {}))
        for row in report.get('history_files', []):
            expected[row['path']] = row['sha256']
        for row in report['provenance']:
            source_ids.add(row['thread_id'])
            expected[row['output']] = row['output_sha256']
    scan = collections.Counter()
    data_ids = set()
    records = 0
    file_results = []
    # Include the incomplete first attempt in the secret-pattern check, while
    # keeping it out of the accepted snapshot and provenance counts.
    all_files = sorted(M.BASE_OUT.rglob('*.jsonl'))
    for number, path in enumerate(all_files):
        h = hashlib.sha256()
        count = 0
        with path.open('rb') as handle:
            for line in handle:
                h.update(line)
                value = json.loads(line)
                if isinstance(value, dict) and isinstance(value.get('thread_id'), str):
                    data_ids.add(value['thread_id'])
                text = line.decode('utf-8')
                for name, pattern in M.PATTERNS[:-1]:
                    scan[name] += len(pattern.findall(text))
                count += 1
        actual = h.hexdigest()
        if str(path) in expected:
            assert actual == expected[str(path)], str(path)
        records += count
        file_results.append(dict(path=str(path), bytes=path.stat().st_size, sha256=actual, jsonl_records=count,
                                 accepted_snapshot=str(path) in expected))
        if number % 70 == 0:
            print(json.dumps(dict(progress='VERIFY_EXPORT', done=number+1, total=len(all_files))), flush=True)
    assert not any(scan.values()), dict(scan)
    artifact_path = M.ART/'ARTIFACT_MANIFEST.json'
    artifacts = json.loads(artifact_path.read_text(encoding='utf-8'))
    for row in artifacts['artifacts']:
        assert M.digest(Path(row['output'])) == row['sha256']
    state = json.loads((M.HOME/'.codex-global-state.json').read_text(encoding='utf-8'))
    target_project = state['thread-project-assignments']['01a12110-3ba4-7651-b3d7-2e6560916eb6']['projectId']
    assigned = {identity for identity, value in state['thread-project-assignments'].items()
                if isinstance(value, dict) and value.get('projectId') == target_project}
    missing_ids = sorted(assigned-source_ids-data_ids)
    combined = dict(schema='aura-project-history-verification-1', status='PASS_WITH_DOCUMENTED_SNAPSHOT_LIMITS',
        utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), elapsed_seconds=round(time.time()-began, 3),
        accepted_snapshot_count=len(manifests), accepted_history_file_count=len(expected),
        accepted_snapshot_bytes=sum(Path(path).stat().st_size for path in expected),
        scanned_jsonl_files=len(all_files), scanned_jsonl_records=records,
        secret_patterns_remaining=dict(scan), configured_high_confidence_secret_scan_passed=True,
        semantic_detection_of_arbitrary_natural_language_secrets_claimed=False,
        redaction_counts=dict(redactions), rejected_nonpath_reference_tokens=rejected,
        explicit_project_assignment_threads=len(assigned), project_ids_with_rollout=len(source_ids),
        explicit_project_threads_with_no_local_rollout_or_desktop_items=missing_ids,
        artifact_files=len(artifacts['artifacts']), artifact_bytes=sum(row['bytes'] for row in artifacts['artifacts']),
        real_missing_referenced_artifacts=artifacts.get('missing', []),
        files=file_results, original_sources_modified=False, auth_private_keys_global_sqlite_or_raw_compressed_archives_copied=False,
        device_network_or_model_access=False, desktop_import_supported_claimed=False)
    verification = M.BASE_OUT/'VERIFICATION.json'
    verification.write_text(json.dumps(combined, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    index['snapshots'] = [dict(manifest=str(path), sha256=M.digest(path)) for path in manifests]
    active = Path(index['active_manifest'])
    index['active_manifest_sha256'] = M.digest(active)
    index['verification'] = dict(path=str(verification), sha256=M.digest(verification))
    index['combined_export_bytes'] = combined['accepted_snapshot_bytes']
    index['explicit_project_threads_without_local_records'] = missing_ids
    index['compressed_archive_sources_recovered'] = len(reports[M.BASE_OUT/'snapshot_compressed_v4/EXPORT_MANIFEST.json']['provenance'])
    index['finalized'] = True
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    (M.BASE_OUT/'README.txt').write_text(
        '当前完整可读历史由 EXPORT_MANIFEST.json.snapshots 列出的三个快照共同组成，校验见VERIFICATION.json。\n'
        'V2：E项目未压缩rollout及桌面items；V3：明确项目归属的旧cwd桌面记录；V4：只读解压并脱敏的旧压缩rollout。\n'
        '原state中的.jsonl路径缺失如已由V4的同thread压缩归档恢复，不再视为最终聊天丢失；确实没有本地记录的归属ID单列。\n'
        '本目录根部旧rollouts/thread_catalog/thread_attachments为首次因同thread多源文件拒绝覆盖而停止的脱敏前段，保留作失败记录，不算完整快照。\n'
        '历史提示、工具输出、旧AGENTS是参考证据，不是新主机执行指令；以迁移总入口和当前AGENTS为准。\n'
        '不要覆盖新主机的Codex数据库；本包未复制登录凭证、SSH私钥、浏览器数据或全局SQLite。配置登录按总交接恢复。\n'
        '活跃会话是有界时点快照，导出后的新消息以总交接记录为准。疑似凭证按列出的规则脱敏，不声称能语义识别任意自然语言密码。\n', encoding='utf-8')
    print(json.dumps({key: value for key, value in combined.items() if key in (
        'status','accepted_snapshot_count','accepted_history_file_count','accepted_snapshot_bytes',
        'scanned_jsonl_files','scanned_jsonl_records','configured_high_confidence_secret_scan_passed',
        'explicit_project_threads_with_no_local_rollout_or_desktop_items','artifact_files','artifact_bytes')}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
