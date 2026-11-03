"""One frozen public ARM run with fresh production read-only guards before and after."""
from pathlib import Path
import ast
import base64
import hashlib
import json
import sys
import time
import zipfile

HERE = Path(__file__).resolve().parents[1]
PROJECT = HERE.parents[3]
JOINT = HERE.parent / 'joint_performance_20261101'
PACKAGE = PROJECT / 'deliverables/2026-10-30_board_owner/integration/dialogue_repair/joint_balance_20261101/continued_validation_20261101/pause_resume_candidate'
ARCHIVE_SHA = 'dd79bc5ea6a8b3250ecfd47f44149bc3de57c560bd9482ca46aeb62e66102b35'
MANIFEST_SHA = '3d940ab2e1caf7526d1ec2360b60fb7fe13b86e43941ea86e92ccea22ed77c8c'
sys.path.insert(0, str(PROJECT / 'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    archive = (PACKAGE / 'portable_arm_v1.zip').read_bytes()
    assert len(archive) == 54750 and sha(archive) == ARCHIVE_SHA
    with zipfile.ZipFile(PACKAGE / 'portable_arm_v1.zip') as z:
        manifest_raw = z.read('portable_arm_v1/PACKAGE_MANIFEST.json')
        assert sha(manifest_raw) == MANIFEST_SHA
        manifest = json.loads(manifest_raw)
        assert len(manifest['files']) == 14 and manifest['tests'] == 9
        assert manifest['after_sha256'] == '54fa17ac97e3fdbeeb2725b6534a86dec9ece60839f2b14ffa77c348e714dafc'
        pins = dict(manifest['files'], **{'PACKAGE_MANIFEST.json': dict(bytes=len(manifest_raw), sha256=MANIFEST_SHA)})
        assert set(z.namelist()) == {'portable_arm_v1/' + name for name in pins}
        for name, pin in pins.items():
            raw = z.read('portable_arm_v1/' + name)
            assert len(raw) == pin['bytes'] and sha(raw) == pin['sha256']
            if name.endswith('.py'):
                ast.parse(raw.decode('utf-8'), feature_version=(3, 9))
    spec_raw = (PROJECT / 'deliverables/2026-10-30_board_owner/integration/production_business_acceptance/spec.json').read_bytes()
    assert sha(spec_raw) == '62b99e24560229c78a3be000fed5752b6a50c4fb16ab6bc2c88e987561831177'
    spec = json.loads(spec_raw)
    proof = json.loads((HERE / 'evidence/preflight_1793539648715521000.json').read_bytes())['result']
    assert proof['can_continue_plan_preparation'] is True and proof['startup_sha256'] == spec['startup_sha256']
    owners = {role: {key: row[key] for key in ('pid', 'birth_ticks', 'command_sha256')}
              for role, row in proof['owners_discovered_fresh'].items()}
    common = (JOINT / 'remote/common.py').read_text('utf-8').replace(
        '8ff79452570385921e06c098b5d42c2ea1ef5dfb84d81dfa7f53a9295373d0e8', spec['source_manifest_sha256'])
    source = ((JOINT / 'package/subtitle_receipt/camera_binding_runtime.py').read_text('utf-8') + '\n' + common
              + '\nSTARTUP_SHA=' + repr(spec['startup_sha256']) + '\nEXPECTED_OWNERS=' + repr(owners)
              + '\nARCHIVE=' + repr(base64.b64encode(archive).decode()) + '\nPUBLIC_PINS=' + repr(pins) + '\n' + REMOTE)
    result = json.loads(ssh('python3 -B -', source, timeout=100))
    envelope = dict(schema='aura-pause-resume-public-arm-envelope-1',
                    utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                    source_sha256=sha(source.encode()), package_sha256=ARCHIVE_SHA,
                    package_manifest_sha256=MANIFEST_SHA, result=result)
    path = HERE / 'evidence' / ('pause_resume_public_arm_' + str(time.time_ns()) + '.json')
    raw = (json.dumps(envelope, indent=2, allow_nan=False) + '\n').encode()
    with path.open('xb') as f:
        f.write(raw)
    print(json.dumps(dict(evidence=str(path), sha256=sha(raw), result=result)))


REMOTE = r'''
import base64,io,platform,zipfile
def current_guard():
    assert os.geteuid()==0 and platform.machine()=='aarch64'
    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
    assert digest(BUSINESS/'startup/config.json')==STARTUP_SHA
before,public_before,_=preflight()
assert public_before.get('automatic_conversation',{}).get('enabled') is False
assert document('/home/root/.local/share/aura-board-business/listening_preference.json')['enabled'] is False
raw=base64.b64decode(ARCHIVE,validate=True)
assert len(raw)==54750 and hashlib.sha256(raw).hexdigest()=='dd79bc5ea6a8b3250ecfd47f44149bc3de57c560bd9482ca46aeb62e66102b35'
arm_root=Path('/home/root/pr-arm-dd79-'+str(time.time_ns()))
assert arm_root.parent==Path('/home/root') and not arm_root.exists()
arm_root.mkdir(mode=0o700)
with zipfile.ZipFile(io.BytesIO(raw)) as z:
    assert set(z.namelist())=={'portable_arm_v1/'+name for name in PUBLIC_PINS}
    assert sum(row.file_size for row in z.infolist())<1048576
    for name,pin in PUBLIC_PINS.items():
        parts=Path(name).parts
        assert not Path(name).is_absolute() and '..' not in parts and ':' not in name and '\\' not in name
        info=z.getinfo('portable_arm_v1/'+name)
        assert not info.is_dir() and (info.external_attr>>16)&0o170000!=0o120000
        payload=z.read(info)
        assert len(payload)==pin['bytes'] and hashlib.sha256(payload).hexdigest()==pin['sha256']
        target=arm_root/name
        assert arm_root in target.parents
        target.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
        with target.open('xb') as f:f.write(payload)
env=dict(os.environ);env.pop('PYTHONPATH',None)
env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1')
began=time.monotonic()
p=subprocess.run(['/usr/bin/python3','-I','-B','run_public_validation.py'],cwd=arm_root,env=env,
    capture_output=True,text=True,timeout=75,preexec_fn=lambda:os.nice(10))
(arm_root/'ARM.stdout.txt').write_text(p.stdout,encoding='utf-8')
(arm_root/'ARM.stderr.txt').write_text(p.stderr,encoding='utf-8')
proofs={}
for name in ('PORTABLE_TEST_RESULT.json','PORTABLE_RUN_RECEIPT.json'):
    try:proofs[name]=json.loads((arm_root/name).read_text('utf-8'))
    except (OSError,ValueError):proofs[name]=None
for name,pin in PUBLIC_PINS.items():
    payload=(arm_root/name).read_bytes()
    assert len(payload)==pin['bytes'] and hashlib.sha256(payload).hexdigest()==pin['sha256']
after,public_after,_=preflight()
assert before['owners']==after['owners'] and before['startup_sha256']==after['startup_sha256']
assert public_after.get('automatic_conversation',{}).get('enabled') is False
assert document('/home/root/.local/share/aura-board-business/listening_preference.json')['enabled'] is False
t=proofs['PORTABLE_TEST_RESULT.json'] or {};run=proofs['PORTABLE_RUN_RECEIPT.json'] or {}
passed=(p.returncode==0 and t.get('passed') is True and t.get('tests')==9 and t.get('failures')==0 and t.get('errors')==0
    and t.get('actual_device_model_HTTP_service_private_database_or_grant_access') is False
    and run.get('passed') is True and run.get('machine')=='aarch64'
    and run.get('manifest_sha256')=='3d940ab2e1caf7526d1ec2360b60fb7fe13b86e43941ea86e92ccea22ed77c8c'
    and run.get('pinned_files_checked_before')==14 and run.get('pinned_files_checked_after')==14)
arm_report=dict(status='PASSED' if passed else 'FAILED',machine=platform.machine(),python_version=platform.python_version(),
    public_tests=t.get('tests'),returncode=p.returncode,elapsed_seconds=time.monotonic()-began,root=str(arm_root),
    candidate_sha256='54fa17ac97e3fdbeeb2725b6534a86dec9ece60839f2b14ffa77c348e714dafc',
    private_database_or_device_services_used=False,microphone_model_or_motion_commands_sent=False,
    public_test_results=proofs,stdout_public=p.stdout,stderr_public=p.stderr,
    source_owner_output_guard_before=before,source_owner_output_guard_after=after,
    production_modified=False,all_15_package_files_verified_after=True)
(arm_root/'ARM_RESULT.json').write_text(json.dumps(arm_report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(arm_report,allow_nan=False))
'''


if __name__ == '__main__':
    main()
