"""Create local-only migration evidence and hash manifest; never contact a board."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_new(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write('\n')


def main():
    utc = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    ready_path = ROOT / 'evidence/prepare_repeat_initialization_1793544873985148800.json'
    stop_path = ROOT / 'evidence/abort_stop_readback_1793544812068226700.json'
    assert sha(ready_path) == '250d1cdf0164295b0d5eedf8ed834289420ade881b022e590e1868dc2c9784fc'
    assert sha(stop_path) == '77104846b153aeefd872ac7f3e835be5af693d1ac9c8092e25fcd79398f24bae'
    ready = json.loads(ready_path.read_bytes())
    stop = json.loads(stop_path.read_bytes())
    sources = [ROOT / 'remote/_new_boot_common.py', ROOT / 'remote/freeze_for_5090_migration.py']
    source_hash = hashlib.sha256(b'\n'.join(p.read_bytes() for p in sources)).hexdigest()
    failure_path = ROOT / 'evidence/migration_stop_transport_failure.json'
    failure = dict(schema='aura-axis-migration-stop-attempt-1', recorded_utc=utc,
        status='SSH_BANNER_TIMEOUT_NO_FRESH_STOP_RECEIPT', host='192.168.50.2', port=22,
        local_command_exit_code=1, tool_wall_seconds=4.3449427,
        transport_error='Connection timed out during banner exchange; Connection to 192.168.50.2 port 22 timed out',
        requested_operation='Existing ID_STOP_ONLY; no ARM/COMMIT/REFERENCE',
        source_sha256=source_hash, remote_command_execution_confirmed=False,
        fresh_stop_readback_obtained=False, retry_performed=False,
        device_commands_frozen=True)
    write_new(failure_path, failure)
    snapshot = dict(schema='aura-axis-5090-handoff-1', recorded_utc=utc,
        status='MIGRATION_FROZEN_CURRENT_DEVICE_STATE_UNVERIFIED',
        ownership=dict(old_exclusive_device_thread='01a195e4-58a7-72d3-b141-d5d373579f7f',
            coordinator_local_only_thread='01a18bcd-1167-71a0-ba0b-d809148d39d9'),
        fresh_device_state_verified=False, transport_failure_evidence=failure_path.relative_to(ROOT).as_posix(),
        device_commands_frozen=True, queued_repeat_cancelled=True, automatic_motion_resume_allowed=False,
        latest_saved_stop=dict(utc=ready['utc'], receipt=ready_path.relative_to(ROOT).as_posix(),
            sha256=sha(ready_path), readback=ready['result']['stopped'], freshness='HISTORICAL_ONLY'),
        latest_executed_stop_owner_check=dict(utc=stop['utc'],receipt=stop_path.relative_to(ROOT).as_posix(),
            sha256=sha(stop_path),remaining_motion_owners=stop['result']['remaining_motion_owners'],
            freshness='HISTORICAL_ONLY'),
        last_known_platform=dict(boot_id='3c94e7a0-3f4d-4b66-801c-fa0a1b749bfb',
            camera_pid=2094,camera_birth_ticks=64899,
            camera_command_sha256='acf3ee123d7674fdea6e90e79252909ca396249c870269169910879d940c27dd',
            firmware='aura-visual-servo-b4096-wide-v1.bit.bin',
            fdt_sha256='e35979051349cffd903e2acf42b6ce10fbc9074d8e807c7e7ba92bf47adf0cc3',
            boot_default_observed='kv260-benchmark-b4096.bit.bin',persistent_wide_boot_integration_passed=False,
            runtime_wide_recovery_completed=True,
            remote_session='/home/root/aura-axis-priority-20261101-3c94e7a0',
            checkpoint_sha256='5b26714b0be9d52bf99fe14c07a0f810105379171712328b63454beb314bc6bb'),
        last_known_software=dict(startup_sha256='ec12fccfdd3e8446e9c761e161167e00187e6fcf90372aa7e52c9865cc23c56f',
            manifest_sha256='b144536398bcaa6fdda2f36f9c14decced7e2f766f03e55714853674d8cfdd0d',
            component_count=380,gui_main_pid=0,gui_status='FAILED_MCP01_NOT_READY',
            saved_listening_enabled=False,new_boot_gui_ready_passed=False,new_camera_gui_readback_rebound=False),
        motion_acceptance=dict(initialization_executed=True,initialization_sequence_us=[1500,1505],
            duration_seconds=2,digital_ack_count=43,output_closed_at_end=True,
            physical_observation='NOT_OBSERVED; initial adverse selection corrected by user',
            physical_center_calibrated=False,current_boot_direction_verified=False,
            repeat_executed_by_this_window=False,direction_roundtrip_executed=False,face_follow_executed=False),
        data_handling=dict(private_keys_copied=False,credentials_copied=False,
            model_weights_copied=False,private_board_database_exported=False),
        notes=['Old boot READY/PID430894/direction+1 feedback are historical.',
            'No more device commands after failed final STOP transport attempt.',
            'This snapshot is local evidence; remote session was not updated during the failed connection.'])
    write_new(ROOT / 'CURRENT_MIGRATION_STATE.json', snapshot)
    manifest_path = ROOT / 'HANDOFF_5090_MANIFEST.json'
    files = sorted(p for p in ROOT.rglob('*') if p.is_file() and p != manifest_path)
    manifest = dict(schema='aura-axis-5090-local-manifest-1',created_utc=utc,
        scope='All files under axis_priority_20261101, excluding this manifest itself',
        files=[dict(path=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,sha256=sha(p)) for p in files])
    write_new(manifest_path, manifest)
    for path in files:
        if path.suffix == '.py':
            compile(path.read_text(encoding='utf-8'), str(path), 'exec')
    assert all(sha(ROOT / item['path']) == item['sha256'] for item in manifest['files'])
    print(json.dumps(dict(status='LOCAL_HANDOFF_WRITTEN_AND_HASHES_VERIFIED',file_count=len(files),
        artifacts=[dict(path=str(ROOT/name),sha256=sha(ROOT/name)) for name in
            ('HANDOFF_5090.txt','PROMPT_5090.txt','CURRENT_MIGRATION_STATE.json','HANDOFF_5090_MANIFEST.json')]),ensure_ascii=False))


if __name__ == '__main__':
    main()
