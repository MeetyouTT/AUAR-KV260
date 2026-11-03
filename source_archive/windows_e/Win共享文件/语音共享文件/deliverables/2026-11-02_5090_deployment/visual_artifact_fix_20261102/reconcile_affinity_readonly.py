"""Read-only reconciliation after an unconfirmed bounded affinity request."""
import hashlib
import http.client
import json
import os
from pathlib import Path
import time

root = Path('/home/root/aura-5090-recovery-20261102-a6d4a069')
tx = root / 'single-consumer-affinity-1'
startup = Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13/startup/config.json')
out = {'schema': 'aura-affinity-read-only-reconciliation-1', 'mono_ms': int(time.monotonic()*1000), 'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(), 'startup_sha256': hashlib.sha256(startup.read_bytes()).hexdigest(), 'transaction_exists': tx.exists(), 'mutation_count': 0}
out['transaction_files'] = sorted(p.name for p in tx.iterdir()) if tx.exists() else []
for name in ('affinity-intent.json', 'affinity-result.json', 'close-capture-intent.json', 'restore-listening-intent.json'):
    p = tx / name
    if p.is_file():
        out[name] = json.loads(p.read_text())
out['processes'] = []
for pid in (394712,394720,362659,394769,394861):
    p = Path('/proc') / str(pid)
    row = {'pid': pid, 'exists': p.exists()}
    if p.exists():
        v = p.joinpath('stat').read_text().rsplit(')',1)[1].split()
        row.update(birth_ticks=v[19], command_sha256=hashlib.sha256(p.joinpath('cmdline').read_bytes()).hexdigest(), nice=int(v[16]))
        if pid == 394769:
            row['threads'] = []
            for task in (p/'task').iterdir():
                try:
                    s=(task/'stat').read_text().rsplit(')',1)[1].split(); tid=int(task.name)
                    row['threads'].append({'tid':tid,'birth_ticks':s[19],'nice':int(s[16]),'affinity':sorted(os.sched_getaffinity(tid)),'policy':os.sched_getscheduler(tid),'utime_ticks':int(s[11]),'stime_ticks':int(s[12])})
                except OSError:
                    pass
    out['processes'].append(row)
c=http.client.HTTPConnection('127.0.0.1',8783,timeout=3)
try:
    c.request('GET','/api/state');r=c.getresponse();assert r.status==200;v=json.loads(r.read(2097152))
    out['ui']={k:v.get(k) for k in ('ui_page','playing','pending_job','sequence')}
    h=v.get('handsfree_dialogue') or {}
    out['ui']['handsfree']={k:h.get(k) for k in ('enabled','microphone_open','state')}
    pan=v.get('manual_pan') or {}
    out['ui']['axis']={k:pan.get(k) for k in ('automatic_following','state','current_width_us','error_code')}
    af=(v.get('audio_frontend') or {}).get('current') or {}
    out['audio_frontend_cached_numeric']={k:z for k,z in af.items() if type(z) in (int,float,bool)}
    diag=v.get('safe_capture_diagnostics') or {}
    q=diag.get('input_queue') or {}
    out['queue_cache']={k:z for k,z in q.items() if type(z) in (int,float,bool)}
    expected = {394712:('3106155','48a28efa32b2050901e73e85a80a30a90dcfbce0b7249bde5d6d90902740631d'),394720:('3106263','e81bf963d019b5b23293db8d863359ca706564b4e1fa74a69a212517dc08de48'),362659:('2850120','acf3ee123d7674fdea6e90e79252909ca396249c870269169910879d940c27dd'),394769:('3108205','236c51091fd21c314c0ca2e1cb48fefde1181eda5cb0431b974f60941dfa943e')}
    guards=[{'condition':'boot','pass':out['boot_id']=='a6d4a069-e9b0-4065-8df7-dc23556b168e'}, {'condition':'startup','pass':out['startup_sha256']=='c3861fa3d2cbb10fee424804f7b3932eadd576819a2a6290c7ca406d900b9602'}]
    for row in out['processes']:
        if row['pid'] in expected:
            birth,cmd=expected[row['pid']]
            guards.append({'condition':'lifetime_'+str(row['pid']),'pass':row.get('birth_ticks')==birth and row.get('command_sha256')==cmd})
    guards += [{'condition':'line138_vision','pass':v.get('ui_page')=='vision'}, {'condition':'line138_no_playback_or_job','pass':not v.get('playing') and not v.get('pending_job')}, {'condition':'line138_follow_off','pass':not pan.get('automatic_following')}, {'condition':'line138_listening_enabled_and_open','pass':bool(h.get('enabled') and h.get('microphone_open'))}, {'condition':'line138_main_nice','pass':os.getpriority(os.PRIO_PROCESS,394769)==-10}]
    out['original_readonly_prefix_current_guards']=guards
    out['current_first_failed_guard']=next((g['condition'] for g in guards if not g['pass']),None)
    out['historical_exception_line_not_retained']=True
finally:
    c.close()
print(json.dumps(out))
