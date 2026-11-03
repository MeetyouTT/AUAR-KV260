"""Write ONLY synthetic and public-source evidence beneath this directory."""
import ast
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import re
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parent
AURA = ROOT.parents[4] / 'aura'
sys.path[:0] = [str(ROOT / 'candidate'), str(ROOT)]
from dialogue_chunk_policy import segment_reply
from supply_budget import estimate_supply
from build_review_patch import EXPECTED, REFERENCE


def save(name, value):
    (ROOT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    log = io.StringIO()
    suite = unittest.defaultTestLoader.discover(str(ROOT / 'tests'), pattern='test_candidate.py')
    started = time.perf_counter()
    result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    elapsed = time.perf_counter() - started
    (ROOT / 'offline_tests.log').write_text(log.getvalue(), encoding='utf-8')
    validation = dict(status='PASS' if result.wasSuccessful() else 'FAIL', tests=result.testsRun,
        failures=len(result.failures), errors=len(result.errors), seconds=round(elapsed, 4),
        python=sys.version.split()[0], platform='Windows synthetic stdlib tests; NOT ARM runtime validation',
        run_utc=datetime.now(timezone.utc).isoformat(),
        first_attempt=dict(tests=32, failures=1, fixed='Parenthesized sentence punctuation must not detach the following main clause'),
        property_cases=dict(generated_text_partitions=1000, generated_arrival_traces=200),
        model_requests=0, device_operations=0, database_accesses=0, production_changes=0,
        command='python -B write_offline_evidence.py')
    save('VALIDATION.json', validation)
    if not result.wasSuccessful():
        print(json.dumps(validation))
        raise SystemExit(1)

    source = REFERENCE.read_bytes()
    if hashlib.sha256(source).hexdigest() != EXPECTED:
        raise ValueError('reference_source_changed')
    node = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == 'split_sentences')
    namespace = {'re': re, 'ReplyRejected': ValueError}
    exec(compile(ast.Module(body=[node], type_ignores=[]), 'pinned_split_sentences_only', 'exec'), namespace)
    baseline_split = namespace['split_sentences']
    examples = [
        ('BRIEF', '今天也很高兴见到你。'),
        ('SHORT_ACK', '好的！我会先核对版本，再继续处理。最后把结果告诉你。'),
        ('SHORT_TAILS', '我建议今天先休息一下。第二句。第三句。第四句。'),
        ('QUOTED_SENTENCES', '她说：“先停一下！再核对版本。”确认后才继续。最后说明结果。'),
        ('NUMERIC_URL', '温度是3.14度。请看https://example.org/path?a=1&b=2，之后再确认。'),
        ('LONG_PHRASES', '第一部分，' * 30 + '结束。第二部分，' * 5 + '结束。'),
    ]
    text_rows = []
    for code, text in examples:
        before, after = baseline_split(text), segment_reply(text)
        text_rows.append(dict(case_code=code, synthetic=True, characters=len(text),
            baseline_calls=len(before), candidate_calls=len(after),
            baseline_chunk_chars=[len(part) for part in before],
            candidate_chunk_chars=[len(part) for part in after],
            exact_character_preservation=''.join(before) == ''.join(after) == text))
    arrivals = {
        'REGULAR': [dict(arrival_ms=index * 20, samples=480) for index in range(20)],
        'JITTER_120MS': [dict(arrival_ms=at, samples=480) for at in (0, 20, 40, 180, 180, 180, 180)],
        'SUPPLY_DEFICIT_1980MS': [dict(arrival_ms=at, samples=480) for at in (0, 2000)],
        'BURST_400MS': [dict(arrival_ms=0, samples=480) for _ in range(20)],
    }
    supply = {code: [estimate_supply(records, start_reserve_ms=reserve).as_dict()
                      for reserve in (0, 80, 160, 240)] for code, records in arrivals.items()}
    pauses = [dict(continuation_pause_ms=pause, timeout_ms=timeout,
                   premature_end=timeout < pause, end_wait_ms=timeout,
                   evidence_kind='ANALYTIC_SYNTHETIC_PAUSE_ONLY_NO_AUDIO_OR_VAD_TEST')
              for pause in (400, 600, 800, 1200) for timeout in (500, 700, 900)]
    save('SYNTHETIC_COMPARISON.json', dict(
        evidence_kind='SYNTHETIC_ONLY_NO_TTS_ASR_GST_DEVICE_OR_SUBJECTIVE_QUALITY_MEASUREMENT',
        grouping=text_rows, supply_profiles=supply, timeout_tradeoff=pauses,
        constraints=['No claim of first-sound speedup', 'No throughput/voice-quality measurements',
                     'Extra start reserve costs the same amount of initial waiting',
                     'Packet arrival metadata must be post-fresh-check and on one board clock']))

    pins = json.loads((ROOT.parent / 'frontend_balance_candidate/baseline_manifest.json').read_text(encoding='utf-8-sig'))
    candidates = {
        'board/runtime/board_dialogue.py': REFERENCE,
        'board/runtime/audio/board_dialogue_jobs.py': ROOT.parent / 'guard_session_candidate/after/board/runtime/audio/board_dialogue_jobs.py',
        'tools/gstreamer_persistent_engine.py': AURA / 'tools/gstreamer_persistent_engine.py',
        'tools/streaming_controller.py': AURA / 'tools/streaming_controller.py',
        'tools/board_recording.py': ROOT.parent / 'instrumentation_candidate/after/tools/board_recording.py',
        'board/runtime/audio/board_asr.py': ROOT.parent.parent / 'response_latency/asr_threads_candidate/after/board/runtime/audio/board_asr.py',
        'tools/voice_first_recording.py': ROOT.parent / 'after/tools/voice_first_recording.py',
    }
    reviewed = []
    for target, path in candidates.items():
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        reviewed.append(dict(target=target, source_path=str(path), expected_sha256=pins['component_sha256'][target],
            reviewed_sha256=actual, matches_375_pin_manifest=actual == pins['component_sha256'][target]))
    host_sha = hashlib.sha256((AURA / 'tools/model_inference_host.py').read_bytes()).hexdigest()
    host_receipt = json.loads((ROOT.parent.parent / 'response_latency/STATUS.json').read_text(encoding='utf-8-sig'))
    save('SOURCE_REVIEW.json', dict(
        authority='root frontend_balance_candidate/baseline_manifest.json, not aura main tree',
        startup_sha256=pins['startup_sha256'], public_components=len(pins['component_sha256']), files=reviewed,
        windows_host=dict(path=str(AURA / 'tools/model_inference_host.py'),
            sha256=host_sha,
            matches_response_latency_installed_receipt=host_sha == host_receipt['windows']['host_source_sha256']),
        all_integration_sources_require_fresh_root_pin_check=True))

    artifacts = {}
    for path in sorted(ROOT.rglob('*')):
        staged_reference = any(part.startswith('patch_check_') for part in path.relative_to(ROOT).parts)
        if path.is_file() and path.suffix in ('.py', '.patch') and not staged_reference:
            artifacts[path.relative_to(ROOT).as_posix()] = dict(sha256=hashlib.sha256(path.read_bytes()).hexdigest(), bytes=path.stat().st_size)
    save('CANDIDATE_MANIFEST.json', dict(status='OFFLINE_PASS_REVIEW_ONLY_NOT_INSTALLED',
        root_publish_only=True, baseline_board_dialogue_sha256=EXPECTED, artifacts=artifacts,
        runtime_delta=['change _prepare model replies to split_dialogue_sentences; local handlers and baseline splitter unchanged',
                       'add board/runtime/dialogue_chunk_policy.py'],
        analysis_only=['candidate/supply_budget.py', 'candidate/metadata_contract.py'],
        reserved_untouched=['memory_health_collaboration', 'frontend_balance_candidate', 'all production sources and authoritative status']))
    print(json.dumps(validation))
    print(json.dumps({'grouping': text_rows}, ensure_ascii=False))
