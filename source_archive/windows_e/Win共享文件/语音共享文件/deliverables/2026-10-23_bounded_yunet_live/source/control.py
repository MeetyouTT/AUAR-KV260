"""Short real-workload recovery test, then a clean retained release."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import time
import traceback

import handoff
from live_checks import (PARENT_RELEASE, PARENT_UNIT_SHA, completed_recovery,
                         rewrite_unit, validate_state)

LIVE_ROOT = Path('/home/root/aura-dpu-vision-20261021/postpower-retry-live')
PARENT_REPORT = Path('/home/root/aura-release-acceptance-20261023/63d4244d6add3ad0/report.json')
UNIT = Path('/etc/systemd/system/aura-camera-ui.service')
SESSION_ROOT = Path('/home/root/aura-coordinated-switch-20261023')


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
    report.setdefault('stages', []).append(stage); save()
    for index in range(duration//5+1):
        state = ops.m.camera(); validate_state(state, injected=injected); check_fresh(state)
        assert state['pid'] == first['pid']
        assert ops.pid(handoff.AUDIO) == audio_pid and ops.pid(handoff.XSERVER) == xserver_pid
        assert state['dpu_schedule']['primary_period_overruns'] == first['dpu_schedule']['primary_period_overruns']
        assert ops.m.audio_warnings(cursor) == 0
        stage['samples'].append({'elapsed_s': time.monotonic()-started,
            'detected_frames': state['detected_frames'], 'face_processed': state['face_targets']['processed'],
            'native_completed': native_completed(state), 'face_backend': state['face_targets']['backend'],
            'source_age_ms': state['face_targets']['source_age_ms'],
            'yunet': state['dpu_schedule']['optional']['yunet'],
            'recovery': state['dpu_schedule']['yunet_recovery']})
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
    assert elapsed >= duration and stage['yolo_hz'] >= 9 and stage['face_publish_hz'] >= 2
    assert stage['native_completed_delta'] >= 50 and stage['usb_warning_count'] == 0
    if injected: completed_recovery(last)
    else:
        assert last['dpu_schedule']['yunet_recovery']['phase'] == 'RUNNING'
        assert last['dpu_schedule']['yunet_recovery']['faults'] == 0
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
    report = {'scope': 'BOUNDED_YUNET_RECOVERY_SHORT_ACTIVATION', 'complete': False,
              'passed': False, 'accepted': False, 'phase': 'PREFLIGHT'}
    save = lambda: handoff.atomic_json(folder/'report.json', report)
    save(); armed = accepted = False; ops = None
    try:
        assert Path('/proc/sys/kernel/random/boot_id').read_text().strip() == handoff.BOOT
        parent = json.loads(PARENT_REPORT.read_text())
        assert parent['complete'] and parent['accepted'] and parent['passed']
        assert parent['release'] == PARENT_RELEASE and parent['unit_sha256'] == PARENT_UNIT_SHA
        previous = Path(PARENT_RELEASE)
        assert tree_manifest(previous/'aura') == parent['source_manifest']
        assert sha(UNIT) == PARENT_UNIT_SHA
        for name, digest in candidate_pins.items(): assert sha(folder/'candidate/aura'/name) == digest
        seal = hashlib.sha256(json.dumps(candidate_pins, sort_keys=True).encode()).hexdigest()
        release = LIVE_ROOT/('release-bounded-'+seal[:12]+'-'+str(os.getpid()))
        release.mkdir(mode=0o700)
        shutil.copytree(previous/'aura', release/'aura', ignore=shutil.ignore_patterns('__pycache__', '*.db*', '*.sqlite*'))
        for name, digest in candidate_pins.items():
            target = release/'aura'/name; target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((folder/'candidate/aura'/name).read_bytes()); assert sha(target) == digest
        manifest = tree_manifest(release/'aura')
        for name in ('runtime_entry.py', 'gil_camera_launcher.py'):
            shutil.copyfile(previous/name, release/name)
        assert sha(release/'gil_camera_launcher.py') == '0cec741d143a012b5d5aa5808f404e7b818510d2773f3b122dd1fb639222ae02'
        assert sha(release/'runtime_entry.py') == parent['runtime_entry_sha256']
        shutil.copyfile(folder/'injection_entry.py', release/'injection_entry.py')
        session = SESSION_ROOT/('bounded-'+str(os.getpid()))
        session.mkdir(mode=0o700)
        ops = handoff.BoardOps(session); before = ops.capture(wrapper)
        config = json.loads(Path(ops.meta['config']).read_text())
        assert config.get('yunet_dpu_recovery', False) is False
        config['yunet_dpu_recovery'] = True
        (release/'board_camera_ui.json').write_text(json.dumps(config, ensure_ascii=False, indent=2)+'\n')
        units = {}
        original = (session/'camera.original').read_bytes()
        (release/'camera.previous.service').write_bytes(original)
        for target in ('injected', 'candidate'):
            unit = rewrite_unit(original, previous, release, injected=target=='injected')
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
                      release/'injection_entry.py', rollback]
        protected += [release/'aura'/name for name in candidate_pins]
        ops.meta['protected'].update({str(path): sha(path) for path in protected})
        timer = 'aura-bounded-release-restore-'+str(os.getpid())
        ops.meta['guard'] = timer; ops.save_meta(); ops.verify()
        report.update(previous_release=PARENT_RELEASE, previous_unit_sha256=PARENT_UNIT_SHA,
            camera_before=before, release=str(release), source_manifest=manifest,
            source_manifest_sha256=hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest(),
            candidate_pins=candidate_pins, unit_hashes=units, config_sha256=sha(release/'board_camera_ui.json'),
            handoff_root=str(session), timer=timer, rollback=str(rollback), rollback_sha256=sha(rollback))
        save()
        ops.m.command(['systemd-run', '--unit='+timer, '--on-active=600s', '--property=RuntimeMaxSec=300',
                       '/usr/bin/python3', '-B', str(rollback), '--guard'], timeout=10)
        armed = True; ops.meta['guard_armed'] = True; ops.save_meta(); ops.assert_guard_armed()
        report['phase'] = 'STARTING_INJECTED'; save(); handoff.transition(ops, 'injected')
        report['phase'] = 'OBSERVING_INJECTED'; save(); observe(ops, 'injected', report, save)
        injection = json.loads((release/'injected-once.json').read_text())
        assert injection['one_time'] and injection['native_completed_before_delay']
        assert injection['requested_delay_ms'] == 31
        report['injected_delay'] = injection
        report['phase'] = 'STARTING_CLEAN'; save(); handoff.transition(ops, 'candidate')
        report['phase'] = 'OBSERVING_CLEAN'; save(); observe(ops, 'candidate', report, save)
        assert tree_manifest(release/'aura') == manifest
        assert tree_manifest(previous/'aura') == parent['source_manifest']
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
