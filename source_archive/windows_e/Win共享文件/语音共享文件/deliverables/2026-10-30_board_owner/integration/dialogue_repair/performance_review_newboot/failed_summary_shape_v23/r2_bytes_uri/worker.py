"""One read-only failed-group diagnosis. Private text exists only in this child RAM."""
import contextlib
import hashlib
import http.client
import importlib
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import sys
import threading
import time
import uuid


DATABASE = Path('/home/root/.local/share/aura-board-business/timeline.sqlite3')
PREFERENCE = Path('/home/root/.local/share/aura-board-business/listening_preference.json')
CONTROL = Path('/home/root/aura-board-business-20261030/control-production-v1/state.json')
WORDS = ('没有', '不要', '不能', '不会', '不是', '尚未', '未完成', '不去', '不买', '不做',
         '未准备', '未能', '未校准', '未确认', '未购买', '未执行', '无法', '并非', '并未',
         '从未', '未曾', '不再', '未喝', '不可能', '不应', '不想', '不愿', '不需要', '无需',
         'not', 'never', 'no', '未', '没', '非', '无须', '不必', '否认', '否定', '拒绝',
         '缺少', '否', '不正常', '不', '无')
MARKERS = ('询问', '提问', '想知道', '是否', '能否', '?', '？', '无论', '不管', '不论')
REASONS = ('protected_name_missing', 'protected_number_missing_or_changed', 'negation_missing',
           'planned_status_missing', 'completed_status_missing', 'cancelled_status_missing',
           'observation_evidence_missing')
STAGES = ('idle', 'prepare', 'admission', 'model_request', 'wire_response', 'semantic_json',
          'semantic_shape', 'semantic_bounds', 'fragmentation', 'fragment_validation', 'reduction',
          'reduction_validation', 'full_source_validation', 'complete', 'selection', 'guard', 'other')
CLASSES = ('none', 'CandidateRejected', 'ContextLimitError', 'ModelRequestError', 'WireError',
           'InterruptedError', 'TimeoutError', 'RuntimeError', 'ValueError', 'TypeError', 'KeyError',
           'JSONDecodeError', 'OperationalError', 'DatabaseError', 'OSError', 'FileNotFoundError',
           'ConnectionError', 'ConnectionRefusedError', 'ConnectionResetError', 'Refused', 'other')
CODES = ('none', 'candidate_rejected', 'cancelled', 'deadline_exceeded', 'context_limit',
         'operation_failed', 'preempted', 'superseded', 'foreground_busy', 'backend_failed',
         'backend_invalid_result', 'gpu_busy', 'startup_busy', 'queue_full', 'owner_capacity',
         'duplicate_request', 'stale_generation', 'shutdown', 'other')
STATUSES = ('DIAGNOSIS_COMPLETE', 'NO_ELIGIBLE_FAILED_GROUP', 'GUARD_REFUSED',
            'DIAGNOSTIC_FAILED', 'OWNED_CHILD_WINDOW_EXPIRED', 'OUTPUT_CONTRACT_REFUSED')


class Refused(RuntimeError):
    pass


def need(value):
    if not value:
        raise Refused()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def parse(raw):
    def unique(pairs):
        value = {}
        for key, item in pairs:
            need(key not in value)
            value[key] = item
        return value
    return json.loads(raw, object_pairs_hook=unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(Refused()))


def enum(value, allowed):
    return value if type(value) is str and value in allowed else 'other'


def features(text, metadata, memory):
    need(type(text) is str and len(text.encode('utf8')) <= 8192 and isinstance(metadata, dict))
    counts = {word: (len(re.findall(r'\b' + word + r'\b', text, re.I))
                     if word in ('not', 'never', 'no') else text.count(word)) for word in WORDS}
    return dict(utf8_bytes=len(text.encode('utf8')), metadata_negated=int(metadata.get('negated') is True),
                negation_matches=len(list(memory.NEGATION.finditer(text))),
                polar_matches=len(list(memory.POLAR_QUESTION.finditer(text))), negative_form_counts=counts,
                nonassertive_marker_counts={marker: text.count(marker) for marker in MARKERS})


def empty_result(status='DIAGNOSTIC_FAILED'):
    return dict(status=status, accepted=0, sources=[], summary=None, calls=0, cancel_calls=0,
                request_cost=0, model_elapsed_seconds=0.0, source_complete_coverage=0,
                stage='idle', code='none', error_class='none', rejection_reasons=[],
                unknown_rejection_reasons=0, full_components_before=0, full_components_after=0,
                same_owners_before_after=0, saved_pause_preserved=0, database_connections=0,
                database_write_statements=0, final_summary_capacity=301, request_budget_ms=30000,
                max_calls=1, hard_window_seconds=45)


def validate_output(value):
    need(type(value) is dict and set(value) == set(empty_result()))
    need(value['status'] in STATUSES and value['stage'] in STAGES and value['code'] in CODES
         and value['error_class'] in CLASSES)
    need(type(value['sources']) is list and len(value['sources']) <= 2)
    rows = value['sources'] + ([] if value['summary'] is None else [value['summary']])
    feature_keys = {'utf8_bytes', 'metadata_negated', 'negation_matches', 'polar_matches',
                    'negative_form_counts', 'nonassertive_marker_counts'}
    for row in rows:
        need(type(row) is dict and set(row) == feature_keys)
        need(type(row['negative_form_counts']) is dict and set(row['negative_form_counts']) == set(WORDS))
        need(type(row['nonassertive_marker_counts']) is dict and set(row['nonassertive_marker_counts']) == set(MARKERS))
        numbers = [row[key] for key in ('utf8_bytes', 'metadata_negated', 'negation_matches', 'polar_matches')]
        numbers += list(row['negative_form_counts'].values()) + list(row['nonassertive_marker_counts'].values())
        need(all(type(number) is int and 0 <= number <= 8192 for number in numbers))
    need(type(value['rejection_reasons']) is list and len(value['rejection_reasons']) <= len(REASONS)
         and all(type(reason) is str and reason in REASONS for reason in value['rejection_reasons']))
    excluded = {'status', 'sources', 'summary', 'stage', 'code', 'error_class', 'rejection_reasons'}
    need(all(type(number) in (int, float) and math.isfinite(number) and 0 <= number <= 30000
             for key, number in value.items() if key not in excluded))
    need(value['calls'] <= 1 and value['database_connections'] <= 1 and value['database_write_statements'] == 0)
    need(value['final_summary_capacity'] == 301 and value['request_budget_ms'] == 30000
         and value['max_calls'] == 1 and value['hard_window_seconds'] == 45)
    return value


def readonly_authorizer(action, first, second, database, origin):
    if action in (sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION):
        return sqlite3.SQLITE_OK
    if action == sqlite3.SQLITE_TRANSACTION and first in ('BEGIN', 'COMMIT', 'ROLLBACK'):
        return sqlite3.SQLITE_OK
    if action == sqlite3.SQLITE_PRAGMA and first in ('application_id', 'user_version', 'query_only', 'journal_mode') and second is None:
        return sqlite3.SQLITE_OK
    return sqlite3.SQLITE_DENY


def select_failed_group(path, memory):
    need(path.is_file() and path.resolve() == path and not path.is_symlink())
    with contextlib.closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=.25)) as db:
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA query_only=ON')
        db.set_authorizer(readonly_authorizer)
        need(db.execute('PRAGMA application_id').fetchone()[0] == memory.APPLICATION_ID
             and db.execute('PRAGMA user_version').fetchone()[0] == memory.SCHEMA_VERSION
             and db.execute('PRAGMA query_only').fetchone()[0] == 1
             and db.execute('PRAGMA journal_mode').fetchone()[0] == 'delete')
        db.create_function('diagnostic_has_polar', 1, lambda text: int(not isinstance(text, str)
                           or memory.POLAR_QUESTION.search(text) is not None))
        db.execute('BEGIN')
        task = db.execute("""SELECT t.* FROM bm_tasks t
            WHERE t.status='failed' AND t.error_code='candidate_rejected'
            AND (SELECT count(*) FROM bm_task_sources s WHERE s.task_id=t.task_id) BETWEEN 1 AND 2
            AND NOT EXISTS(SELECT 1 FROM bm_task_sources s
                LEFT JOIN bm_events e ON e.event_id=s.event_id
                LEFT JOIN bm_bodies b ON b.event_id=s.event_id
                WHERE s.task_id=t.task_id AND (e.event_id IS NULL OR b.event_id IS NULL
                    OR e.source!='user_said' OR e.state!='valid' OR e.closed_utc IS NULL
                    OR e.scope_kind!=t.scope_kind OR e.scope_id!=t.scope_id OR e.topic!=t.topic
                    OR e.revision!=s.revision OR e.body_hash!=s.body_hash
                    OR e.compacted_summary_id IS NOT NULL OR e.reserved_task IS NOT NULL
                    OR length(CAST(b.text AS BLOB)) NOT BETWEEN 1 AND 8192
                    OR diagnostic_has_polar(b.text)!=0))
            ORDER BY t.created_utc DESC,t.task_id DESC LIMIT 1""").fetchone()
        if task is None:
            return None
        rows = db.execute("""SELECT e.*,b.text FROM bm_task_sources s
            JOIN bm_events e ON e.event_id=s.event_id JOIN bm_bodies b ON b.event_id=s.event_id
            WHERE s.task_id=? ORDER BY e.recorded_utc,e.event_id""", (task['task_id'],)).fetchall()
        need(1 <= len(rows) <= 2)
        sources = []
        for row in rows:
            need(digest(row['text'].encode('utf8')) == row['body_hash'])
            item = memory.BoardMemoryStore._public_event(row)
            need(isinstance(item['metadata'], dict))
            item['include_in_summary'] = True
            sources.append(item)
        return dict(schema_version=memory.SCHEMA_VERSION,
                    scope=dict(kind=task['scope_kind'], id=task['scope_id']), topic=task['topic'],
                    start_utc=task['start_utc'], end_utc=task['end_utc'], sources=sources,
                    required_claims=memory.BoardMemoryStore._required_claims(sources))


class ProjectionClient:
    def __init__(self, actual, memory, policy, guard, result, owner_prefix):
        self.actual, self.memory, self.policy = actual, memory, policy
        self.guard, self.result, self.owner_prefix = guard, result, owner_prefix

    def request(self, kind, payload, *, deadline, cancelled):
        self.guard()
        need(self.result['calls'] == 0 and kind == 'llm' and payload.get('task') == 'summary'
             and payload.get('board_boot_id') == self.owner_prefix
             and payload.get('options') == {'num_predict': 384} and 1 <= payload['budget_ms'] <= 30000)
        self.result['request_cost'] = self.policy.message_cost(payload['messages'], 384)
        need(self.result['request_cost'] <= 2048)
        self.result['calls'] += 1
        started = time.monotonic()
        try:
            response = self.actual.request(kind, payload, deadline=deadline, cancelled=cancelled)
            verified = self.policy.validate_response(response, self.policy.Owner.from_dict(payload), 'llm')
            if verified['ok']:
                try:
                    semantic = parse(verified['result']['text'])
                    if type(semantic) is dict and set(semantic) == {'summary', 'keywords'}:
                        self.result['summary'] = features(semantic['summary'], {}, self.memory)
                except Exception:
                    pass
            self.guard()
            return response
        finally:
            self.result['model_elapsed_seconds'] = min(30000.0, time.monotonic() - started)

    def cancel(self, owner):
        self.result['cancel_calls'] += 1
        return self.actual.cancel(owner)


def diagnose(prepared, memory, policy, actual, guard, cancelled, result):
    result['sources'] = [features(row['text'], row['metadata'], memory) for row in prepared['sources']]
    need(all(row['polar_matches'] == 0 for row in result['sources']))
    fake_boot = 'private-shape-diagnostic-v23-' + uuid.uuid4().hex
    projected = ProjectionClient(actual, memory, policy, guard, result, fake_boot)
    summary = policy.BoardSummaryClient(projected, board_boot_id=fake_boot, budget_ms=30000,
        total_budget_ms=30000, max_calls=1, final_summary_max_utf8_bytes=301)
    try:
        candidate = summary(prepared, cancelled)
        task = dict(scope_kind=prepared['scope']['kind'], scope_id=prepared['scope']['id'],
                    topic=prepared['topic'], start_utc=prepared['start_utc'], end_utc=prepared['end_utc'])
        memory.BoardMemoryStore._candidate(candidate, task, prepared['sources'])
        result['accepted'] = 1
    except Exception as error:
        result['error_class'] = enum(type(error).__name__, CLASSES)
        reasons = getattr(error, 'rejection_reasons', ())
        if isinstance(reasons, (tuple, list)):
            result['rejection_reasons'] = [reason for reason in REASONS if reason in reasons]
            result['unknown_rejection_reasons'] = sum(type(reason) is not str or reason not in REASONS for reason in reasons[:64])
    metadata = summary.failure_metadata()
    result.update(status='DIAGNOSIS_COMPLETE', stage=enum(metadata.get('stage'), STAGES),
                  code=enum(metadata.get('code'), CODES),
                  source_complete_coverage=int(summary.metrics.get('complete_source_coverage') is True))
    guard()
    return result


@contextlib.contextmanager
def isolated_imports():
    selected = lambda name: name.split('.', 1)[0] in ('common', 'board', 'tools')
    saved = {name: module for name, module in sys.modules.items() if selected(name)}
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
        sys.path[:] = old_path


def full_guard(arguments):
    captured = []
    namespace = dict(SPEC=arguments['spec'], READY=arguments['ready'], INSTALLED=arguments['installed'],
        BASE_SPEC_SHA=arguments['previous_spec_sha256'], ACTION='ready', TOKEN=None, WINDOW=None,
        print=lambda value: captured.append(parse(value)))
    with isolated_imports():
        exec(compile(arguments['guard_source'], '<frozen-v23-readonly-seal>', 'exec'), namespace)
    need(len(captured) == 1)
    proof = captured[0]
    expected = arguments['mapping']
    for key in ('boot_id', 'startup_sha256', 'source_manifest_sha256', 'configuration_sha256',
                'component_pins', 'supervisor', 'gtk', 'camera'):
        need(proof[key] == expected[key])
    need(len(proof['component_pins']) == 380)


def fast_guard(arguments):
    expected = arguments['mapping']
    need(Path('/proc/sys/kernel/random/boot_id').read_text().strip() == expected['boot_id'])
    for kind in ('supervisor', 'gtk', 'camera'):
        owner = expected[kind]
        root = Path('/proc') / str(owner['pid'])
        fields = (root / 'stat').read_text().rsplit(')', 1)[1].split()
        need(int(fields[19]) == owner['birth_ticks'] and digest((root / 'cmdline').read_bytes()) == owner['command_sha256'])
    need(digest((Path(arguments['spec']['target']) / 'startup/config.json').read_bytes()) == expected['startup_sha256'])
    saved = parse(PREFERENCE.read_bytes())
    need(set(saved) == {'version', 'enabled'} and type(saved['version']) is int
         and saved['version'] == 1 and saved['enabled'] is False)
    state = parse(CONTROL.read_bytes())
    need(state.get('phase') == 'COMMITTED' and state.get('guard_removed') is True
         and state.get('target_startup_sha256') == expected['startup_sha256'])
    connection = http.client.HTTPConnection('127.0.0.1', 8783, timeout=2)
    try:
        connection.request('GET', '/api/state')
        response = connection.getresponse()
        raw = response.read(1048577)
        need(response.status == 200 and len(raw) <= 1048576)
        ui = parse(raw)
    finally:
        connection.close()
    listen = ui.get('handsfree_dialogue', {})
    need(listen.get('enabled') is False and listen.get('state') == 'PAUSED'
         and listen.get('microphone_open') is False and ui.get('phase') == 'IDLE'
         and ui.get('playing') is False)


def readonly_audit(uri, connected):
    def audit(event, values):
        if event == 'sqlite3.connect':
            value = values[0]
            need(type(value) in (str, bytes) and os.fsdecode(value) == uri and connected[0] == 0)
            connected[0] += 1
        if event == 'open' and isinstance(values[0], (str, bytes, os.PathLike)):
            path = os.fsdecode(values[0])
            if path == '/dev/null':
                return
            need(not (path.startswith('/dev/') and path != '/dev/null'))
            flags = values[2]
            need(not isinstance(flags, int) or not flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
        if event == 'ctypes.dlopen':
            need(values[0] is None)
    return audit


def execute(arguments):
    import resource
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    need(sys.platform.startswith('linux') and os.geteuid() == 0)
    sys.dont_write_bytecode = True
    result = empty_result()
    connected = [0]
    sys.addaudithook(readonly_audit(DATABASE.as_uri() + '?mode=ro', connected))
    stop = threading.Event()
    guard_failed = threading.Event()
    monitor = None
    try:
        result['stage'] = 'guard'
        full_guard(arguments)
        fast_guard(arguments)
        result['full_components_before'] = 380
        runtime = Path(arguments['spec']['target']) / 'runtime/aura'
        with isolated_imports():
            sys.path.insert(0, str(runtime))
            memory = importlib.import_module('common.board_memory')
            policy = importlib.import_module('board.runtime.board_memory_policy')
            client_module = importlib.import_module('board.runtime.board_dialogue_client')
            for module in (memory, policy, client_module):
                relative = module.__name__.replace('.', '/') + '.py'
                need(Path(module.__file__).resolve() == runtime / relative
                     and digest(Path(module.__file__).read_bytes()) == arguments['spec']['component_sha256'][relative])
            result['stage'] = 'selection'
            prepared = select_failed_group(DATABASE, memory)
            result['database_connections'] = connected[0]
            if prepared is None:
                result['status'] = 'NO_ELIGIBLE_FAILED_GROUP'
            else:
                deadline = time.monotonic() + 30
                def monitor_guard():
                    while not stop.wait(.5):
                        try:
                            fast_guard(arguments)
                        except Exception:
                            guard_failed.set()
                            return
                monitor = threading.Thread(target=monitor_guard, daemon=True)
                monitor.start()
                cancelled = lambda: guard_failed.is_set() or time.monotonic() >= deadline
                diagnose(prepared, memory, policy, client_module.InferenceHttpClient('192.168.50.1', 8797),
                         lambda: fast_guard(arguments), cancelled, result)
        stop.set()
        if monitor is not None:
            monitor.join(timeout=2.5)
        need(not guard_failed.is_set())
        full_guard(arguments)
        fast_guard(arguments)
        result.update(full_components_after=380, same_owners_before_after=1, saved_pause_preserved=1)
    except BaseException as error:
        result['status'] = 'GUARD_REFUSED' if isinstance(error, Refused) or guard_failed.is_set() else 'DIAGNOSTIC_FAILED'
        result['error_class'] = enum(type(error).__name__, CLASSES)
        result['database_connections'] = connected[0]
    finally:
        stop.set()
    return validate_output(result)


def child_main():
    # Suppress any library output at the file-descriptor boundary. Only this
    # final fixed-vocabulary object may reach the parent pipe.
    output = os.dup(1)
    with open(os.devnull, 'wb') as sink:
        os.dup2(sink.fileno(), 1)
        os.dup2(sink.fileno(), 2)
    result = empty_result()
    try:
        raw = sys.stdin.buffer.read(2097153)
        need(len(raw) <= 2097152)
        result = execute(parse(raw))
    except BaseException as error:
        result = empty_result()
        result['error_class'] = enum(type(error).__name__, CLASSES)
    raw = json.dumps(validate_output(result), ensure_ascii=True, allow_nan=False).encode('ascii')
    os.write(output, raw)
    os.close(output)


if __name__ == '__main__':
    child_main()
