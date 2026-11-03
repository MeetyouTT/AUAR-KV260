CONFIG={'activation_report': '/home/root/aura-release-acceptance-20261023/63d4244d6add3ad0/report.json', 'handoff_root': '/home/root/aura-coordinated-switch-20261023/recovery50-197870', 'handoff_sha256': '12a6a4ea98f33926465d3e0cb6ae046cf3a82f29fbaa8021d4beaad249f9c734', 'rollback_path': '/home/root/aura-release-acceptance-20261023/63d4244d6add3ad0/rollback.py', 'rollback_sha256': 'f043384d1d85970a7e8e7b2f701ca573617da10774ef04a0aa1e80936a23bb8c'}
"""Default is read-only inspection. --restore arms an independent owned rollback."""
import hashlib,importlib.util,json,os,sys
from pathlib import Path


def restore_owned(ops,rollback_path):
    ops.verify()
    if ops.ready('original'):return {'passed':True,'already_original':True,'guard_left_armed':False}
    ops.assert_idle_or_stopped()
    timer='aura-manual-owned-restore-'+str(os.getpid())
    ops.meta['guard']=timer;ops.save_meta()
    ops.m.command(['systemd-run','--unit='+timer,'--on-active=450s','--property=RuntimeMaxSec=300',
        '/usr/bin/python3','-B',str(rollback_path)],timeout=10)
    ops.meta['guard_armed']=True;ops.save_meta()
    try:
        result=ops.restore();assert result['restored'] and ops.ready('original')
        ops.disarm()
        return {'passed':True,'restored':True,'guard_left_armed':False,'result':result}
    except Exception as exc:
        return {'passed':False,'error':type(exc).__name__+': '+str(exc)[:400],'guard_left_armed':True,'guard':timer}


def main(config):
    if sys.flags.optimize:raise RuntimeError('Assertions required')
    sys.dont_write_bytecode=True
    report=json.loads(Path(config['activation_report']).read_text())
    assert report['complete'] and report['accepted'] and report['passed']
    assert report['handoff_root']==config['handoff_root']
    root=Path(config['handoff_root']);module=root/'handoff.py'
    assert hashlib.sha256(module.read_bytes()).hexdigest()==config['handoff_sha256']
    rollback=Path(config['rollback_path'])
    assert hashlib.sha256(rollback.read_bytes()).hexdigest()==config['rollback_sha256']
    spec=importlib.util.spec_from_file_location('_owned_manual_restore',module)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    ops=m.BoardOps(root);ops.verify()
    if sys.argv[1:]==['--restore']:value=restore_owned(ops,rollback)
    else:
        assert sys.argv[1:] in ([],['--check'])
        value={'passed':True,'read_only':True,'boot':ops.meta['boot'],'camera_pid':ops.pid('aura-camera-ui.service'),
            'current_unit_sha256':hashlib.sha256(ops.m.UNIT.read_bytes()).hexdigest(),
            'original_unit_sha256':ops.meta['unit_hashes']['original'],
            'release_unit_sha256':ops.meta['unit_hashes']['candidate'],'audio_pid':ops.pid('aura-avatar-ui.service')}
    print(json.dumps(value))
    if not value['passed']:raise SystemExit(1)


if __name__=='__main__':main(CONFIG)
