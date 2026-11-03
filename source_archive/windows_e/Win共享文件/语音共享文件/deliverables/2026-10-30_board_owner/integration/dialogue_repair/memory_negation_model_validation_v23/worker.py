"""Bounded public summary calls through the unchanged production HTTP client.

The default only validates a saved public payload. Root alone enables calls
after a normal GUI close. No Store or runtime instance is created.
"""
import argparse
import contextlib
import copy
import hashlib
import importlib
import json
import os
from pathlib import Path
import signal
import sys
import threading
import time
import types
import uuid


SPEC_SHA = 'ecdc034bd06cdd15bffe004a3ac1be3a6bc350dc3c879d91d3a19403f5c0f74a'
STARTUP = '48cb1a3a1fc62eae32c93a5be02df0bd60926cd064884a06990dd24b62762885'
BOOT = 'bebd3e7d-e984-4517-8cbb-211df7f1c6dc'
BEFORE = {
    'common.board_memory': ('common/board_memory.py', '05095d249caf3598802d5951910b412affe167b508933c7e831e3ffacc4fc0d0'),
    'board.runtime.board_memory_policy': ('board/runtime/board_memory_policy.py', '410e5b3eaf7986be6baa68d148469eb33443654ed0db597004518877732533c5'),
}
CLIENT_SHA = '600e044dedfc90c70e319e0e91999b8b4b7f648e0a5ca98e2a1bc0ab09a076b2'
LOCKS = ('/run/aura-avatar-ui.lock', '/home/root/.local/share/aura-board-business/writer.lock',
         '/home/root/.local/share/aura-board-business/speaker/speaker-writer.lock')
PREFERENCE = '/home/root/.local/share/aura-board-business/listening_preference.json'
AUDIT_PHASE = 'summary'


def need(value, code):
    if not value:
        raise ValueError(code)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def parse(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            need(key not in result, 'duplicate_json_field')
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=unique,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite_json_value')))


def read_payload(path, expected):
    raw = path.read_bytes()
    need(len(raw) <= 2 * 1024 * 1024 and digest(raw) == expected, 'exact_bounded_payload_required')
    payload = parse(raw)
    need(payload['schema'] == 'aura.public-memory-model-probe.v23' and payload['public_cases_only'] is True,
         'public_fixture_payload_required')
    need(digest(payload['spec_raw'].encode()) == SPEC_SHA and payload['final_summary_max_utf8_bytes'] == 301,
         'production_v22_spec_and_capacity_required')
    spec = parse(payload['spec_raw'])
    need(spec['startup_sha256'] == STARTUP and spec['boot_id'] == BOOT
         and spec['camera_owner']['camera_pid'] == 229296
         and str(spec['camera_owner']['camera_start_ticks']) == '2474670', 'exact_live_baseline_required')
    need(digest(payload['guard_source'].encode()) == payload['guard_sha256'], 'guard_source_changed')
    need(payload['mode'] in ('before', 'candidate') and 1 <= len(payload['cases']) <= 11, 'bounded_mode_and_cases_required')
    for case in payload['cases']:
        need(set(case) == {'case', 'sources', 'semantic_review_rubric'}
             and isinstance(case['case'], str) and isinstance(case['semantic_review_rubric'], str), 'public_case_shape_required')
        need(1 <= len(case['sources']) <= 4, 'bounded_public_source_count_required')
        for source in case['sources']:
            need(set(source) == {'source', 'text', 'protected'} and source['source'] == 'user_said'
                 and isinstance(source['text'], str) and 0 < len(source['text'].encode()) <= 4096
                 and isinstance(source['protected'], dict), 'public_text_source_required')
    need(len({case['case'] for case in payload['cases']}) == len(payload['cases']), 'duplicate_case')
    need(set(payload['candidate_sources']) == (set(BEFORE) if payload['mode'] == 'candidate' else set()),
         'exact_two_source_overlay_or_original_required')
    for name, record in payload['candidate_sources'].items():
        need(record['before_sha256'] == BEFORE[name][1] and digest(record['source'].encode()) == record['sha256'],
             'candidate_source_digest_changed')
    return payload, spec


@contextlib.contextmanager
def isolated_project_imports():
    roots = ('board', 'common', 'tools')
    selected = lambda name: name.split('.', 1)[0] in roots
    saved = {name: module for name, module in sys.modules.items() if selected(name)}
    packages = [(module, dict(module.__dict__)) for module in saved.values() if hasattr(module, '__path__')]
    old_path = list(sys.path)
    try:
        for name in saved:
            sys.modules.pop(name)
        yield
    finally:
        for name in list(sys.modules):
            if selected(name):
                sys.modules.pop(name)
        sys.modules.update(saved)
        for module, attributes in packages:
            module.__dict__.clear()
            module.__dict__.update(attributes)
        sys.path[:] = old_path


@contextlib.contextmanager
def metadata_guard_imports():
    global AUDIT_PHASE
    previous = AUDIT_PHASE
    AUDIT_PHASE = 'metadata_guard'
    try:
        with isolated_project_imports():
            yield
    finally:
        AUDIT_PHASE = previous


def prohibit_private_data_and_devices(event, args):
    # ctypes imports PyDLL(None) for Python's own C API. The inherited guard's
    # pure Seed structure import needs this, without loading a native library.
    current_process_api = event == 'ctypes.dlopen' and AUDIT_PHASE == 'metadata_guard' and args[0] is None
    if event == 'sqlite3.connect' or event == 'ctypes.dlopen' and not current_process_api:
        raise RuntimeError('public_probe_database_or_native_initialization_forbidden')
    if event == 'open' and isinstance(args[0], (str, bytes, os.PathLike)):
        path = os.fsdecode(args[0]).lower()
        if path.startswith('/dev/') or any(path.endswith(suffix) for suffix in ('.db', '.sqlite', '.sqlite3', '-wal', '-shm')):
            raise RuntimeError('public_probe_private_database_or_device_read_forbidden')


def saved_pause():
    path = Path(PREFERENCE)
    need(path.resolve() == path and not path.is_symlink(), 'saved_preference_path_changed')
    raw = path.read_bytes()
    value = parse(raw)
    need(set(value) == {'version', 'enabled'} and type(value['version']) is int
         and value['version'] == 1 and value['enabled'] is False, 'saved_user_pause_required')
    return digest(raw)


def fast_guard(context, journal_before, preference_sha):
    context['boot']()
    current = context['journal']()
    need(current == journal_before and current['phase'] == 'NORMAL_CLOSED'
         and current.get('guard_removed') is False, 'normal_close_guard_or_journal_changed')
    unit = context['guarded'](current)
    context['ownerless'](unit)
    need(saved_pause() == preference_sha, 'saved_pause_changed')


def load_overlay(name, record):
    parent_name, attribute = name.rsplit('.', 1)
    parent = importlib.import_module(parent_name)
    module = types.ModuleType(name)
    module.__package__ = parent_name
    module.__file__ = '<public-memory-v23-candidate/' + name.replace('.', '/') + '.py>'
    sys.modules[name] = module
    setattr(parent, attribute, module)
    try:
        exec(compile(record['source'], module.__file__, 'exec'), module.__dict__)
    except BaseException:
        sys.modules.pop(name, None)
        if getattr(parent, attribute, None) is module:
            delattr(parent, attribute)
        raise
    return module


def prepared_case(case, memory):
    sources = [dict(event_id='public-v23-' + case['case'] + '-' + str(index), revision=1,
        include_in_summary=True, source=row['source'], text=row['text'], metadata=copy.deepcopy(row['protected']),
        recorded_utc=1700000000.0 + index) for index, row in enumerate(case['sources'], 1)]
    return dict(schema_version=memory.SCHEMA_VERSION, scope={'kind': 'conversation', 'id': 'public-v23-' + case['case']},
        topic='公开摘要验证', start_utc=1700000000.0, end_utc=1700000000.0 + len(sources), sources=sources,
        required_claims=memory.BoardMemoryStore._required_claims(sources))


class RecordingClient:
    def __init__(self, client, guard):
        self.client, self.guard = client, guard
        self.calls = []
        self.cancel_count = 0

    def request(self, kind, payload, *, deadline, cancelled):
        self.guard()
        need(kind == 'llm' and payload['task'] == 'summary'
             and payload['board_boot_id'].startswith('public-memory-v23-')
             and payload['options'] == {'num_predict': 384}, 'original_public_summary_request_required')
        exported = parse(payload['messages'][-1]['content'])['sources']
        stage = 'single'
        if all(item.get('source') == 'summary_fragment' for item in exported):
            stage = 'reduction'
        elif any('alias' in item for item in exported):
            stage = 'fragment'
        row = {'index': len(self.calls) + 1, 'stage': stage,
               'request': copy.deepcopy(payload), 'started_mono': time.monotonic()}
        self.calls.append(row)
        try:
            result = self.client.request(kind, payload, deadline=deadline, cancelled=cancelled)
            row['response'] = copy.deepcopy(result)
            self.guard()
            return result
        except Exception as exc:
            row['exception_class'] = type(exc).__name__
            raise
        finally:
            row['elapsed_seconds'] = time.monotonic() - row['started_mono']

    def cancel(self, owner):
        self.cancel_count += 1
        return self.client.cancel(owner)


def execute_cases(payload, spec, guard, cancelled):
    runtime = Path(spec['target']) / 'runtime/aura'
    with isolated_project_imports():
        sys.path.insert(0, str(runtime))
        for name, (relative, expected) in BEFORE.items():
            need(digest((runtime / relative).read_bytes()) == expected, 'actual_summary_source_changed')
        need(digest((runtime / 'board/runtime/board_dialogue_client.py').read_bytes()) == CLIENT_SHA,
             'actual_inference_client_changed')
        if payload['mode'] == 'candidate':
            memory = load_overlay('common.board_memory', payload['candidate_sources']['common.board_memory'])
            policy = load_overlay('board.runtime.board_memory_policy', payload['candidate_sources']['board.runtime.board_memory_policy'])
        else:
            memory = importlib.import_module('common.board_memory')
            policy = importlib.import_module('board.runtime.board_memory_policy')
        client_module = importlib.import_module('board.runtime.board_dialogue_client')
        need(Path(client_module.__file__).resolve() == runtime / 'board/runtime/board_dialogue_client.py', 'runtime_client_import_changed')
        actual = client_module.InferenceHttpClient('192.168.50.1', 8797)
        client = RecordingClient(actual, guard)
        fake_boot = 'public-memory-v23-' + uuid.uuid4().hex
        summary = policy.BoardSummaryClient(client, board_boot_id=fake_boot, final_summary_max_utf8_bytes=301)
        need((summary.maximum, summary.reserve, summary.budget_ms, summary.max_calls, summary.total_budget_ms)
             == (2048, 384, 30000, 256, 900000), 'original_summary_defaults_changed')
        rows = []
        for case in payload['cases']:
            if cancelled():
                break
            guard()
            prepared = prepared_case(case, memory)
            start_call, started = len(client.calls), time.monotonic()
            row = {'case': case['case'], 'sources': case['sources'], 'semantic_review_rubric': case['semantic_review_rubric'],
                   'accepted': False, 'human_semantic_review': 'PENDING', 'store_instantiated': False}
            try:
                candidate = summary(prepared, cancelled)
                task = {'scope_kind': prepared['scope']['kind'], 'scope_id': prepared['scope']['id'],
                        'topic': prepared['topic'], 'start_utc': prepared['start_utc'], 'end_utc': prepared['end_utc']}
                memory.BoardMemoryStore._candidate(candidate, task, prepared['sources'])
                need(summary.metrics.get('complete_source_coverage') is True
                     and summary.metrics['covered_utf8_bytes'] == summary.metrics['input_utf8_bytes'], 'complete_source_coverage_required')
                row.update(accepted=True, candidate=candidate, source_refs_and_claims_checked=True)
            except Exception as exc:
                row.update(exception_class=type(exc).__name__, source_refs_and_claims_checked=False)
            row.update(elapsed_seconds=time.monotonic() - started, failure_metadata=summary.failure_metadata(),
                       summary_metrics=copy.deepcopy(summary.metrics), model_calls=client.calls[start_call:],
                       cancelled=cancelled())
            row['failure_code'] = ('none' if row['accepted'] else
                summary.failure_metadata()['code'] if summary.failure_metadata()['code'] != 'none' else 'public_post_validation_failed')
            rows.append(row)
            guard()
        return {'status': 'PUBLIC_CASES_FINISHED' if len(rows) == len(payload['cases']) and not cancelled() else 'PUBLIC_WINDOW_STOPPED',
                'mode': payload['mode'], 'public_board_boot_id': fake_boot, 'cases': rows,
                'actual_model_calls': len(client.calls), 'cancel_calls': client.cancel_count,
                'final_summary_max_utf8_bytes': 301, 'production_summary_defaults_preserved': True,
                'store_runtime_or_device_instantiated': False, 'database_read': False,
                'no_production_transcripts_or_database_read': True,
                'local_model_runtimes_initialized': False,
                'guard_reads_inherited_source_configuration_and_model_pin_bytes': True,
                'production_changed': False,
                'GUI_restoration_performed': False, 'GUI_guard_retained': True,
                'human_semantic_review_required': True}


def execute(payload, spec, window_seconds):
    import fcntl
    need(sys.platform.startswith('linux') and os.geteuid() == 0, 'root_linux_execution_required')
    sys.dont_write_bytecode = True
    sys.addaudithook(prohibit_private_data_and_devices)
    stop = threading.Event()
    for name in (signal.SIGINT, signal.SIGTERM):
        signal.signal(name, lambda *_: stop.set())
    deadline = time.monotonic() + window_seconds
    cancelled = lambda: stop.is_set() or time.monotonic() >= deadline
    context = {'SPEC': spec, 'ACTION': 'ready', 'TOKEN': None, 'WINDOW': None, '__name__': '_public_memory_guard'}
    with contextlib.ExitStack() as stack:
        descriptor = os.open('/run/aura-production-publisher.lock', os.O_RDWR | os.O_NOFOLLOW)
        publisher = stack.enter_context(os.fdopen(descriptor, 'r+b'))
        fcntl.flock(publisher, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with metadata_guard_imports():
            exec(compile(payload['guard_source'], '<frozen-v22-readonly-guard>', 'exec'), context)
            context['boot']()
            context['source']()
            journal = context['journal']()
            need(journal['phase'] == 'NORMAL_CLOSED' and journal.get('guard_removed') is False,
                 'root_normal_WM_DELETE_close_required')
            context['inactive'](journal)
        preference_sha = saved_pause()
        for path in LOCKS:
            descriptor = os.open(path, os.O_RDWR | os.O_NOFOLLOW)
            lock = stack.enter_context(os.fdopen(descriptor, 'r+b'))
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        guard = lambda: fast_guard(context, journal, preference_sha)
        guard()
        try:
            result = execute_cases(payload, spec, guard, cancelled)
        finally:
            guard()
            with metadata_guard_imports():
                context['source']()
        result.update(actual_startup_sha256=STARTUP, actual_board_boot_id=BOOT, actual_camera_pid=229296,
                      actual_camera_birth_ticks=2474670, three_writer_locks_held=True,
                      full_source_guard_before_after=True, listening_preference_sha256=preference_sha,
                      listening_enabled=False, hard_outer_window_seconds=window_seconds)
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--payload', required=True, type=Path)
    parser.add_argument('--payload-sha256', required=True)
    parser.add_argument('--window-seconds', type=int, default=180)
    parser.add_argument('--execute-root-only', action='store_true')
    args = parser.parse_args()
    need(30 <= args.window_seconds <= 900, 'bounded_outer_window_required')
    payload, spec = read_payload(args.payload, args.payload_sha256)
    if not args.execute_root_only:
        print(json.dumps({'status': 'DRY_VALIDATED_NO_DEVICE_OR_MODEL_ACCESS', 'mode': payload['mode'],
                          'cases': [case['case'] for case in payload['cases']], 'final_summary_max_utf8_bytes': 301}))
        return
    result = execute(payload, spec, args.window_seconds)
    result['payload_sha256'] = args.payload_sha256
    print(json.dumps(result, ensure_ascii=True, allow_nan=False), flush=True)


if __name__ == '__main__':
    main()
