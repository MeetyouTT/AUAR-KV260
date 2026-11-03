#!/usr/bin/env python3
"""Run the finite review, then restore the original baseline in a finally block."""
import datetime
import hashlib
import json
from pathlib import Path
import signal
import traceback

WORK=Path('/home/root/kv260-runtime-live-20261003T082232Z')
CFG=json.loads((WORK/'config.json').read_text())
STATUS=WORK/'controller-status.json'
state={'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
       'state':'running','phase':None,'completed_phases':[],'failures':[],
       'automatic_retries':False,'baseline_restored':False}

def update():
    state['updated_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    temporary=STATUS.with_suffix('.partial')
    temporary.write_text(json.dumps(state,indent=2))
    temporary.replace(STATUS)

def checked(path,expected):
    data=path.read_bytes()
    assert hashlib.sha256(data).hexdigest()==expected,'Reviewed source changed: '+str(path)
    return data

def execute(name):
    state['phase']=name;update()
    namespace={'__name__':'__board_review__','__file__':str(WORK/'actions'/name)}
    common=WORK/'live_common.py'
    exec(compile(checked(common,CFG['common_sha256']),str(common),'exec'),namespace)
    action=WORK/'actions'/name
    exec(compile(checked(action,CFG['phase_hashes'][name]),str(action),'exec'),namespace)
    state['completed_phases'].append(name);update()

def interrupted(number,frame):
    raise RuntimeError('Review interrupted by signal '+str(number))

signal.signal(signal.SIGTERM,interrupted)
signal.signal(signal.SIGINT,interrupted)
assert not STATUS.exists(),'Refusing repeated worker execution'
update()
try:
    for phase in ['10_start.py','20_functional.py','30_official_reload.py',
                  '40_sustained_inference.py','50_m3_functional.py']:
        execute(phase)
except BaseException:
    state['failures'].append({'phase':state['phase'],'traceback':traceback.format_exc()})
    print(traceback.format_exc(),flush=True)
finally:
    state['state']='recovering';update()
    try:
        execute('60_restore.py')
        state['baseline_restored']=True
        final_log=WORK/'agent_logs/60-restore/candidate-final-log.json'
        if final_log.exists():
            review=json.loads(final_log.read_text())
            state['candidate_final_log']=review
            if review['ERROR_lines']:
                state['failures'].append({'phase':'flushed-candidate-log','errors':review['ERROR_lines']})
        recovery=WORK/'agent_logs/60-restore/result.json'
        if recovery.exists():
            outcome=json.loads(recovery.read_text())
            if outcome.get('recovery_diagnostics'):
                state['failures'].append({'phase':'recovery-diagnostics','issues':outcome['recovery_diagnostics']})
    except BaseException:
        state['failures'].append({'phase':'60_restore.py','traceback':traceback.format_exc()})
        print(traceback.format_exc(),flush=True)
    state['state']='complete' if not state['failures'] else 'failed'
    state['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    update()
print('CONTROLLER_RESULT '+json.dumps(state),flush=True)
raise SystemExit(0 if state['state']=='complete' else 1)
