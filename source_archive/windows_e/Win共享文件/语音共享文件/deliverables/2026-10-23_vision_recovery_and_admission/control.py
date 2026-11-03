"""Guarded camera + one-line GUI consumer promotion; no model/database migration."""
import ast
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback

import handoff
from live_checks import PARENT_CONFIG,PARENT_IDENTITY,PARENT_RELEASE,PARENT_UNIT_SHA,validate_state,rewrite_unit

PARENT_REPORT=Path('/home/root/aura-sface-formal-20261023/00b792619ce222d2/report.json')
LIVE=Path('/home/root/aura-dpu-vision-20261021/postpower-retry-live')
GUI_RUNTIME=Path('/home/root/aura-speech-motion-20261021/de989bf024a9/runtime')
GUI_QUERY_SHA='ba37e44b857f4b1e5b9c8c641b908c932b52dfeb66ed9ecea7fa6b3a9d08ff92'
ENTRY_SHA='c270e4ce9e794754ed6195202b8a00b74650bd6edc740099bf664a5e06d884cd'
WRAPPER_SHA='0cec741d143a012b5d5aa5808f404e7b818510d2773f3b122dd1fb639222ae02'
sha=handoff.digest


def tree_manifest(root):
    result={}
    for path in Path(root).rglob('*'):
        name=path.relative_to(root)
        if '__pycache__' in name.parts or '.db' in path.name or '.sqlite' in path.name:continue
        assert not path.is_symlink(),'Camera package links are not permitted'
        if path.is_file():result[str(name)]={'sha256':sha(path),'bytes':path.stat().st_size}
    return result


def python_manifest(root):
    return {str(p.relative_to(root)):sha(p) for p in Path(root).rglob('*.py') if '__pycache__' not in p.parts}


def clone_gui(release,candidate_query):
    runtime=release/'gui-runtime';runtime.mkdir()
    assert sha(GUI_RUNTIME/'aura/board/identity/spoken_query.py')==GUI_QUERY_SHA
    before=python_manifest(GUI_RUNTIME/'aura')
    # Materialize Python files so __file__.resolve() and imports stay inside the
    # new source tree. Existing static resources remain private board paths.
    shutil.copytree(GUI_RUNTIME/'aura',runtime/'aura',symlinks=True,
                    ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    for path in GUI_RUNTIME.iterdir():
        if path.name in ('aura','managed-runs','launch.json','stage.log') or '.tmp-' in path.name:continue
        target=runtime/path.name
        if path.name.startswith('avatar') and path.name.endswith('settings.json'):
            shutil.copyfile(path,target)
        else:
            target.symlink_to(path.resolve(),target_is_directory=path.is_dir())
    (runtime/'aura/board/identity/spoken_query.py').write_bytes(candidate_query.read_bytes())
    after=python_manifest(runtime/'aura')
    assert set(before)==set(after)
    assert [key for key in before if before[key]!=after[key]]==['board/identity/spoken_query.py']
    startup=release/'gui-startup';startup.mkdir()
    shutil.copyfile(handoff.CFG.parent/'launcher.py',startup/'launcher.py')
    config=json.loads(handoff.CFG.read_text());assert Path(config['runtime'])==GUI_RUNTIME
    config['runtime']=str(runtime)
    config.setdefault('component_sha256',{})['board/identity/spoken_query.py']=sha(candidate_query)
    (startup/'config.json').write_text(json.dumps(config,indent=2)+'\n')
    checked=subprocess.run(['/usr/bin/python3','-B',str(startup/'launcher.py'),'--config',str(startup/'config.json'),'--preflight'],
        stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=15,text=True)
    assert checked.returncode==0,checked.stderr[-300:]+checked.stdout[-300:]
    return runtime,startup,before,after


def rollback_source(folder,session,pins):
    return '''import hashlib,json,sys
from pathlib import Path
sys.dont_write_bytecode=True
if sys.flags.optimize:raise RuntimeError('Assertions required')
root=Path(ROOT)
for name,digest in PINS.items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest
sys.path.insert(0,str(root))
from handoff import BoardOps
ops=BoardOps(Path(SESSION));ops.verify()
args=sys.argv[1:];assert args in ([],['--check'],['--restore'],['--guard'])
if args in ([],['--check']):
 print(json.dumps({'passed':True,'read_only':True,'camera_pid':ops.pid('aura-camera-ui.service'),
  'unit_sha256':hashlib.sha256(ops.m.UNIT.read_bytes()).hexdigest(),
  'gui_override_present':Path(ops.meta['gui_override']).exists()}))
else:
 if args==['--restore']:
  ops.assert_idle_or_stopped();ops.assert_capture_closed()
  ops.meta['guard']='aura-reliability-manual-'+str(__import__('os').getpid());ops.save_meta();ops.arm()
 else:assert ops.meta['guard_armed']
 result=ops.restore();ops.disarm();print(json.dumps(result))
'''.replace('ROOT',repr(str(folder))).replace('PINS',repr(pins)).replace('SESSION',repr(str(session)))


def isolated_checks(folder):
    code='''import builtins,io,json,sqlite3,sys,unittest
from pathlib import Path
folder=Path(sys.argv[1]);sys.path.insert(0,str(folder/'tests'))
original=builtins.__import__
def guarded(name,*args,**kw):
 if name.split('.')[0] in ('vart','xir'):raise AssertionError('No real DPU in isolation')
 return original(name,*args,**kw)
builtins.__import__=guarded
import bootstrap
suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(name) for name in
 ('test_feature_availability','test_release_audit','test_sface_notification','test_bounded_recovery','test_owner_fence'))
out=io.StringIO();result=unittest.TextTestRunner(stream=out,verbosity=2).run(suite)
(folder/'board-isolated-tests.txt').write_text(out.getvalue())
print(json.dumps({'passed':result.wasSuccessful(),'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors)}))
sys.exit(0 if result.wasSuccessful() else 1)
'''
    env=dict(os.environ,AURA_SHARED_SOURCE=PARENT_RELEASE+'/aura',AURA_LIVE_SOURCE=PARENT_RELEASE+'/aura',
             AURA_DPU_SOURCE=PARENT_RELEASE+'/aura',AURA_CANDIDATE_SOURCE=str(folder/'candidate/aura'),
             PYTHONDONTWRITEBYTECODE='1')
    result=subprocess.run(['/usr/bin/python3','-B','-c',code,str(folder)],env=env,cwd=folder,
        stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=35)
    if result.returncode:raise RuntimeError('Board isolation failed: '+result.stderr[-300:]+result.stdout[-300:])
    parsed=json.loads(result.stdout);assert parsed['passed'] and parsed['tests']>=60
    return parsed


def check_candidate(state):
    validate_state(state)
    face=state['face_targets'];schedule=state['dpu_schedule']
    assert face['backend']=='DPU_YUNET_INT8' and face['worker_alive'] and not face['fault_latched']
    assert face['worker_faults']==0
    assert not schedule['optional']['yunet']['overruns'] and not schedule['optional'].get('sface',{}).get('overruns',0)
    assert schedule['diagnostic_failures']==0 and not schedule['diagnostic_snapshot_atomic_with_schedule']
    assert not schedule['owner_fenced']
    assert state['feature_inference']['ready'] and state['feature_status']['ready']
    counters=face['freshness_metrics']['counters']
    assert counters['observed_gap_intervals']==0 and counters['process_errors']==0
    assert face['inference']['fallback_calls']==0


def observe(ops,report,save,duration=60):
    before=ops.m.camera();check_candidate(before);start=time.monotonic();cpu=ops.m.cpu()
    stage={'scope':'SHORT_REAL_CAMERA_WORKLOAD_NOT_FIELD_ACCURACY','samples':[]};report['observation']=stage;save()
    gui_pid=ops.pid(handoff.AUDIO);primary=before['dpu_schedule']['primary_period_overruns']
    stage['initial_primary_period_overruns']=primary
    cursor=ops.meta['quiescent_cursor']
    for index in range(duration//5+1):
        h=ops.m.camera();check_candidate(h);ops.verify()
        assert h['pid']==before['pid'] and ops.pid(handoff.AUDIO)==gui_pid
        assert h['dpu_schedule']['primary_period_overruns']==primary
        assert ops.m.audio_warnings(cursor)==0
        stage['samples'].append({'elapsed_s':time.monotonic()-start,'capture_frames':h['capture_frames'],
            'detected_frames':h['detected_frames'],'face_processed':h['face_targets']['processed'],
            'face_source_age_ms':h['face_targets']['source_age_ms'],'worker_alive':h['face_targets']['worker_alive'],
            'sface_completed':h['feature_inference']['completed'],
            'yunet_calls':h['dpu_schedule']['optional']['yunet']['calls'],
            'diagnostic_failures':h['dpu_schedule']['diagnostic_failures']});save()
        if index<duration//5:time.sleep(max(0,start+(index+1)*5-time.monotonic()))
    after=ops.m.camera();check_candidate(after);elapsed=time.monotonic()-start
    assert after['dpu_schedule']['primary_period_overruns']==primary
    stage.update(duration_s=elapsed,yolo_hz=(after['detected_frames']-before['detected_frames'])/elapsed,
        face_publish_hz=(after['face_targets']['processed']-before['face_targets']['processed'])/elapsed,
        native_yunet_completed=after['dpu_schedule']['optional_diagnostics']['counters']['yunet']['native_completed']-
            before['dpu_schedule']['optional_diagnostics']['counters']['yunet']['native_completed'],
        native_sface_completed=after['feature_inference']['completed']-before['feature_inference']['completed'],
        cpu=ops.m.cpu_delta(cpu,ops.m.cpu()),usb_warning_count=ops.m.audio_warnings(cursor))
    assert elapsed>=duration and stage['yolo_hz']>=9.0 and stage['face_publish_hz']>=2.0
    assert stage['native_yunet_completed']>=100 and stage['usb_warning_count']==0
    assert ops.ready('candidate');stage['passed']=True;save()


def run(folder,wrapper,pins):
    folder=Path(folder);wrapper=Path(wrapper)
    report={'complete':False,'passed':False,'accepted':False,'phase':'PREFLIGHT'}
    save=lambda:handoff.atomic_json(folder/'report.json',report)
    save();ops=None;armed=False;rollback=None
    try:
        assert sha(Path('/etc/systemd/system/aura-camera-ui.service'))==PARENT_UNIT_SHA
        parent=json.loads(PARENT_REPORT.read_text());assert parent['complete'] and parent['accepted'] and parent['passed']
        previous=Path(PARENT_RELEASE);assert tree_manifest(previous/'aura')==parent['source_manifest']
        for name,digest in pins.items():assert sha(folder/'candidate/aura'/name)==digest
        report['board_isolated']=isolated_checks(folder);save()
        release=LIVE/('release-reliability-'+sha(wrapper)[:12]+'-'+str(os.getpid()));release.mkdir(mode=0o700)
        session=Path('/home/root/aura-coordinated-switch-20261023')/('reliability-'+str(os.getpid()));session.mkdir(mode=0o700)
        ops=handoff.BoardOps(session);before=ops.capture(wrapper)
        report['preserved_parent_fault_snapshot']=before;save()
        shutil.copytree(previous/'aura',release/'aura',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        for name,digest in pins.items():
            if name=='board/identity/spoken_query.py':continue
            p=release/'aura'/name;p.write_bytes((folder/'candidate/aura'/name).read_bytes());assert sha(p)==digest
        for name,digest in (('runtime_entry.py',ENTRY_SHA),('gil_camera_launcher.py',WRAPPER_SHA)):
            shutil.copyfile(previous/name,release/name);assert sha(release/name)==digest
        shutil.copyfile(PARENT_CONFIG,release/'board_camera_ui.json')
        identity=json.loads(Path(PARENT_IDENTITY).read_text());assert identity['feature_backend']['kind']=='dpu_sface'
        assert identity['threshold']==.5 and identity['ambiguity_margin']==.1
        database=Path(identity['database']);database_sha=sha(database)
        gui,startup,gui_before,gui_after=clone_gui(release,folder/'candidate/aura/board/identity/spoken_query.py')
        override=Path('/etc/systemd/system/aura-avatar-ui.service.d')/('zzzzzzzzzzzz-aura-reliability-'+sha(wrapper)[:12]+'.conf')
        assert not override.exists()
        data=('[Service]\nExecStart=\nExecStart=/usr/bin/python3 -B '+str(startup/'launcher.py')+
              ' --config '+str(startup/'config.json')+'\n').encode()
        (session/'gui.candidate.conf').write_bytes(data)
        unit=rewrite_unit((session/'camera.original').read_bytes(),previous,release)
        (session/'camera.candidate').write_bytes(unit);(release/'camera.candidate.service').write_bytes(unit)
        ops.meta['unit_hashes']['candidate']=hashlib.sha256(unit).hexdigest()
        ops.meta['runtimes']['candidate']=str(release/'aura');ops.meta['configs']['candidate']=str(release/'board_camera_ui.json')
        ops.meta.update(gui_override=str(override),gui_override_sha256=hashlib.sha256(data).hexdigest(),gui_launcher=str(startup/'launcher.py'))
        own_pins={name:sha(folder/name) for name in ('handoff.py','live_checks.py')}
        rollback=release/'restore_previous.py';rollback.write_text(rollback_source(folder,session,own_pins))
        ops.meta['restore_entry']=str(rollback)
        protected=[folder/name for name in ('control.py','handoff.py','live_checks.py')]
        protected += [release/'runtime_entry.py',release/'gil_camera_launcher.py',release/'board_camera_ui.json',rollback,
                      startup/'launcher.py',startup/'config.json',session/'gui.candidate.conf',Path(PARENT_IDENTITY)]
        protected += [release/'aura'/name for name in pins if name!='board/identity/spoken_query.py']
        protected += [gui/'aura/board/identity/spoken_query.py']
        for key in ('model','manifest'):protected.append(Path(identity['feature_backend'][key]))
        ops.meta['protected'].update({str(path):sha(path) for path in protected});ops.save_meta();ops.verify()
        manifest=tree_manifest(release/'aura')
        report.update(release=str(release),gui_runtime=str(gui),source_manifest=manifest,gui_sources_before=gui_before,
            gui_sources_after=gui_after,unit_sha256=ops.meta['unit_hashes']['candidate'],candidate_pins=pins,
            previous_unit_sha256=PARENT_UNIT_SHA,rollback=str(rollback),rollback_sha256=sha(rollback),
            session=str(session),identity_config=PARENT_IDENTITY,identity_config_sha256=sha(PARENT_IDENTITY),
            database=str(database),database_sha256=database_sha,gui_override=str(override))
        report['phase']='SWITCHING';save();ops.arm();armed=True
        handoff.transition(ops,'candidate');report['phase']='OBSERVING';save()
        observe(ops,report,save)
        assert sha(database)==database_sha and sha(PARENT_IDENTITY)==report['identity_config_sha256']
        assert tree_manifest(previous/'aura')==parent['source_manifest']
        assert tree_manifest(release/'aura')==manifest and python_manifest(GUI_RUNTIME/'aura')==gui_before
        assert python_manifest(gui/'aura')==gui_after
        checked=ops.m.command(['/usr/bin/python3','-B',str(rollback),'--check'],timeout=10)
        report['rollback_readonly_check']=json.loads(checked)
        ops.verify();last=ops.m.camera();check_candidate(last)
        assert last['dpu_schedule']['primary_period_overruns']==report['observation']['initial_primary_period_overruns']
        assert ops.ready('candidate')
        ops.service('stop',ops.meta['guard']+'.timer');assert not ops.active(ops.meta['guard']+'.timer')
        ops.meta.update(guard_armed=False,accepted_target='candidate');ops.save_meta();armed=False
        report.update(passed=True,accepted=True,phase='ACCEPTED',camera_pid=ops.pid(handoff.CAMERA),
                      gui_pid=ops.pid(handoff.AUDIO),xserver_pid=ops.pid(handoff.XSERVER))
    except Exception as exc:
        report['error']=type(exc).__name__+': '+str(exc)[:500]
        point=traceback.extract_tb(exc.__traceback__)[-1]
        report['error_location']={'file':point.filename,'line':point.lineno,'function':point.name}
        if ops is not None:
            try:report['fault_snapshot']=ops.m.camera()
            except Exception:pass
    finally:
        if armed and not report['accepted']:
            report['phase']='RESTORING';save()
            try:
                report['restoration']=json.loads(ops.m.command(['/usr/bin/python3','-B',str(rollback),'--guard'],timeout=300))
                assert report['restoration']['restored'];armed=False
            except Exception as exc:report['restore_error']=type(exc).__name__+': '+str(exc)[:400]
        report.update(complete=True,guard_left_armed=armed)
        if not report['accepted']:report['phase']='FINISHED_NOT_ACCEPTED'
        save()
    return {key:report.get(key) for key in ('complete','passed','accepted','phase','error','restore_error','release','camera_pid','gui_pid','guard_left_armed')}
