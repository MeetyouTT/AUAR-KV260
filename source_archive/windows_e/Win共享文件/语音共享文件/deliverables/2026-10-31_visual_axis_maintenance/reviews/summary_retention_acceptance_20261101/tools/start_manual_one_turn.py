"""Prepare by default. Explicit execution uses one SSH/control stream and public UI only."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import sys
import threading
import time

HERE = Path(__file__).resolve().parents[1]
PROJECT = HERE.parents[3]
JOINT = HERE.parent / 'joint_performance_20261101'
CONTEXT = HERE / 'evidence/preflight_1793537147007232900.json'
CONTEXT_SHA = '2843d860584b49813c12121b735b57e8589c7fd1500784587b2c33fdd2e2fc7f'
OLD_MANIFEST = '8ff79452570385921e06c098b5d42c2ea1ef5dfb84d81dfa7f53a9295373d0e8'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def build_source():
    context_raw = CONTEXT.read_bytes()
    assert sha(context_raw) == CONTEXT_SHA
    proof = json.loads(context_raw)['result']
    spec_raw = (PROJECT / 'deliverables/2026-10-30_board_owner/integration/production_business_acceptance/spec.json').read_bytes()
    assert sha(spec_raw) == '62b99e24560229c78a3be000fed5752b6a50c4fb16ab6bc2c88e987561831177'
    spec = json.loads(spec_raw)
    assert proof['can_continue_plan_preparation'] is True
    assert proof['startup_sha256'] == spec['startup_sha256']
    assert proof['manifest_sha256'] == spec['source_manifest_sha256'] and proof['component_pins'] == 380
    owners = {role: {key: row[key] for key in ('pid', 'birth_ticks', 'command_sha256')}
              for role, row in proof['owners_discovered_fresh'].items()}
    package = JOINT / 'package/subtitle_receipt'
    camera = (package / 'camera_binding_runtime.py').read_text('utf-8')
    common = (JOINT / 'remote/common.py').read_text('utf-8').replace(OLD_MANIFEST, spec['source_manifest_sha256'])
    original = (JOINT / 'remote/live_observer_caption_accepted.py').read_bytes()
    assert sha(original) == '8ebb76746cb87bd3608671848cc8087d724e24d4282f2933a3c15b4879bd4819'
    observer = (HERE / 'remote/live_observer_manual_accepted.py').read_bytes()
    assert sha(observer) == '4a01af8831de2a4b21c65c618e21a5e911990e87dda4df9b7d703e37c8423527'
    controls = (HERE / 'remote/manual_one_turn_control.py').read_text('utf-8')
    source = (camera + '\n' + common + '\nSTARTUP_SHA=' + repr(spec['startup_sha256'])
              + '\nEXPECTED_OWNERS=' + repr(owners) + '\n'
              + controls + '\nOBSERVER_SOURCE=' + repr(observer.decode('utf-8')) + '\n' + REMOTE)
    compile(source, '<manual-public-ui-observer>', 'exec')
    return source.encode('utf-8'), owners, sha(observer)


def verify_frozen_manifest():
    manifest = json.loads((HERE / 'manual_driver/FROZEN_MANIFEST.json').read_bytes())
    for row in manifest['files']:
        path = Path(row['path']).resolve()
        assert path.is_relative_to(PROJECT)
        raw = path.read_bytes()
        assert len(raw) == row['bytes'] and sha(raw) == row['sha256']


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    source, owners, observer_sha = build_source()
    if not args.execute:
        print(json.dumps(dict(status='LOCAL_PREPARATION_ONLY_NO_DEVICE_ACCESS',
                              source_sha256=sha(source), source_bytes=len(source),
                              observer_sha256=observer_sha, expected_owners=owners)))
        return
    verify_frozen_manifest()
    sys.path.insert(0, str(PROJECT / 'deliverables/2026-10-18_board_dialogue'))
    from board_ssh import KEY
    folder = HERE / 'evidence' / ('manual_trial_' + str(time.time_ns()))
    folder.mkdir(parents=True)
    evidence = folder / 'metadata.jsonl'
    control_file = folder / 'STOP.json'
    # A bounded length prefix leaves the same SSH stdin open for one stop token.
    bootstrap = "import sys; n=int(sys.stdin.buffer.readline(16)); assert 0<n<200000; s=sys.stdin.buffer.read(n); assert len(s)==n; exec(compile(s,'<manual-public-ui-observer>','exec'))"
    command = "python3 -u -B -c '" + bootstrap.replace("'", "'\"'\"'") + "'"
    argv = ['C:/Windows/System32/OpenSSH/ssh.exe', '-T', '-i', str(KEY),
            '-o', 'IdentitiesOnly=yes', '-o', 'BatchMode=yes',
            '-o', 'StrictHostKeyChecking=yes', '-o', 'ConnectTimeout=4',
            'root@192.168.50.2', command]
    process = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    process.stdin.write(str(len(source)).encode('ascii') + b'\n' + source)
    process.stdin.flush()
    done = threading.Event()
    control_status = {'status': 'NO_STOP_RECEIVED'}

    def relay_stop():
        while not done.wait(.1):
            if not control_file.exists():
                continue
            try:
                assert not control_file.is_symlink()
                raw = control_file.read_bytes()
                assert len(raw) <= 128 and json.loads(raw) == {'command': 'stop'}
                process.stdin.write(b'{"command":"stop"}\n')
                process.stdin.flush()
                control_status['status'] = 'STOP_TOKEN_FORWARDED_ON_EXISTING_SSH'
            except Exception as exc:
                control_status.update(status='CONTROL_RELAY_REFUSED', error_class=type(exc).__name__)
            return

    relay = threading.Thread(target=relay_stop, daemon=True)
    relay.start()
    rows = []
    with evidence.open('x', encoding='utf-8') as stream:
        for raw in process.stdout:
            row = json.loads(raw)
            rows.append(row)
            stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + '\n')
            stream.flush()
            if row.get('kind') == 'ready':
                ready = dict(row, source_sha256=sha(source), observer_sha256=observer_sha,
                             trial_directory=str(folder), evidence_path=str(evidence), control_file=str(control_file),
                             expected_owners=owners)
                (folder / 'READY.json').write_text(json.dumps(ready, indent=2) + '\n', encoding='utf-8')
                print(json.dumps(dict(status='MANUAL_READY_FOR_ONE_NEW_TURN', ready=str(folder / 'READY.json'),
                                      control_file=str(control_file), max_recording_seconds=20)), flush=True)
            if row.get('kind') == 'manual_control':
                print(json.dumps(row), flush=True)
            state = row.get('proof', {}).get('state', {})
            if (row.get('kind') == 'final_guard' and state.get('listening_state') == 'PAUSED'
                    and state.get('microphone_open') is False and state.get('playing') is False):
                (folder / 'FINAL_PAUSED.json').write_text(json.dumps(row, indent=2) + '\n', encoding='utf-8')
    code = process.wait(timeout=10)
    done.set()
    relay.join(timeout=1)
    process.stdin.close()
    stderr = process.stderr.read()
    turn_complete = any(r.get('kind') == 'complete' and r.get('status') == 'ONE_NEW_TURN_COMPLETE' for r in rows)
    final_paused = any(r.get('kind') == 'final_guard' and r.get('one_new_turn_complete') is True
                       and r.get('proof', {}).get('state', {}).get('listening_state') == 'PAUSED'
                       and r.get('proof', {}).get('state', {}).get('microphone_open') is False
                       and r.get('proof', {}).get('state', {}).get('playing') is False for r in rows)
    status = ('ONE_NEW_MANUAL_TURN_COMPLETE' if code == 0 and turn_complete and final_paused
              else 'MANUAL_OBSERVER_PROCESS_ERROR' if code else 'MANUAL_TRIAL_INCOMPLETE')
    result = dict(status=status, exit_code=code,
                  stderr_present=bool(stderr), terminal_events=[r for r in rows if r.get('kind') in
                  ('complete', 'final_guard', 'observer_exception', 'observation_cleanup', 'manual_control')],
                  samples=sum(r.get('kind') == 'sample' for r in rows), control=control_status,
                  evidence=str(evidence), source_sha256=sha(source), private_text_audio_images_saved=False)
    path = folder / 'RESULT.json'
    path.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    print(json.dumps(dict(result_path=str(path), **result)), flush=True)


REMOTE = r'''
def current_guard():
    assert os.geteuid()==0 and os.uname().machine=='aarch64'
    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
    assert digest(BUSINESS/'startup/config.json')==STARTUP_SHA
before,_,_=preflight()
print(json.dumps(dict(kind='guard_before',proof=before)),flush=True)
def ui_command(data):
    assert data in (dict(type='service_action',action='record_start'),dict(type='service_action',action='record_stop'))
    c=http.client.HTTPConnection('127.0.0.1',8783,timeout=5)
    try:
        c.request('POST','/api/command',body=json.dumps(data),headers={'Content-Type':'application/json','Origin':'http://127.0.0.1:8783'})
        r=c.getresponse();raw=r.read(100001)
        assert r.status==200 and len(raw)<=100000 and json.loads(raw).get('ok') is True
    finally:c.close()
live_ns=globals()
live_ns.update(EXPECTED_STARTUP=STARTUP_SHA,EXPECTED_BOOT=BOOT)
try:
    start_receipt=manual_start()
    print(json.dumps(dict(kind='manual_start',**start_receipt)),flush=True)
    exec(compile(OBSERVER_SOURCE,'<manual-accepted-caption-observer>','exec'),live_ns)
except Exception as exc:
    print(json.dumps(dict(kind='observer_exception',error_class=type(exc).__name__)),flush=True)
one_complete=bool(live_ns.get('completed'))
try:
    cleanup=settle_manual_without_cancel()
    print(json.dumps(dict(kind='observation_cleanup',**cleanup)),flush=True)
except Exception as exc:
    print(json.dumps(dict(kind='cleanup_error',error_class=type(exc).__name__)),flush=True)
try:
    after,value,_=preflight()
    assert value.get('automatic_conversation',{}).get('enabled') is False
    print(json.dumps(dict(kind='final_guard',proof=after,one_new_turn_complete=one_complete,
        manual_metadata=manual_metadata(value),cancel_or_pause_command_sent=False,
        acoustic_first_sound_measured=False)),flush=True)
except Exception as exc:
    print(json.dumps(dict(kind='final_guard',status='FAILED',error_class=type(exc).__name__,one_new_turn_complete=one_complete)),flush=True)
'''


if __name__ == '__main__':
    main()
