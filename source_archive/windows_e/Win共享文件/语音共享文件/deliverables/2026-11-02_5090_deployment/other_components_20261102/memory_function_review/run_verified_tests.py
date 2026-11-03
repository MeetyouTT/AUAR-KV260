"""Run bounded synthetic memory tests against the current pinned source closure."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import uuid

HERE = Path(__file__).resolve().parent
RUNTIME = HERE/'runtime_v24'
WORK = HERE/'test_work'
WORK.mkdir(exist_ok=True)
tempfile.tempdir = str(WORK)
manifest = json.loads((HERE/'SOURCE_CLOSURE.json').read_text(encoding='utf-8'))
for relative, entry in manifest['sources'].items():
    assert hashlib.sha256((RUNTIME/relative).read_bytes()).hexdigest() == entry['sha256']
os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD'] = '1'
sys.dont_write_bytecode = True
sys.path.insert(0, str(RUNTIME))
guards = {'sqlite_connections': 0, 'network_attempts': 0, 'process_attempts': 0,
          'device_library_attempts': 0, 'outside_database_attempts': 0,
          'outside_write_attempts': 0, 'model_file_attempts': 0,
          'windows_console_library_loads': 0}
denied_write_attempts = []

def inside(path, root):
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False

def audit(event, args):
    if event == 'sqlite3.connect':
        value = os.fsdecode(args[0])
        guards['sqlite_connections'] += 1
        if value != ':memory:' and not inside(Path(value), WORK):
            guards['outside_database_attempts'] += 1
            raise PermissionError('Only fresh synthetic test databases are allowed')
    if event in ('socket.connect', 'socket.connect_ex', 'socket.bind', 'socket.sendto', 'socket.getaddrinfo'):
        guards['network_attempts'] += 1
        raise PermissionError('Network use is forbidden in this offline validation')
    if event in ('subprocess.Popen', 'os.system', 'os.exec', 'os.posix_spawn'):
        guards['process_attempts'] += 1
        raise PermissionError('External programs are forbidden in this validation process')
    if event == 'ctypes.dlopen':
        if str(args[0]).casefold() in ('kernel32', 'kernel32.dll'):
            guards['windows_console_library_loads'] += 1
            return
        guards['device_library_attempts'] += 1
        raise PermissionError('ctypes/device library loads are forbidden')
    if event == 'open' and isinstance(args[0], (str, bytes, os.PathLike)):
        path = Path(os.fsdecode(args[0]))
        if path.suffix.casefold() in ('.gguf', '.onnx', '.pt', '.pth', '.safetensors', '.bin'):
            guards['model_file_attempts'] += 1
            raise PermissionError('Model/resource reads are forbidden')
        if path.suffix.casefold() in ('.sqlite', '.sqlite3', '.db') and not inside(path, WORK):
            guards['outside_database_attempts'] += 1
            raise PermissionError('Real or external database reads are forbidden')
        mode = args[1]
        flags = args[2]
        writing = (isinstance(mode, str) and any(char in mode for char in 'wax+')) or (
            isinstance(flags, int) and bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)))
        if writing and not inside(path, HERE):
            guards['outside_write_attempts'] += 1
            if len(denied_write_attempts) < 10:
                frame, stack = sys._getframe(1), []
                for _ in range(8):
                    if frame is None:
                        break
                    stack.append({'file': frame.f_code.co_filename, 'function': frame.f_code.co_name,
                                  'line': frame.f_lineno})
                    frame = frame.f_back
                denied_write_attempts.append({'path': str(path), 'stack': stack, 'write_allowed': False})
            raise PermissionError('Test writes must stay in the owned review directory')

sys.addaudithook(audit)

def verify_imports():
    imported = {}
    for name, module in tuple(sys.modules.items()):
        if name.split('.')[0] not in ('common', 'board') or not getattr(module, '__file__', None):
            continue
        path = Path(module.__file__).resolve()
        assert inside(path, RUNTIME), 'Project import escaped staged runtime: ' + name
        relative = path.relative_to(RUNTIME.resolve()).as_posix()
        assert relative in manifest['sources'], 'Project import lacks production pin: ' + relative
        content_sha = hashlib.sha256(path.read_bytes()).hexdigest()
        assert content_sha == manifest['sources'][relative]['sha256']
        imported[name] = content_sha
    assert not any(name.split('.')[0] in ('torch', 'onnxruntime', 'cv2', 'gi') for name in sys.modules)
    return imported

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--phase', choices=('original', 'targeted', 'reopen'), required=True)
    args = parser.parse_args()
    if args.phase == 'reopen':
        from common.board_memory import BoardMemoryStore
        from common.profile_access import ProfileAccess, ProfileGrant
        fixture = json.loads((WORK/'persistence_fixture.json').read_text(encoding='utf-8'))
        path = WORK/'synthetic-persistent.sqlite3'
        before = (path.read_bytes(), path.stat().st_mtime_ns)
        store = BoardMemoryStore(path, clock=lambda: 5000., profile_access=ProfileAccess('9'*64, clock=lambda: 5000.))
        anonymous = {'kind': 'conversation', 'id': 'synthetic-persistent-conversation'}
        assert store.context(anonymous)['facts'][0]['value'] == '离线合成新项目'
        assert any(row['source'] == 'timeline_summary' for row in store.history(anonymous, search='书单'))
        assert store.health()['active_bodies'] == 0
        access = store.profile_access
        profile = {'kind': 'profile', 'id': 'a'*32}
        try:
            store.context(profile)
        except PermissionError:
            pass
        else:
            raise AssertionError('Persisted personal facts must not grant access after process restart')
        copied = ProfileGrant('a'*32, ('offline-boot', 'offline-session'), fixture['old_grant_nonce'], 9000.)
        try:
            store.context(dict(profile, grant=copied))
        except PermissionError:
            pass
        else:
            raise AssertionError('A copied grant is not a live grant in this process')
        access.authenticate('9'*64)
        _, grant = access.issue('a'*32, {'board_boot_id': 'offline-boot', 'session_id': 'offline-new-session'})
        assert store.context(dict(profile, grant=grant))['facts'][0]['value'] == '离线合成个人事实'
        assert (path.read_bytes(), path.stat().st_mtime_ns) == before
        code, summary = 0, {'fresh_python_process_reopened_synthetic_store': True,
                            'anonymous_fact_and_summary_survived': True,
                            'old_or_forged_grant_denied': True,
                            'new_authenticated_selection_reads_durable_personal_fact': True,
                            'synthetic_database_unchanged_during_reopen': True}
    else:
        import pytest
        base = RUNTIME/'tests/framework'
        selected = {
            'test_board_memory.py': [
                'test_last_closure_not_created_time_controls_exact_five_minute_boundary',
                'test_success_publishes_durable_summary_but_deletes_only_bodies',
                'test_failed_model_and_rejected_candidate_keep_all_detail',
                'test_sqlite_publish_failure_rolls_back_summary_and_cleanup',
                'test_scope_and_topic_are_never_merged',
                'test_forget_after_body_cleanup_revokes_summary_keywords_and_facts',
                'test_correction_after_cleanup_keeps_revisions_and_only_new_current_value',
                'test_concurrent_forget_invalidates_lease_and_prevents_resurrection',
                'test_grants_isolate_profiles_and_restart_or_speaker_cannot_unlock',
                'test_cross_scope_mutation_and_dependency_are_denied',
                'test_profile_revocation_blocks_generated_audio_and_ack_callbacks',
            ],
            'test_board_memory_search_clear.py': [
                'test_old_keyword_only_summary_is_found_before_twenty_new_unrelated_blocks',
                'test_forgetting_compacted_source_removes_text_and_keyword_search_hits',
                'test_search_never_crosses_profile_grants_or_anonymous_scope',
            ],
        }
        nodes = ([str(base/file)+'::'+name for file, names in selected.items() for name in names]
                 if args.phase == 'original' else [str(HERE/'test_memory_function_v24.py')])
        temp = WORK/(args.phase + '-' + uuid.uuid4().hex)
        assert not temp.exists()
        junit = HERE/(args.phase.upper() + '_RESULTS.xml')
        assert not junit.exists(), 'Keep each test result immutable'
        code = pytest.main(nodes + ['-q', '--color=no', '-p', 'no:capture', '-p', 'no:logging', '-p', 'no:cacheprovider', '--basetemp=' + str(temp), '--junitxml=' + str(junit)])
        summary = {'selected_original_test_methods': sum(map(len, selected.values())) if args.phase == 'original' else None,
                   'synthetic_basetemp': str(temp), 'junit': str(junit)}
    result = {'schema': 'aura-offline-memory-test-run-1', 'phase': args.phase, 'exit_code': int(code),
              'summary': summary, 'guard_counts': guards, 'loaded_production_module_sha256': verify_imports(),
              'denied_write_attempts': denied_write_attempts,
              'runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'targeted_test_sha256': hashlib.sha256((HERE/'test_memory_function_v24.py').read_bytes()).hexdigest()
                                     if (HERE/'test_memory_function_v24.py').exists() else None,
              'network_or_model_called': False, 'real_database_opened': False,
              'production_file_changed': False, 'board_accessed': False}
    (HERE/(args.phase.upper() + '_RUN.json')).write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'phase': args.phase, 'exit_code': int(code), 'guards': guards}, ensure_ascii=True))
    raise SystemExit(int(code))

if __name__ == '__main__':
    main()
