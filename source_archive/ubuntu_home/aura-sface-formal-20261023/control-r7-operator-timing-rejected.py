"""Promote bounded event-driven admission after one short real-workload check."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import time
import traceback
import sqlite3

import handoff
from live_checks import (PARENT_RELEASE, PARENT_UNIT_SHA, completed_recovery,
                         rewrite_unit, validate_state)

LIVE_ROOT = Path('/home/root/aura-dpu-vision-20261021/postpower-retry-live')
PARENT_REPORT = Path('/home/root/aura-slot-wait-release-20261023/4970321c51bdea6c/report.json')
RUNTIME_ENTRY_SHA = 'c270e4ce9e794754ed6195202b8a00b74650bd6edc740099bf664a5e06d884cd'
UNIT = Path('/etc/systemd/system/aura-camera-ui.service')
SESSION_ROOT = Path('/home/root/aura-coordinated-switch-20261023')
PRIVATE_ROOT=Path('/home/root/.local/share/aura')
SFACE_MODEL=Path('/home/root/aura-dpu-vision-20261021/staging/03580d3216661ba0/kit/sface_public_int8.xmodel')
SFACE_MANIFEST=SFACE_MODEL.with_name('sface-manifest.json')


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def tree_manifest(root):
    rows = {}
    for path in Path(root).rglob('*'):
        assert not path.is_symlink()
        name = path.relative_to(root)
        if '__pycache__' in name.parts or '.db' in path.name or '.sqlite' in path.name:
            continue
        if path.is_file(): rows[str(name)] = {'sha256': sha(path), 'bytes': path.stat().st_size}
    return rows


def native_completed(state):
    return state['dpu_schedule']['optional_diagnostics']['counters']['yunet']['native_completed']


def check_fresh(state):
    face = state['face_targets']; fresh = face['freshness_metrics']
    assert face['slot_retry']['recovery_interval_ms'] == 50
    assert face['slot_retry'].get('independent_admission') is True
    assert face['slot_retry']['busy'] == 0
    assert fresh['observer_failures'] == 0 and fresh['gap_records_dropped'] == 0
    for key in ('observed_gap_intervals', 'post_commit_at_or_over_ttl', 'process_errors',
                'callback_errors', 'input_ttl_discarded', 'publish_ttl_discarded'):
        assert fresh['counters'][key] == 0, key
    counts = state['dpu_schedule']['optional_diagnostics']['counters']['yunet']
    assert counts['native_failed'] == face['slot_retry']['withdrawn_after_slot']


def observe(ops, target, report, save, *, duration=60):
    injected = target == 'injected'
    first = ops.m.camera(); validate_state(first, injected=injected); check_fresh(first)
    ops.m.single_owner(first['pid'])
    audio_pid = ops.pid(handoff.AUDIO); xserver_pid = ops.pid(handoff.XSERVER)
    cursor = ops.meta['quiescent_cursor']; first_cpu = ops.m.cpu(); started = time.monotonic()
    stage = {'target': target, 'camera_pid': first['pid'], 'audio_pid': audio_pid, 'samples': []}
    assert first['identity_backend']=='DPU_SFACE_INT8' and first['identity_ready'] and not first['identity_error']
    first_sface=first['feature_inference']['completed']
    db=sqlite3.connect(Path(report['new_database']).as_uri()+'?mode=ro',uri=True)
    try:
        identities=db.execute('SELECT id FROM identities').fetchall();assert len(identities)==1
        expected_person=identities[0][0]
    finally:db.close()
    stage['initial_yunet'] = dict(first['dpu_schedule']['optional']['yunet'])
    stage['initial_slot_wait'] = dict(first['dpu_schedule']['yunet_slot_wait'])
    first_matches=dict(first['match_diagnostics']['counts'])
    report.setdefault('stages', []).append(stage); save()
    for index in range(duration//5+1):
        state = ops.m.camera(); validate_state(state, injected=injected); check_fresh(state)
        assert state['identity_backend']=='DPU_SFACE_INT8' and state['identity_ready'] and not state['identity_error']
        inference=state['feature_inference'];assert inference['kind']=='DPU_SFACE_INT8'
        view=ops.m.get(8790,'/v1/ui/status')['modules']['identity']
        known=view.get('state')=='KNOWN' and view.get('person_id')==expected_person
        assert state['pid'] == first['pid']
        assert ops.pid(handoff.AUDIO) == audio_pid and ops.pid(handoff.XSERVER) == xserver_pid
        assert state['dpu_schedule']['primary_period_overruns'] == first['dpu_schedule']['primary_period_overruns']
        assert ops.m.audio_warnings(cursor) == 0
        stage['samples'].append({'elapsed_s': time.monotonic()-started,
            'detected_frames': state['detected_frames'], 'face_processed': state['face_targets']['processed'],
            'native_completed': native_completed(state), 'face_backend': state['face_targets']['backend'],
            'source_age_ms': state['face_targets']['source_age_ms'],
            'yunet': state['dpu_schedule']['optional']['yunet'],
            'slot_wait': state['dpu_schedule']['yunet_slot_wait'],
            'recovery': state['dpu_schedule']['yunet_recovery']})
        stage['samples'][-1].update(sface=inference,identity_state=view.get('state'),
            recognized_expected_enrolled_person=known,face_count=view.get('face_count'),
            match_diagnostics=state['match_diagnostics'])
        save()
        if index < duration//5:
            time.sleep(max(0, started+(index+1)*5-time.monotonic()))
    last = ops.m.camera(); validate_state(last, injected=injected); check_fresh(last)
    elapsed = time.monotonic()-started
    stage.update(observed_seconds=elapsed, yolo_hz=(last['detected_frames']-first['detected_frames'])/elapsed,
        face_publish_hz=(last['face_targets']['processed']-first['face_targets']['processed'])/elapsed,
        native_completed_delta=native_completed(last)-native_completed(first),
        cpu_window=ops.m.cpu_delta(first_cpu, ops.m.cpu()), usb_warning_count=ops.m.audio_warnings(cursor),
        final=last)
    stage['sface_native_completed_delta']=last['feature_inference']['completed']-first_sface
    stage['sface_hz']=stage['sface_native_completed_delta']/elapsed
    stage['known_correct_samples']=sum(row['recognized_expected_enrolled_person'] for row in stage['samples'])
    stage['match_decision_deltas']={key:last['match_diagnostics']['counts'][key]-first_matches[key] for key in first_matches}
    decisions=sum(stage['match_decision_deltas'].values())
    stage['known_decision_fraction']=stage['match_decision_deltas']['KNOWN']/decisions if decisions else 0.
    assert elapsed >= duration and stage['yolo_hz'] >= 9 and stage['face_publish_hz'] >= 2
    assert stage['native_completed_delta'] >= 50 and stage['usb_warning_count'] == 0
    assert stage['sface_native_completed_delta']>=30 and stage['known_correct_samples']>=6
    assert stage['known_decision_fraction']>=.7,'Known-person live matching below 70 percent'
    if injected: completed_recovery(last)
    else:
        assert last['dpu_schedule']['yunet_recovery']['phase'] == 'RUNNING'
        assert last['dpu_schedule']['yunet_recovery']['faults'] == 0
        waiter = last['dpu_schedule']['yunet_slot_wait']
        assert waiter['enabled'] and waiter['maximum_wait_ms'] == 100
        stage['slot_wait_delta'] = {key:waiter[key]-stage['initial_slot_wait'][key]
            for key in ('calls','ready','timeouts','disabled','condition_waits','total_wall_ms')}
        assert stage['slot_wait_delta']['ready'] > 0 and stage['slot_wait_delta']['condition_waits'] > 0
        sface_wait=last['dpu_schedule']['sface_slot_wait']
        assert sface_wait['maximum_wait_ms']==100
    stage['passed'] = True; save()
    return stage


def restore_source(folder, module_pins):
    return '''import hashlib,json,os,subprocess,sys
from pathlib import Path
sys.dont_write_bytecode=True
if sys.flags.optimize:raise RuntimeError('Assertions required')
root=Path(ROOT);assert root.resolve()==root
for name,digest in PINS.items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest
sys.path.insert(0,str(root))
from handoff import BoardOps
ops=BoardOps(Path(SESSION));ops.verify()
args=sys.argv[1:];assert args in ([],['--check'],['--restore'],['--guard'])
if args==['--guard']:
 assert ops.meta['guard_armed']
 print(json.dumps(ops.restore()))
elif args==['--restore']:
 ops.assert_idle_or_stopped()
 timer='aura-bounded-manual-restore-'+str(os.getpid())
 ops.meta['guard']=timer;ops.save_meta()
 ops.m.command(['systemd-run','--unit='+timer,'--on-active=450s','--property=RuntimeMaxSec=300',
                '/usr/bin/python3','-B',__file__,'--guard'],timeout=10)
 ops.meta['guard_armed']=True;ops.save_meta();ops.assert_guard_armed()
 result=ops.restore();ops.disarm();print(json.dumps(result))
else:
 print(json.dumps({'passed':True,'read_only':True,'camera_pid':ops.pid('aura-camera-ui.service'),
                  'current_unit_sha256':hashlib.sha256(ops.m.UNIT.read_bytes()).hexdigest(),
                  'previous_unit_sha256':ops.meta['unit_hashes']['original']}))
'''.replace('ROOT', repr(str(folder))).replace('PINS', repr(module_pins)).replace('SESSION', repr(str(folder/'session-placeholder')))


def run(folder, wrapper, candidate_pins):
    folder = Path(folder); wrapper = Path(wrapper)
    report = {'scope': 'FORMAL_SFACE_INT8_MIGRATION_SHORT_ACTIVATION', 'complete': False,
              'passed': False, 'accepted': False, 'phase': 'PREFLIGHT'}
    save = lambda: handoff.atomic_json(folder/'report.json', report)
    save(); armed = accepted = False; ops = None
    try:
        assert Path('/proc/sys/kernel/random/boot_id').read_text().strip() == handoff.BOOT
        parent = json.loads(PARENT_REPORT.read_text())
        assert parent['complete'] and parent['accepted'] and parent['passed']
        parent_unit = parent.get('unit_sha256') or parent['unit_hashes']['candidate']
        assert parent['release'] == PARENT_RELEASE and parent_unit == PARENT_UNIT_SHA
        previous = Path(PARENT_RELEASE)
        assert tree_manifest(previous/'aura') == parent['source_manifest']
        assert sha(UNIT) == PARENT_UNIT_SHA
        for name, digest in candidate_pins.items(): assert sha(folder/'candidate/aura'/name) == digest
        seal = hashlib.sha256(json.dumps(candidate_pins, sort_keys=True).encode()).hexdigest()
        release = LIVE_ROOT/('release-sface-int8-'+seal[:12]+'-'+str(os.getpid()))
        release.mkdir(mode=0o700)
        shutil.copytree(previous/'aura', release/'aura', ignore=shutil.ignore_patterns('__pycache__', '*.db*', '*.sqlite*'))
        for name, digest in candidate_pins.items():
            target = release/'aura'/name; target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((folder/'candidate/aura'/name).read_bytes()); assert sha(target) == digest
        manifest = tree_manifest(release/'aura')
        for name in ('runtime_entry.py', 'gil_camera_launcher.py'):
            shutil.copyfile(previous/name, release/name)
        assert sha(release/'gil_camera_launcher.py') == '0cec741d143a012b5d5aa5808f404e7b818510d2773f3b122dd1fb639222ae02'
        assert sha(release/'runtime_entry.py') == RUNTIME_ENTRY_SHA
        session = SESSION_ROOT/('sface-formal-'+str(os.getpid()))
        session.mkdir(mode=0o700)
        ops = handoff.BoardOps(session); before = ops.capture(wrapper)
        config = json.loads(Path(ops.meta['config']).read_text())
        assert config.get('yunet_dpu_recovery') is True and config.get('yunet_slot_wait_ms') == 100
        original_identity=Path(config['identity']['config'])
        old_identity=json.loads(original_identity.read_text())
        assert old_identity['feature_backend']['kind']=='windows_sface' and old_identity['threshold']==.5
        identity=json.loads(json.dumps(old_identity))
        model_id='sface-int8-12b2ff5c7de15713'
        identity.update(model_id=model_id,database=str(PRIVATE_ROOT/(model_id+'-'+str(os.getpid())+'.sqlite3')),
            threshold=.5,threshold_origin='INT8_FIXED_EXPERIMENTAL_0_50_ARCHIVED_HOLDOUT_AND_LIVE_KNOWN_CHECK',
            field_threshold_validated=False)
        identity['feature_backend']={'kind':'dpu_sface',
            'model':str(SFACE_MODEL),
            'manifest':str(SFACE_MANIFEST),
            'model_sha256':'12b2ff5c7de157133ebd5aa71665fc5ddcd1f65d9e30e2d6e965e0752e467f25',
            'manifest_sha256':'d52e4343910f7d3c775405c161e3fdf16db27396891dc617b0e5defdb878841b',
            'fallback_config':str(original_identity),'max_source_age_ms':1000}
        if (identity.get('enrollment_photos') or {}).get('enabled'):
            identity['enrollment_photos']['directory']=str(PRIVATE_ROOT/('photos-'+model_id+'-'+str(os.getpid())))
        for key in ('dpu_sface_shadow','dpu_sface_producer','dpu_sface_calibration'):identity.pop(key,None)
        new_identity=release/'board_identity.sface_int8.json'
        new_identity.write_text(json.dumps(identity,ensure_ascii=False,indent=2)+'\n')
        config['identity']['config']=str(new_identity)
        config['sface_slot_wait_ms']=100
        (release/'board_camera_ui.json').write_text(json.dumps(config, ensure_ascii=False, indent=2)+'\n')
        units = {}
        original = (session/'camera.original').read_bytes()
        (release/'camera.previous.service').write_bytes(original)
        for target in ('candidate',):
            unit = rewrite_unit(original, previous, release)
            (session/('camera.'+target)).write_bytes(unit)
            (release/('camera.'+target+'.service')).write_bytes(unit)
            units[target] = hashlib.sha256(unit).hexdigest()
            ops.meta['unit_hashes'][target] = units[target]
            ops.meta['runtimes'][target] = str(release/'aura')
            ops.meta['configs'][target] = str(release/'board_camera_ui.json')
        pins = {name: sha(folder/name) for name in ('handoff.py', 'live_checks.py')}
        restore = restore_source(folder, pins).replace(repr(str(folder/'session-placeholder')), repr(str(session)))
        rollback = release/'restore_previous.py'; rollback.write_text(restore)
        protected = [folder/name for name in ('handoff.py', 'live_checks.py', 'control.py')]
        protected += [release/'board_camera_ui.json', release/'runtime_entry.py', release/'gil_camera_launcher.py',
                      rollback]
        protected += [release/'aura'/name for name in candidate_pins]
        protected += [new_identity,folder/'migration.py',folder/'migrate_entry.py']
        for key in ('model','manifest'):protected.append(Path(identity['feature_backend'][key]))
        ops.meta['protected'].update({str(path): sha(path) for path in protected})
        timer = 'aura-sface-formal-restore-'+str(os.getpid())
        ops.meta['guard'] = timer; ops.save_meta(); ops.verify()
        report.update(previous_release=PARENT_RELEASE, previous_unit_sha256=PARENT_UNIT_SHA,
            camera_before=before, release=str(release), source_manifest=manifest,
            source_manifest_sha256=hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest(),
            candidate_pins=candidate_pins, unit_hashes=units, config_sha256=sha(release/'board_camera_ui.json'),
            unit_sha256=units['candidate'],runtime_entry_sha256=RUNTIME_ENTRY_SHA,
            handoff_root=str(session), timer=timer, rollback=str(rollback), rollback_sha256=sha(rollback),
            identity_config=str(new_identity),identity_config_sha256=sha(new_identity),
            new_database=identity['database'],old_database_sha256=sha(Path(old_identity['database']).expanduser()))
        save()
        ops.m.command(['systemd-run', '--unit='+timer, '--on-active=600s', '--property=RuntimeMaxSec=300',
                       '/usr/bin/python3', '-B', str(rollback), '--guard'], timeout=10)
        armed = True; ops.meta['guard_armed'] = True; ops.save_meta(); ops.assert_guard_armed()
        report['phase']='OFFLINE_ENROLLMENT_MIGRATION';save()
        ops.assert_idle_or_stopped();ops.stop_audio();ops.wait_pcm_closed();ops.service('stop',handoff.CAMERA)
        migration_result=ops.m.command(['/usr/bin/python3','-B',str(folder/'migrate_entry.py'),str(release),
            str(original_identity),str(new_identity),str(release/'migration-report.json')],timeout=90)
        report['migration']=json.loads(migration_result);assert report['migration']['passed']
        assert sha(Path(old_identity['database']).expanduser())==report['old_database_sha256']
        report['phase'] = 'STARTING_CLEAN'; save(); handoff.transition(ops, 'candidate')
        report['phase']='WAITING_FRONTAL_KNOWN_TARGET';save()
        ready_by=time.monotonic()+45;consecutive=0
        while time.monotonic()<ready_by:
            status=ops.m.get(8790,'/v1/ui/status')['modules']['identity']
            consecutive=consecutive+1 if status.get('state')=='KNOWN' and status.get('face_count')==1 else 0
            if consecutive>=3:break
            time.sleep(.5)
        assert consecutive>=3,'No stable known frontal target before observation'
        report['phase'] = 'OBSERVING_CLEAN'; save(); observe(ops, 'candidate', report, save)
        assert tree_manifest(release/'aura') == manifest
        assert tree_manifest(previous/'aura') == parent['source_manifest']
        assert sha(Path(old_identity['database']).expanduser())==report['old_database_sha256']
        ops.verify(); assert ops.ready('candidate')
        report['phase'] = 'VERIFIED_PENDING_ACCEPTANCE'; save()
        ops.service('stop', timer+'.timer')
        assert ops.service('show', timer+'.timer', '-p', 'ActiveState', '--value').strip() == 'inactive'
        armed = False; accepted = True
        report.update(passed=True, accepted=True, phase='ACCEPTED', camera_pid=ops.pid(handoff.CAMERA),
                      audio_pid=ops.pid(handoff.AUDIO), xserver_pid=ops.pid(handoff.XSERVER))
        try:
            ops.meta['guard_armed'] = False; ops.meta['accepted_target'] = 'candidate'; ops.save_meta()
        except Exception as error: report['metadata_warning'] = type(error).__name__+': '+str(error)[:300]
    except Exception as error:
        report['error'] = type(error).__name__+': '+str(error)[:500]
        point = traceback.extract_tb(error.__traceback__)[-1]
        report['error_location'] = {'file': point.filename, 'line': point.lineno, 'function': point.name}
        if ops is not None:
            try: report['fault_camera_snapshot'] = ops.m.camera()
            except Exception as fault: report['fault_snapshot_error'] = type(fault).__name__
    finally:
        if armed and not accepted:
            report['phase'] = 'RESTORING'; save()
            try:
                result = ops.m.command(['/usr/bin/python3', '-B', str(rollback), '--guard'], timeout=300)
                report['restoration'] = json.loads(result); assert report['restoration']['restored']
                ops.meta = json.loads((ops.folder/'session.json').read_text()); ops.disarm(); armed = False
            except Exception as error: report['restore_error'] = type(error).__name__+': '+str(error)[:400]
        report.update(complete=True, guard_left_armed=armed)
        if not accepted: report['phase'] = 'FINISHED_NOT_ACCEPTED'
        save()
        if accepted:
            try: handoff.atomic_json(release/'activation-short.json', {k:v for k,v in report.items() if k != 'camera_before'})
            except Exception as error:
                report['marker_warning'] = type(error).__name__+': '+str(error)[:300]; save()
    return {key:report.get(key) for key in ('complete', 'passed', 'accepted', 'phase', 'error', 'restore_error',
                                           'release', 'camera_pid', 'audio_pid', 'guard_left_armed')}
