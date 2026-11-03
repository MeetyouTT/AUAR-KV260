"""Derive a first live test profile that tightens only the existing runner's pulse limits."""
import ast
import base64
import copy
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parents[1]
TASK=HERE.parents[1]
sha=lambda b:hashlib.sha256(b).hexdigest()
dump=lambda v:(json.dumps(v,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()

def main():
    raw=(TASK/'candidate/controller/run_face_motion.py').read_bytes()
    assert sha(raw)=='9ebf21a1bcbc37992398e8d59f459141d7cc49163dcf400e768ea129f4e8be94'
    anchor=b'EdgeConfig(minimum_us=500,maximum_us=2500'
    assert raw.count(anchor)==1
    changed=raw.replace(anchor,b'EdgeConfig(minimum_us=1400,maximum_us=1600')
    expected=ast.parse(raw);calls=[n for n in ast.walk(expected) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='EdgeConfig']
    assert len(calls)==1
    for kw in calls[0].keywords:
        if kw.arg in ('minimum_us','maximum_us'):kw.value=ast.Constant(value=1400 if kw.arg=='minimum_us' else 1600)
    assert ast.dump(expected,include_attributes=False)==ast.dump(ast.parse(changed),include_attributes=False)
    old=json.loads((HERE/'package/deployment-manifest.json').read_bytes())
    root='/home/root/aura-face-follow-test-20261101-bebd3e7d-r2/control-first1400-1600'
    new=copy.deepcopy(old);new['schema']='aura-first-live-bounded-r2-1'
    new.update(scope='First attended 20s follow, software bounds 1400..1600us; same R2 controller and hardware safeguards',
        parent_r2_manifest_sha256=sha((HERE/'package/deployment-manifest.json').read_bytes()),test_range_us=[1400,1600])
    for row in new['files']:
        row['source']=row['destination'];row['destination']=root+'/'+row['source_rel']
        if row['source_rel']=='run_face_motion.py':row.update(bytes=len(changed),sha256=sha(changed))
    data=dump(new)
    (HERE/'package/first_follow_manifest.json').write_bytes(data)
    (HERE/'package/run_face_motion_first.py').write_bytes(changed)
    plan=dict(root=root,manifest=base64.b64encode(data).decode(),manifest_sha256=sha(data),
        runner=base64.b64encode(changed).decode(),runner_sha256=sha(changed),
        parent_manifest_sha256=new['parent_r2_manifest_sha256'])
    source='''# USE_SESSION_COMMON
import ast,base64
P=__PLAN__
current_guard();wide_active();verify_wide_files()
j=state();assert j['phase']=='DIRECTION_BOUND_FACE_PREFLIGHT' and j['control_polarity']==-1
assert digest(Path(j['r2_controller'])/'deployment-manifest.json')==P['parent_manifest_sha256']
target=Path(P['root']);assert target.parent==ROOT and not target.exists()
manifest_raw=base64.b64decode(P['manifest'],validate=True);assert hashlib.sha256(manifest_raw).hexdigest()==P['manifest_sha256']
m=json.loads(manifest_raw);parent=document(Path(j['r2_controller'])/'deployment-manifest.json')
assert len(m['files'])==len(parent['files'])==26
assert all(digest(r['destination'])==r['sha256'] for r in parent['files'])
payload={}
for r in m['files']:
 name=r['source_rel'];assert r['destination']==str(target/name) and '..' not in Path(name).parts
 raw=base64.b64decode(P['runner'],validate=True) if name=='run_face_motion.py' else read_regular(r['source'])
 assert len(raw)==r['bytes'] and hashlib.sha256(raw).hexdigest()==r['sha256']
 if name.endswith('.py'):ast.parse(raw)
 payload[name]=raw
target.mkdir(mode=0o700)
for name,raw in payload.items():
 path=target/name;path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
 with path.open('xb') as f:f.write(raw)
 os.chmod(path,0o600)
with (target/'deployment-manifest.json').open('xb') as f:f.write(manifest_raw)
settings=dict(schema='aura-face-zone-settings-1',board_boot_id=BOOT,target_kind='face',reference='face_center',
 mirror_horizontal=True,frame_width=640,frame_height=480,left_ratio=0.,viewport=[8,112,568,300],
 left_camera_ratio=.25,right_ratio=(84.+400.*.75)/568.)
atomic(ROOT/'first-follow-zone.json',settings)
atomic(ROOT/'first-follow-human.json',dict(boot_id=BOOT,user_requested='需要转轴跟着人脸转动',
 current_direction_evidence_sha256=j['direction_evidence_sha256'],test_only=True,
 duration_s=20,range_us=[1400,1600],mechanical_zero_calibrated=False,physical_angle_measured=False))
j.update(first_follow_controller=str(target),first_follow_manifest_sha256=P['manifest_sha256'],
 first_follow_runner_sha256=P['runner_sha256'],phase='BOUNDED_FACE_TEST_PREPARED');save(j)
print(json.dumps(dict(status=j['phase'],range_us=[1400,1600],duration_s=20,files=26,
 manifest_sha256=P['manifest_sha256'],runner_sha256=P['runner_sha256'],controller_algorithms_changed=False,
 current_business_source_written=False,motion_started=False)))
'''.replace('__PLAN__',repr(plan))
    (HERE/'remote/stage_bounded_follow.py').write_text(source,encoding='utf-8',newline='\n')
    record=dict(status='BOUNDED_PROFILE_AST_VERIFIED',only_changed_keywords={'minimum_us':[500,1400],'maximum_us':[2500,1600]},
        whole_remaining_ast_identical=True,runner_sha256=sha(changed),manifest_sha256=sha(data),
        controller_tests_carried_from_unchanged_r2=41,gui_not_part_of_standalone_test=True)
    (HERE/'evidence/bounded_profile_check.json').write_bytes(dump(record))
    print(json.dumps(record))

if __name__=='__main__':main()
