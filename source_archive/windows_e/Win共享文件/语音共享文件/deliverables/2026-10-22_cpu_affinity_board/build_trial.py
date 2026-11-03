"""Prepare one bounded dual-model affinity trial from frozen observer sources."""
import ast
import base64
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CANDIDATE = Path('/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-22_cpu_affinity_candidate_r2')
BASE = Path('/home/ghmd/aura-identity-dpu-check-20261018/board_thread_switch_live_20261022.py')
EXPECTED = 'a439f630bfeb7d86fe93133dd7f287cb30a248a011ecf48950ad4692b5e5694d'
assert hashlib.sha256(BASE.read_bytes()).hexdigest() == EXPECTED
for line in (CANDIDATE / 'FILES.sha256').read_text().splitlines():
    digest, relative = line.split('  ', 1)
    assert hashlib.sha256((CANDIDATE / relative).read_bytes()).hexdigest() == digest
payload = {name: (CANDIDATE / name).read_bytes() for name in
           ('affinity_camera_launcher.py', 'thread_affinity_trial.py', 'example_policy_kv260.json')}
hashes = {name: hashlib.sha256(data).hexdigest() for name, data in payload.items()}
policy = json.loads(payload['example_policy_kv260.json'])
assert policy['expected_process_cpus'] == [0, 1, 2, 3]
source = BASE.read_text()
source = source.replace('thread-switch-live', 'affinity-live').replace('thread-switch-launches', 'affinity-launches')
source = source.replace('AURA_RUN_THREAD_SWITCH_LIVE', 'AURA_RUN_AFFINITY_LIVE')
source = source.replace('THREAD_SWITCH_DUAL_MODEL_120S_ALWAYS_RESTORED', 'CPU_AFFINITY_DUAL_MODEL_120S_ALWAYS_RESTORED')


def replace(old, new):
    global source
    assert source.count(old) == 1, (old[:90], source.count(old))
    source = source.replace(old, new)


extra = '''
def affinity_rows(folder,pid):
    path=folder/('affinity-'+str(pid)+'.jsonl')
    raw=path.read_bytes();assert len(raw)<=65536
    return [json.loads(line) for line in raw.splitlines() if line]

def proc_start(path):
    return int(Path(path).read_text().rsplit(')',1)[1].split()[19])

def affinity_snapshot(folder,pid):
    rows=affinity_rows(folder,pid)
    baseline=[r for r in rows if r['event']=='PROCESS_BASELINE'];assert len(baseline)==1
    assert baseline[0]['pid']==pid and baseline[0]['allowed_cpus']==[0,1,2,3]
    assert baseline[0]['gil_seconds']==.005
    assert baseline[0]['policy_sha256']==PAYLOAD_SHA['example_policy_kv260.json']
    assert baseline[0]['target_sha256']=='1e0e6f0b8881c2d4d4cf81a2527e79d063e673eeba1d069e33bdde2608303005'
    assert baseline[0]['role_source_sha256']==ROLE_PINS
    assert sum(r['event']=='ALL_ROLES_COMMITTED' for r in rows)==1
    applied=[r for r in rows if r['event']=='APPLIED'];assert len(applied)==4
    assert {r['role'] for r in applied}==set(AFFINITY_POLICY['roles'])
    assert not any(r['event'] in ('ABORT_OWNED_PROCESS','RESTORED','CLOSED') for r in rows)
    process_start=proc_start('/proc/'+str(pid)+'/stat');bindings=[]
    for row in applied:
        ident=row['identity'];tid=ident['tid'];task=Path('/proc')/str(pid)/'task'/str(tid)
        assert ident['pid']==pid and ident['process_starttime']==process_start
        assert proc_start(task/'stat')==ident['thread_starttime']
        status=(task/'status').read_text().splitlines()
        assert int(next(x.split()[1] for x in status if x.startswith('Tgid:')))==pid
        actual=sorted(os.sched_getaffinity(tid))
        assert proc_start(task/'stat')==ident['thread_starttime']
        assert proc_start('/proc/'+str(pid)+'/stat')==ident['process_starttime']
        assert row['old_cpus']==[0,1,2,3]
        assert actual==row['actual_cpus']==AFFINITY_POLICY['roles'][row['role']]
        bindings.append({'role':row['role'],'identity':ident,'actual_cpus':actual})
    # Observe remaining tasks without guessing their native/runtime roles.
    tasks=[]
    for task in sorted((Path('/proc')/str(pid)/'task').iterdir()):
        try:tasks.append({'tid':int(task.name),'comm':(task/'comm').read_text().strip(),
                          'cpus':sorted(os.sched_getaffinity(int(task.name)))})
        except (FileNotFoundError,ProcessLookupError):pass
    return {'pid':pid,'mono':time.monotonic(),'bindings':bindings,'tasks':tasks,
        'scope':'two bounded snapshots; unknown descendants may inherit creator mask; not exclusive CPUs'}

def affinity_shutdown(folder,pid):
    rows=affinity_rows(folder,pid)
    applied=[r for r in rows if r['event']=='APPLIED']
    restored=[r for r in rows if r['event']=='RESTORED']
    by_role={r['role']:r for r in restored}
    clean=(len(applied)==len(restored)==4 and len(by_role)==4
        and all(r['role'] in by_role and by_role[r['role']]['identity']==r['identity']
                and by_role[r['role']]['actual_cpus']==r['old_cpus'] for r in applied)
        and sum(r['event']=='CLOSED' for r in rows)==1
        and not any(r['event']=='ABORT_OWNED_PROCESS' for r in rows))
    return {'clean_selected_thread_restoration_and_close':clean,'events':rows,
        'scope':'SIGKILL or process exit may omit events; missing restoration is not reported as clean'}

'''
replace('\ndef main():', '\n' + extra + '\ndef main():')
replace("before=camera();healthy(before);single_owner(before['pid']);idle=ui_idle()",
        "before=camera();healthy(before);single_owner(before['pid']);idle=ui_idle()\n    assert sorted(os.sched_getaffinity(before['pid']))==[0,1,2,3]")
replace('    assert updated!=original_unit', '''
    import base64
    for name,encoded in PAYLOAD_B64.items():
        item=folder/name;item.write_bytes(base64.b64decode(encoded))
        assert digest(item)==PAYLOAD_SHA[name]
    for role,(relative,qualname,expected) in ROLE_SOURCES.items():
        assert digest(candidate/relative)==expected,role
    target=str(candidate/'tools/board_camera_motion.py')
    assert digest(target)=='1e0e6f0b8881c2d4d4cf81a2527e79d063e673eeba1d069e33bdde2608303005'
    text=updated.decode();assert text.count(target)==1
    text=text.replace(target,str(folder/'affinity_camera_launcher.py')+' '+target)
    assert text.count('[Service]\\n')==1
    text=text.replace('[Service]\\n','[Service]\\nEnvironment="AURA_EXPERIMENT_AFFINITY=1"\\n'
        +'Environment="AURA_EXPERIMENT_AFFINITY_POLICY='+str(folder/'example_policy_kv260.json')+'"\\n')
    updated=text.encode()
    assert updated!=original_unit
''')
replace("'runqueue_time_collected':False,'requested_observation_s':120}",
        "'runqueue_time_collected':False,'requested_observation_s':120,\n        'gil_seconds':.005,'payload_sha256':PAYLOAD_SHA,'policy':AFFINITY_POLICY,\n        'native_sources_unchanged_from_observer':True}")
replace("single_owner(state['pid']);first=state;started=time.monotonic();first_cpu=cpu()", '''
        single_owner(state['pid'])
        report['candidate_camera_pid']=state['pid'];save()
        report['affinity_start']=affinity_snapshot(folder,state['pid'])
        first=state;started=time.monotonic();first_cpu=cpu()
''')
replace("report['passed']=True;report['observation_status']='OBSERVER_120S_RUNTIME_ONLY_NOT_ROOT_CAUSE_OR_GAIN_PROOF'", '''
        report['affinity_end']=affinity_snapshot(folder,state['pid'])
        diagnostics=state['pipeline_metrics']['optional_diagnostics']
        assert not diagnostics['fault_events'] and not diagnostics['diagnostic_errors']
        assert diagnostics['counters']['yunet']['native_completed']>=100
        report['observed_yunet_hz']=(state['dpu_schedule']['optional']['yunet']['calls']-first['dpu_schedule']['optional']['yunet']['calls'])/elapsed
        assert report['observed_yunet_hz']>=2.
        ages=[row['face_targets']['source_age_ms'] for row in report['samples']
            if row.get('face_targets',{}).get('source_age_ms') is not None]
        report['freshness']={'scope':'sparse health snapshots, not a per-frame distribution',
            'samples':len(ages),'at_or_over_1000ms':sum(age>=1000 for age in ages),
            'maximum_ms':max(ages),'all_sampled_face_results_fresh':all(0<=age<1000 for age in ages)}
        report['throughput_and_optional_protection_passed']=True
        report['passed']=all(0<=age<1000 for age in ages)
        report['observation_status']='AFFINITY_120S_WITH_SEPARATE_FRESHNESS_GATE_NOT_SPEEDUP_OR_ROOT_CAUSE_PROOF'
''')
replace("report['restored']=restored;report['rollback_verified']=True", '''
            report['restored']=restored;report['rollback_verified']=True
            try:
                report['affinity_shutdown']=affinity_shutdown(folder,report.get('candidate_camera_pid',-1))
                if not report['affinity_shutdown']['clean_selected_thread_restoration_and_close']:
                    report['passed']=False;report['affinity_shutdown_error']='Clean selected-thread restoration/close not confirmed'
            except Exception as exc:
                report['passed']=False;report['affinity_shutdown_error']=type(exc).__name__+': '+str(exc)[:300]
''')
tree = ast.parse(payload['affinity_camera_launcher.py'])
role_sources = ast.literal_eval(next(node.value for node in tree.body if isinstance(node, ast.Assign)
    and isinstance(node.targets[0], ast.Name) and node.targets[0].id == 'ROLE_SOURCES'))
role_pins = {role: value[2] for role, value in role_sources.items() if role in policy['roles']}
prefix = ('PAYLOAD_B64=' + repr({name: base64.b64encode(data).decode() for name,data in payload.items()})
    + '\nPAYLOAD_SHA=' + repr(hashes) + '\nAFFINITY_POLICY=' + repr(policy)
    + '\nROLE_SOURCES=' + repr(role_sources) + '\nROLE_PINS=' + repr(role_pins) + '\n')
source = prefix + source
ast.parse(source)
target = Path('/home/ghmd/aura-identity-dpu-check-20261018/board_cpu_affinity_live_r2_20261022.py')
if target.exists():
    assert target.read_text() == source, 'Do not rewrite a staged helper; version the changed source'
else:
    target.write_text(source)
manifest = {'helper':str(target),'sha256':hashlib.sha256(source.encode()).hexdigest(),
    'payload':hashes,'policy':policy,'native_source_bundle_sha256':
    'cbee206f503bab019812b3ba3943a54943e8913568a5fcd0cecab0f7358b258f',
    'requested_seconds':120,'independent_rollback_seconds':360,'runtime_max_seconds':300,
    'gil_seconds_unchanged':.005,'board_deployed':False}
(ROOT/'trial-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(manifest))
