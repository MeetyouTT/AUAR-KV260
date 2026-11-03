"""Local source and whitelisted runtime-log metadata, without inference/device calls."""
import hashlib
import json
from pathlib import Path
import re
import statistics

PROJECT = Path(r'E:\Win共享文件\语音共享文件')
REPAIR = PROJECT / 'deliverables/2026-10-30_board_owner/integration/dialogue_repair'
OUTPUT = Path(__file__).resolve().parent
INDEX = REPAIR / 'jpeg_demand_review_v20/SOURCE_AUDIT.json'
COMPONENTS = [
    'common/board_memory.py', 'common/board_memory_backoff.py',
    'board/runtime/board_business.py', 'board/runtime/board_memory_policy.py',
    'board/runtime/audio/board_dialogue_jobs.py', 'board/runtime/board_dialogue.py',
    'tools/board_business_gui.py', 'tools/voice_first_recording.py',
    'common/inference_output_contract.py',
]


def main():
    index = json.loads(INDEX.read_text(encoding='utf-8'))
    by_component = {row['component']: row for row in index['files']}
    records = []
    for component in COMPONENTS:
        row = by_component[component]
        digest = hashlib.sha256(Path(row['path']).read_bytes()).hexdigest()
        if digest != row['sha256']:
            raise RuntimeError('Saved source no longer matches its pinned component')
        records.append(dict(component=component, path=row['path'], sha256=digest))
    for relative in ['tools/model_inference_host.py', 'tools/dialogue_host_ollama.py',
                     'common/inference_output_contract.py']:
        path = PROJECT / 'aura' / relative
        records.append(dict(component='windows-local:' + relative, path=str(path),
                            sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                            active_windows_process_binding_verified=False))

    # The existing log can contain private prompt bodies. Never return or copy
    # lines: collect only fixed numeric process/cache metadata and event counts.
    log = PROJECT / 'deliverables/2026-10-18_board_dialogue/project_ollama_stderr.log'
    size_before = log.stat().st_size
    latest = dict(start_line=None, launch_numeric_args={}, ram_cache_mib=None,
                  event_counts={}, cache_update_wall_ms={})
    update_durations = []
    with log.open(encoding='utf-8', errors='replace') as stream:
        for number, line in enumerate(stream, 1):
            if 'starting llama-server' in line or 'starting llama server' in line:
                args = {}
                for flag, key in [('c', 'context_size'), ('np', 'parallel'), ('t', 'threads')]:
                    match = re.search(r'(?<![\w-])-' + flag + r'\s+(\d+)', line)
                    if match:
                        args[key] = int(match[1])
                latest = dict(start_line=number, launch_numeric_args=args, ram_cache_mib=None,
                              event_counts={}, cache_update_wall_ms={})
                update_durations = []
            if not re.match(r'^(?:srv\s|slot\s|main:)', line):
                continue
            if 'prompt cache is enabled' in line:
                match = re.search(r'size limit:\s*(\d+)\s*MiB', line)
                latest['ram_cache_mib'] = int(match[1]) if match else None
            for term in ['updating prompt cache', 'selected slot by LCP similarity', 'selected slot by LRU']:
                if term in line:
                    latest['event_counts'][term] = latest['event_counts'].get(term, 0) + 1
            match = re.search(r'prompt cache update took\s+([0-9.]+) ms', line)
            if match:
                update_durations.append(float(match[1]))
    if update_durations:
        latest['cache_update_wall_ms'] = dict(count=len(update_durations),
            median=statistics.median(update_durations), maximum=max(update_durations))
    evidence = dict(schema='aura.memory-idle-cache-source-review.v1',
        status='READ_ONLY_SCHEDULING_CONFIRMED_CACHE_LATENCY_CAUSE_UNPROVEN',
        startup_sha256=index['startup_sha256'], source_mapping_sha256=index['source_mapping_sha256'],
        baseline_scope='Saved v20 board components; original owner reports memory components unchanged in v21',
        sources=records,
        log=dict(path=str(log), bytes_before=size_before, bytes_after=log.stat().st_size,
            latest_startup_segment=latest, task_attribution_available=False,
            active_pid_build_binding_checked=False, raw_log_lines_exported=False),
        model_requests_sent=False, device_connections_opened=False, product_sources_modified=False,
        observations=dict(worker_poll_interval_seconds=3, worker_max_events=2,
            successful_batch_cooldown_seconds=0, failure_backoff_max_seconds=60,
            quiet_grace_in_existing_memory_idle_gate=False,
            quiet_listening_and_paused_allowed_by_capture_idle=True,
            existing_last_voice_activity_is_last_playback_ack=False,
            camera_structured_summary_can_skip_model=True,
            memory_completed_counter_proves_llm_request=False,
            single_active_slot_proves_all_prior_kv_unrecoverable=False,
            existing_host_stream_observation_supports_optional_cached_token_count=True,
            saved_normal_board_dialogue_explicitly_selects_output_format=False),
        official_reference_scope='Current official source/docs only, not an exact installed-binary source match',
        official_references=[
            'https://github.com/ollama/ollama/blob/main/llm/llama_server.go',
            'https://github.com/ggml-org/llama.cpp/blob/master/tools/server/server-context.cpp',
            'https://docs.ollama.com/api/chat', 'https://docs.ollama.com/faq'])
    (OUTPUT / 'SOURCE_EVIDENCE.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(status=evidence['status'], pinned_board_sources=len(COMPONENTS),
                         latest_log_cache_metadata=latest)))


if __name__ == '__main__':
    main()
