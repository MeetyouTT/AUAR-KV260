"""Observe startup only; never resubmit a service action."""
import hashlib
import http.client
import json
from pathlib import Path
import subprocess
import time

ROOT = Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip() == 'a6d4a069-e9b0-4065-8df7-dc23556b168e'
assert hashlib.sha256((ROOT / 'startup/config.json').read_bytes()).hexdigest() == '474f6640b4a2df3383b8ccb2814db7fe3448965c078dd87f972ba0997b23f7b2'
started = time.monotonic()
answer = dict(api_ready_for_observation=False, unit_failed=False, board_mutations=False, api_state_exported=False)
while time.monotonic() - started < 40:
    p = subprocess.run(['systemctl','show','aura-avatar-ui.service','--property=MainPID,ActiveState,SubState,Job,Result,ExecMainStatus'],capture_output=True,text=True,timeout=3)
    assert p.returncode == 0
    unit = dict(line.split('=',1) for line in p.stdout.splitlines() if '=' in line)
    answer['unit'] = unit
    if unit['ActiveState'] == 'failed':
        answer['unit_failed'] = True
        break
    c = http.client.HTTPConnection('127.0.0.1',8783,timeout=2)
    try:
        c.request('GET','/api/state'); r=c.getresponse(); raw=r.read(2097153)
        if r.status == 200 and len(raw)<=2097152:
            v=json.loads(raw); b=v.get('board_business') or {}; d=b.get('dialogue') or {}
            trace=(d.get('voice_enrollment') or {}).get('entry_trace') or {}
            answer['entry_trace_projection_present'] = trace.get('version') == 1
            answer['business_started'] = b.get('started') is True
            answer['identity_match_threshold'] = (b.get('speaker') or {}).get('identity_match_threshold')
            answer['requested_threshold_loaded'] = answer['identity_match_threshold'] == .35
            answer['self_match_probe_loaded'] = ((b.get('speaker') or {}).get('self_match_probe') or {}).get('version') == 1
            answer['runtime_fault_count'] = (v.get('runtime_faults') or {}).get('count')
            if answer['entry_trace_projection_present'] and answer['business_started'] and answer['self_match_probe_loaded'] and answer['requested_threshold_loaded']:
                answer['api_ready_for_observation'] = True
                break
    except (OSError, ValueError, http.client.HTTPException):
        pass
    finally:
        c.close()
    time.sleep(1)
answer['waited_seconds'] = round(time.monotonic()-started,2)
if answer['unit_failed']:
    p = ROOT/'runtime/stage.log'
    data = p.read_bytes()[-1048576:] if p.is_file() else b''
    answer['stage_log_sha256'] = hashlib.sha256(data).hexdigest()
    answer['fixed_failure_flags'] = {code.decode():code in data for code in (b'ClockUnavailable',b'sample_rtt_exceeded',b'ImportError',b'AttributeError',b'Traceback',b'SyntaxError')}
print(json.dumps(answer))
