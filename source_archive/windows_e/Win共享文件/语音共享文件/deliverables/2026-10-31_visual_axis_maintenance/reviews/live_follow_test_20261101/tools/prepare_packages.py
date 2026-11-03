"""Prepare the existing finite initializer for wide build and the complete isolated R2 inventory."""
import ast
import base64
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parents[1]
TASK=HERE.parents[1]
BUSINESS=TASK.parents[1]
WIDE=BUSINESS.parent/'协作任务/2026-10-28_整机联动与舵机范围/offline_wide'
R2=TASK/'reviews/v24_compatibility/candidate_r2'
BOARD='/home/root/aura-face-follow-test-20261101-bebd3e7d-r2'
CONTROL=BOARD+'/control-r2-ab3ef93bbb9675e4'
sha=lambda b:hashlib.sha256(b).hexdigest()
dump=lambda v:(json.dumps(v,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()

def main():
    stage=HERE/'package';stage.mkdir(exist_ok=True)
    original=(BUSINESS/'deliverables/2026-10-23_pan_joint_firmware/scripts/bench_finite_step.py').read_bytes()
    assert original.count(b'0x778d2512')==1
    initializer=original.replace(b'0x778d2512',b'0x10282601')
    ast.parse(initializer)
    (stage/'bench_finite_step.py').write_bytes(initializer)
    old=json.loads((WIDE/'manifests/controller-manifest.json').read_bytes())
    assert len(old['files'])==25
    edits={}
    for name,expected in (
        ('continuous_session.py','ab3ef93bbb9675e411c2258dcc53078cd5a7b2cdd233f33713264f4dc6dc3dd2'),
        ('session_target_lock.py','7c3bda738c05f6454c9659da2d480dccf04500978074626a96c7bafbe097aa4c')):
        raw=(R2/'controller'/name).read_bytes();assert sha(raw)==expected
        edits[name]=raw
    files=[]
    for oldrow in old['files']:
        row=dict(oldrow);name=row['source_rel'];row['destination']=CONTROL+'/'+name
        row['source']=oldrow['destination']
        if name in edits:
            row.update(source=BOARD+'/staging/'+name,bytes=len(edits[name]),sha256=sha(edits[name]))
        files.append(row)
    name='session_target_lock.py'
    files.append(dict(source=BOARD+'/staging/'+name,source_rel=name,destination=CONTROL+'/'+name,
        bytes=len(edits[name]),sha256=sha(edits[name])))
    assert len(files)==26 and len({x['source_rel'] for x in files})==26
    manifest=dict(schema='aura-continuous-face-zone-wide-r2-1',
        scope='Complete isolated R2 controller; explicit current-boot qualification and new session still required',
        is_motion_permit=False,baseline_manifest_sha256=sha((WIDE/'manifests/controller-manifest.json').read_bytes()),
        files=files)
    manifest_raw=dump(manifest)
    (stage/'deployment-manifest.json').write_bytes(manifest_raw)
    payload=dict(root=CONTROL,manifest_b64=base64.b64encode(manifest_raw).decode(),manifest_sha256=sha(manifest_raw),
        baseline_files=old['files'],edits={n:base64.b64encode(b).decode() for n,b in edits.items()},
        initializer_b64=base64.b64encode(initializer).decode(),initializer_sha256=sha(initializer),
        initializer_original_sha256=sha(original),initializer_only_change='build 0x778d2512 -> 0x10282601')
    (stage/'package_plan.json').write_bytes(dump(payload))
    script='''# USE_SESSION_COMMON
import ast,base64
P=__PLAN__
current_guard();wide_active();verify_wide_files()
j=state();assert j['phase']=='WIDE_ID_STOP_CAMERA_PROGRESS_VERIFIED'
target=Path(P['root']);assert target.parent==ROOT and not target.exists() and not target.is_symlink()
for row in P['baseline_files']:
    raw=read_regular(row['destination']);assert len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256']
manifest_raw=base64.b64decode(P['manifest_b64'],validate=True)
assert hashlib.sha256(manifest_raw).hexdigest()==P['manifest_sha256']
manifest=json.loads(manifest_raw);assert len(manifest['files'])==26
payload={}
for row in manifest['files']:
    name=row['source_rel'];path=Path(name)
    assert not path.is_absolute() and '..' not in path.parts and row['destination']==str(target/path)
    raw=base64.b64decode(P['edits'][name],validate=True) if name in P['edits'] else read_regular(row['source'])
    assert len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256']
    if name.endswith('.py'):ast.parse(raw,filename=name)
    payload[name]=raw
target.mkdir(mode=0o700)
for name,raw in payload.items():
    path=target/name;path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
    with path.open('xb') as handle:handle.write(raw)
    os.chmod(path,0o600)
with (target/'deployment-manifest.json').open('xb') as handle:handle.write(manifest_raw)
assert all(digest(row['destination'])==row['sha256'] for row in manifest['files'])
initial=base64.b64decode(P['initializer_b64'],validate=True)
assert hashlib.sha256(initial).hexdigest()==P['initializer_sha256']
with (ROOT/'bench_finite_step_wide.py').open('xb') as handle:handle.write(initial)
j.update(r2_controller=str(target),r2_controller_manifest_sha256=P['manifest_sha256'],
    initializer_sha256=P['initializer_sha256']);save(j)
print(json.dumps(dict(status='ISOLATED_R2_STAGED_NOT_STARTED',controller=str(target),files=26,
    unchanged_copied=24,source_files_replaced_or_added=2,manifest_sha256=P['manifest_sha256'],
    initializer_sha256=P['initializer_sha256'],production_written=False,motion_commands_sent=0)))
'''.replace('__PLAN__',repr(payload))
    (HERE/'remote/stage_r2_controller.py').write_text(script,encoding='utf-8',newline='\n')
    print(json.dumps(dict(controller_files=26,unchanged=24,edits=2,manifest_sha256=sha(manifest_raw),
        initializer_sha256=sha(initializer),initializer_original_sha256=sha(original)),ensure_ascii=False))

if __name__=='__main__':main()
