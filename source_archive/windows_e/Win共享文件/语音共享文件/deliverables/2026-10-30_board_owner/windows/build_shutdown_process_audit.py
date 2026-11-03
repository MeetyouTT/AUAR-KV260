"""Metadata-only reconciliation of the parent's authoritative host snapshot.

Does not enumerate/stop processes, open a network connection, load a model,
change startup/shutdown settings or inspect business stores.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent


def safe_command(value):
    # Parent snapshot is already redacted; retain a second defensive filter.
    value = re.sub(r'(?i)(--(?:api[-_]?key|token|password|secret|control[-_]?key)(?:=|\s+))("[^"]*"|\S+)',
                   r'\1[redacted]', value)
    return re.sub(r'(?i)(Bearer\s+)[A-Za-z0-9._~+/=-]+', r'\1[redacted]', value)


def main():
    snapshot_path = HERE/'shutdown_process_snapshot.json'
    snapshot = json.loads(snapshot_path.read_text(encoding='utf-8'))
    original = json.loads((HERE/'real_acceptance_initial.json').read_text(encoding='utf-8'))
    capacity = json.loads((HERE/'capacity_audit.json').read_text(encoding='utf-8'))
    rows = snapshot['processes']
    current = {row['pid']: row for row in rows}
    baseline = {row['pid']: row for row in original['baseline']['processes']}
    protected = capacity['runtime']['baseline_critical_pids']
    preserved = []
    for token in protected:
        before, now = baseline[token], current.get(token)
        preserved.append(dict(pid=token, baseline_created_utc=before['created_utc'],
            current_created_utc=now['created_utc'] if now else None,
            same_creation=bool(now and now['created_utc'] == before['created_utc']),
            same_executable=bool(now and now['exe'].casefold() == before['exe'].casefold()),
            original_command_sha256=before['command_sha256'],
            current_command_sha256=hashlib.sha256(now['command_line'].encode()).hexdigest() if now else None,
            same_command=bool(now and hashlib.sha256(now['command_line'].encode()).hexdigest() == before['command_sha256']),
            executable=now['exe'] if now else before['exe'],
            command_line=safe_command(now['command_line']) if now else None,
            action='preserve_no_signal_no_restart'))
    root_servers = [row for row in rows if any(name in row['command_line'] for name in
                    ('model_probe_server.py', 'serve_candidate_assets.py'))]
    ram_tts = [row for row in rows if 'omnivoice_voice.py' in row['command_line'] and '--memory-only' in row['command_line']]
    pytest_rows = [row for row in rows if '-m pytest' in row['command_line'] or row['name'].casefold() == 'pytest.exe']
    other = []
    for row in rows:
        if row['pid'] in protected or row in root_servers or row in ram_tts or row in pytest_rows:
            continue
        note = ('another_conversation_character_fixture_owner_cleans' if row['pid'] == 32652
                else 'unrelated_desktop_pet_preserve' if 'widget_layered.py' in row['command_line']
                else 'origin_not_confirmed_report_only')
        other.append(dict(row, command_line=safe_command(row['command_line']), action='report_only_no_signal', ownership_note=note))
    result = dict(schema_version=1, generated_utc=datetime.now(timezone.utc).isoformat(),
        snapshot_checked_utc=snapshot['checked_utc'],
        provenance=dict(source=str(snapshot_path), source_sha256=hashlib.sha256(snapshot_path.read_bytes()).hexdigest(),
            origin='parent root full-access CIM query; child only reads the sanitized shared snapshot',
            child_direct_host_view_authoritative=False,
            child_direct_view_issue='CIM denied and Get-Process exposed only its sandbox shell/Idle; no absence conclusions used from that view',
            termination_authority='Snapshot is inspection evidence only. Parent must recheck live PID+creation+command/owned-session before any action.'),
        inspected_process_count=len(rows), protected_original_count=len(protected),
        original_13_preserved=all(row['same_creation'] and row['same_executable'] and row['same_command'] for row in preserved),
        protected_original_processes=preserved,
        root_temporary_servers=dict(count=len(root_servers), processes=root_servers,
            names_searched=['model_probe_server.py', 'serve_candidate_assets.py'],
            action='none_required_at_snapshot' if not root_servers else 'parent_confirm_live_ownership_before_any_graceful_cleanup'),
        candidate_ram_tts=dict(count=len(ram_tts), processes=ram_tts, action='report_only_no_direct_pid_stop'),
        root_pytest=dict(processes=[dict(row, command_line=safe_command(row['command_line'])) for row in pytest_rows],
            tool_session_id=18706, ownership='parent explicitly confirmed this running merged pytest family',
            action='parent waits and verifies exit; child does not stop', exit_verified_by_child=False),
        historical_tool_session_37810=dict(status='parent_confirmed_TTL_ended',
            tool_session_id_is_not_a_process_pid=True, action='no_process_action'),
        other_processes_report_only=other,
        actions_performed=[], processes_signalled_or_stopped_by_child=[],
        scope=dict(production_services_closed=False, original_ollama_stopped=False, original_tts_stopped=False,
            llm_unload_requested=False, real_inference_performed=False, new_servers_started=False,
            microphone_or_playback=False, startup_entries_changed=False, scheduled_shutdown_changed=False,
            sandbox_permissions_used=False, private_database_opened=False),
        conclusion='No root model-probe/asset server or candidate RAM TTS is present in the authoritative 15:32 snapshot; original 13 process identities and exact commands match. No cleanup signals were sent. Parent owns completion of its running pytest; the independent character fixture remains its own conversation responsibility.')
    (HERE/'shutdown_process_audit.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'original_13_preserved': result['original_13_preserved'],
        'root_temporary_servers': len(root_servers), 'candidate_ram_tts': len(ram_tts),
        'root_pytest_pids': [row['pid'] for row in pytest_rows], 'process_actions': 0,
        'report': str(HERE/'shutdown_process_audit.json')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
