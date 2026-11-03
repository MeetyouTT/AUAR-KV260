"""Promote only the exact qualified 30-minute runtime, with coordinated rollback."""
import ast
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import shutil
import sys
import time

PARENT=Path('/home/root/aura-post-power-20261022/helpers/fda2e51c83dd27b4/source.py')
PARENT_SHA='fda2e51c83dd27b4e64bc2c9f4129f69fba35b26a95069c20e049ffc3e71de51'
QUALIFIED_SCOPE='COORDINATED_RECOVERY50_GAP3_1MS_DUAL_MODEL_1800S_ALWAYS_RESTORED'
LIVE_ROOT=Path('/home/root/aura-dpu-vision-20261021/postpower-retry-live')


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def finite(value):return type(value) in (int,float) and math.isfinite(value)


def qualify(report,expected_hashes):
    assert report.get('scope')==QUALIFIED_SCOPE
    for key in ('complete','passed','rollback_verified','protected_audio_source_verified','gap_record_retention_passed'):
        assert report.get(key) is True,key
    assert report.get('rollback_timer_left_armed') is False
    assert report.get('error') is None and report.get('rollback_error') is None
    assert report.get('retry_hashes')==expected_hashes
    for key,minimum in (('observed_seconds',1800),('observed_yolo_hz',9),('observed_yunet_hz',2)):
        assert finite(report.get(key)) and report[key]>=minimum,key
    assert type(report.get('native_completed_delta')) is int and report['native_completed_delta']>=3600
    assert type(report.get('usb_warning_count')) is int and report['usb_warning_count']==0
    samples=report['samples'];assert len(samples)==361 and report.get('sample_count')==361
    assert all(type(s['face_targets']['source_age_ms']) is int and 0<=s['face_targets']['source_age_ms']<1000 for s in samples)
    first,last=samples[0]['dpu_schedule'],samples[-1]['dpu_schedule']
    assert first['primary_period_overruns']==last['primary_period_overruns'],'New primary deadline overrun'
    job=last['optional']['yunet'];assert job['overruns']==0 and job['disabled'] is False and job['maximum_ms']<=30
    fresh=report['freshness_final'];assert fresh['schema_version']=='aura-face-freshness-light-3'
    assert fresh['observer_failures']==0 and fresh['gap_records_dropped']==0
    assert all(fresh['counters'][k]==0 for k in ('process_errors','callback_errors','invalid_source_ages',
        'source_clock_pairs_rejected','counter_saturation','observed_gap_intervals','post_commit_at_or_over_ttl'))
    assert report['original_unit_sha256']=='84116d8faf6f4d3972f5f2eac35f8c98cf8ecbe51752a8f78d803aa8a7cdd75c'
    return True


def tree_manifest(root):
    rows={}
    for p in Path(root).rglob('*'):
        assert not p.is_symlink(),'Unreviewed source link: '+str(p)
        relative=p.relative_to(root)
        if '__pycache__' in relative.parts or '.db' in p.name or '.sqlite' in p.name:continue
        if p.is_file():rows[str(relative)]={'sha256':sha(p),'bytes':p.stat().st_size}
    return rows


def rewrite_unit(raw,old_root,new_root):
    text=raw.decode();old_root=str(old_root);new_root=str(new_root)
    assert text.count(old_root)>=2 and '[Service]\n' in text
    text=text.replace(old_root,new_root)
    old=new_root+'/gil_camera_launcher.py'
    assert text.count(old)==1
    text=text.replace(old,new_root+'/runtime_entry.py')
    assert old_root not in text and 'AURA_EXPERIMENT_GIL_MS=1' in text
    return text.encode()


def load_parent():
    assert sha(PARENT)==PARENT_SHA
    sys.dont_write_bytecode=True
    spec=importlib.util.spec_from_file_location('_qualified_camera_trial',PARENT)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    return m


def run_release(folder,wrapper,entry_bytes):
    folder=Path(folder);report={'scope':'QUALIFIED_RECOVERY50_RELEASE_ACTIVATION','passed':False,
        'complete':False,'accepted':False,'phase':'PREFLIGHT'}
    m=load_parent();atomic=lambda: m.atomic(folder/'report.json',(json.dumps(report,indent=2)+'\n').encode())
    atomic();armed=False;accepted=False;ops=None
    try:
        rows=sorted(LIVE_ROOT.glob('coordinated50-*/deployment-result.json'),key=lambda p:p.stat().st_mtime)
        rows=[p for p in rows if json.loads(p.read_text()).get('scope')==QUALIFIED_SCOPE]
        assert rows,'No completed qualified 1800s trial'
        qualified=rows[-1];d=json.loads(qualified.read_text());qualify(d,m.RETRY_HASHES)
        qhash=sha(qualified);qroot=qualified.parent;source=Path(d['candidate_runtime'])
        assert qroot.resolve()==qroot and qroot.parent==LIVE_ROOT and source==qroot/'aura'
        expected=dict(m.BASELINE);expected.update(d['source_hashes'])
        expected.update({name[len('candidate/aura/'):]:v for name,v in m.RETRY_HASHES.items() if name.startswith('candidate/aura/')})
        expected['board/identity/camera_faces.py']=d['freshness_wiring_sha256']
        expected['board/vision/ui_camera_service.py']=d['candidate_ui_sha256']
        for name,digest in expected.items():assert sha(source/name)==digest,name
        original_unit=(qroot/'camera.service.candidate').read_bytes()
        assert hashlib.sha256(original_unit).hexdigest()==d['candidate_unit_sha256']
        manifest=tree_manifest(source);seal=hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest()
        release=LIVE_ROOT/('release-recovery50-'+seal[:12]+'-'+str(os.getpid()))
        assert not release.exists();release.mkdir(mode=0o700)
        shutil.copytree(source,release/'aura',ignore=shutil.ignore_patterns('__pycache__','*.db*','*.sqlite*'))
        assert tree_manifest(release/'aura')==manifest
        launcher=(qroot/'gil_camera_launcher.py').read_bytes();assert hashlib.sha256(launcher).hexdigest()==m.RETRY_WRAPPER_SHA
        (release/'gil_camera_launcher.py').write_bytes(launcher)
        entry=ast.parse(entry_bytes.decode())
        entry_sha=next(ast.literal_eval(n.value) for n in entry.body if isinstance(n,ast.Assign)
                       and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='WRAPPER_SHA')
        assert entry_sha==m.RETRY_WRAPPER_SHA
        (release/'runtime_entry.py').write_bytes(entry_bytes)
        updated=rewrite_unit(original_unit,qroot,release)
        ops,protocol=m.prepare_handoff(wrapper,updated,release/'aura')
        timer='aura-recovery50-release-rollback-'+str(os.getpid())
        ops.meta['guard']=timer;ops.save_meta()
        rollback=folder/'rollback.py';rollback.write_text(m.rollback_source(ops.folder))
        (release/'camera.original.service').write_bytes((ops.folder/'camera.original').read_bytes())
        (release/'camera.release.service').write_bytes(updated)
        report.update(qualified_report=str(qualified),qualified_report_sha256=qhash,release=str(release),
            source_manifest_sha256=seal,source_manifest=manifest,runtime_entry_sha256=hashlib.sha256(entry_bytes).hexdigest(),
            unit_sha256=hashlib.sha256(updated).hexdigest(),handoff_root=str(ops.folder),timer=timer)
        assert sha(qualified)==qhash
        m.command(['systemd-run','--unit='+timer,'--on-active=900s','--property=RuntimeMaxSec=300',
            '/usr/bin/python3','-B',str(rollback)],timeout=10)
        armed=True;ops.meta['guard_armed']=True;ops.save_meta();ops.assert_guard_armed()
        report['phase']='ACTIVATING';atomic();protocol.transition(ops,'candidate')
        first=m.camera();m.healthy(first);m.single_owner(first['pid'])
        observed_audio_pid=ops.pid('aura-avatar-ui.service')
        observed_xserver_pid=ops.pid('xserver-nodm.service')
        settings=list((release/'process-settings'/ops.meta['boot']).glob('launch-*/process-setting-'+str(first['pid'])+'.json'))
        assert len(settings)==1
        setting=json.loads(settings[0].read_text());assert setting['actual_start_seconds']==.001 and setting['previous_seconds']==.005
        report['process_setting']=setting
        cursor=ops.meta['quiescent_cursor'];started=time.monotonic();initial_cpu=m.cpu();report['samples']=[]
        report['phase']='OBSERVING';atomic()
        for index in range(25):
            h=m.camera();m.healthy(h);assert h['pid']==first['pid']
            assert ops.pid('aura-avatar-ui.service')==observed_audio_pid
            assert ops.pid('xserver-nodm.service')==observed_xserver_pid
            face=h['face_targets'];fresh=face['freshness_metrics']
            assert face['slot_retry']['recovery_interval_ms']==50 and fresh['observer_failures']==0
            assert 0<=face['source_age_ms']<1000 and fresh['counters']['observed_gap_intervals']==0
            assert m.audio_warnings(cursor)==0
            report['samples'].append({'elapsed_s':time.monotonic()-started,'pid':h['pid'],
                'source_age_ms':face['source_age_ms'],'yunet':h['dpu_schedule']['optional']['yunet'],
                'gap_count':fresh['counters']['observed_gap_intervals']})
            report['elapsed_s']=report['samples'][-1]['elapsed_s'];atomic()
            if index<24:time.sleep(max(0,started+(index+1)*5-time.monotonic()))
        elapsed=time.monotonic()-started;last=m.camera();m.healthy(last)
        report.update(observed_seconds=elapsed,yolo_hz=(last['detected_frames']-first['detected_frames'])/elapsed,
            yunet_hz=(last['face_targets']['processed']-first['face_targets']['processed'])/elapsed,
            cpu_window=m.cpu_delta(initial_cpu,m.cpu()),usb_warning_count=m.audio_warnings(cursor))
        assert elapsed>=120 and report['yolo_hz']>=9 and report['yunet_hz']>=2 and report['usb_warning_count']==0
        assert last['dpu_schedule'].get('primary_period_overruns')==first['dpu_schedule'].get('primary_period_overruns')
        assert tree_manifest(release/'aura')==manifest and sha(release/'runtime_entry.py')==report['runtime_entry_sha256']
        ops.verify();assert ops.ready('candidate')
        report['phase']='VERIFIED_PENDING_ACCEPTANCE';atomic()
        m.atomic(release/'activation-qualified.json',(json.dumps({k:v for k,v in report.items() if k!='samples'},indent=2)+'\n').encode())
        ops.service('stop',timer+'.timer')
        guard_state=ops.service('show',timer+'.timer','-p','ActiveState','--value').strip()
        assert guard_state=='inactive'
        armed=False;accepted=True
        report.update(passed=True,accepted=True,phase='ACCEPTED',guard_state=guard_state)
        try:
            ops.meta['guard_armed']=False;ops.meta['accepted_target']='candidate';ops.save_meta()
        except Exception as exc:report['metadata_warning']=type(exc).__name__+': '+str(exc)[:300]
    except Exception as exc:
        report['error']=type(exc).__name__+': '+str(exc)[:500]
        if armed:
            try:report['fault_camera_snapshot']=m.camera()
            except Exception as fault:report['fault_snapshot_error']=type(fault).__name__
    finally:
        if not accepted and armed:
            report['phase']='RESTORING';atomic()
            try:
                result=m.command(['/usr/bin/python3','-B',str(folder/'rollback.py')],timeout=300)
                report['restoration']=json.loads(result);assert report['restoration']['restored']
                ops.meta=json.loads((ops.folder/'session.json').read_text());ops.disarm();armed=False
            except Exception as exc:report['restore_error']=type(exc).__name__+': '+str(exc)[:400]
        report.update(complete=True,guard_left_armed=armed)
        if not accepted:report['phase']='FINISHED_NOT_ACCEPTED'
        atomic()
    return {k:report.get(k) for k in ('passed','complete','accepted','phase','error','restore_error','release','guard_left_armed')}
