"""Copy the original 25-file maintenance controller; tighten only pulse bounds."""
import ast,copy
current_guard();wide_active();verify_wide_files()
j=state();assert j['phase']=='WIDE_ID_STOP_CAMERA_PROGRESS_VERIFIED'
original=Path('/home/root/aura-pan-wide-20261028/control-10282601')
assert digest(original/'deployment-manifest.json')=='5c8206ee626c91c9f311ee870245813e169ac14e554e2579554c74489066f562'
m=document(original/'deployment-manifest.json');assert len(m['files'])==25
assert all(digest(row['destination'])==row['sha256'] for row in m['files'])
dest=ROOT/'original-bounded-1400-1600';assert not dest.exists();dest.mkdir(mode=0o700)
new=copy.deepcopy(m);changed=[]
for row in new['files']:
 source=Path(row['destination']);rel=source.relative_to(original);raw=read_regular(source)
 if rel.as_posix()=='run_face_motion.py':
  before=raw;needle=b'EdgeConfig(minimum_us=500,maximum_us=2500'
  assert raw.count(needle)==1
  raw=raw.replace(needle,b'EdgeConfig(minimum_us=1400,maximum_us=1600')
  expected=ast.parse(before.decode())
  calls=[n for n in ast.walk(expected) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='EdgeConfig']
  assert len(calls)==1
  for kw in calls[0].keywords:
   if kw.arg in ('minimum_us','maximum_us'):kw.value=ast.Constant(value=1400 if kw.arg=='minimum_us' else 1600)
  assert ast.dump(expected,include_attributes=False)==ast.dump(ast.parse(raw.decode()),include_attributes=False)
  changed.append(rel.as_posix())
 row.update(destination=str(dest/rel),source=str(source),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
 target=dest/rel;target.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
 with target.open('xb') as out:out.write(raw)
 os.chmod(target,0o600)
assert changed==['run_face_motion.py']
new.update(scope='Attended 25-second test; original controller; only range tightened 1400..1600',parent_manifest_sha256=digest(original/'deployment-manifest.json'))
atomic(dest/'deployment-manifest.json',new)
for name,pin in [('bench_finite_step_deadline_fix.py','f23952abb189e2e826db7f78ff81296a81a4b57c17684258499227d215dc6dc4'),
 ('bench_observed_80us_6s.py','3538bef649574da5607aa54ffbfdee5e103fc4f1db1ebb468eade239500b876c')]:
 source=Path('/home/root/aura-face-follow-test-20261101-bebd3e7d-r2')/name
 assert digest(source)==pin
 with (ROOT/name).open('xb') as f:f.write(read_regular(source))
j.update(phase='BOUNDED_ORIGINAL_STAGED_NO_MOTION',bounded_control=str(dest),bounded_control_manifest_sha256=digest(dest/'deployment-manifest.json'),
 bounded_range_us=[1400,1600],test_duration_s=25);save(j)
print(json.dumps(dict(status=j['phase'],controller=str(dest),manifest_sha256=j['bounded_control_manifest_sha256'],
 original_25_files_preserved=True,changed_test_copy_only=['run_face_motion.py minimum_us 500->1400 maximum_us2500->1600'],
 remaining_AST_identical=True,range_us=[1400,1600],motor_commands_sent=False)))
