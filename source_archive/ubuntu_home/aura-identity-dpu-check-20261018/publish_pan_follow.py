"""Freeze only reviewed pan sources and filtered/synthetic validation evidence."""
import ast,base64,hashlib,io,json,zipfile
from datetime import datetime,timezone
from pathlib import Path

job=Path(__file__).resolve().parent
aura=Path('/home/ghmd/Win共享文件/语音共享文件/aura')
delivery=aura.parent/'deliverables/2026-10-19_pan_follow'
delivery.mkdir(exist_ok=True,parents=True)
records=[]
def save(name,raw):
 p=delivery/name;p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists():assert p.read_bytes()==raw,name
 else:
  with p.open('xb') as stream:stream.write(raw)
 records.append({'path':name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
tree=ast.parse((job/'board_pan_software_suite.py').read_text())
encoded=next(ast.literal_eval(node.value.args[0]) for node in tree.body if isinstance(node,ast.Assign)
             and any(isinstance(t,ast.Name) and t.id=='data' for t in node.targets))
payload=base64.b64decode(encoded,validate=True)
assert hashlib.sha256(payload).hexdigest()=='2f1e928a6ec30f9b559288d3e63720b407085bd629117bdcacf7863a9a78a24b'
manifest=json.loads((job/'pan-source-manifest.json').read_text())
with zipfile.ZipFile(io.BytesIO(payload)) as archive:
 for item in manifest:
  raw=archive.read(item['path'])
  assert len(raw)==item['bytes'] and hashlib.sha256(raw).hexdigest()==item['sha256']
  assert (aura/item['path']).read_bytes()==raw,'Shared file changed during testing: '+item['path']
  save('source/'+item['path'],raw)
save('pan-follow-source.zip',payload)
for phase in ['pan-follow-precheck','pan-follow-board-software','pan-follow-board-final','pan-follow-http-fixture','pan-follow-final-export']:
 status=json.loads((job/('latest-'+phase+'.json')).read_text())
 origin=Path(status['evidence'])
 for name in ['source.py','status.json','response.json']:
  if (origin/name).exists():save('evidence/'+phase+'/'+name,(origin/name).read_bytes())
origin=Path(json.loads((job/'latest-pan-follow-final-export.json').read_text())['evidence'])
export=json.loads((origin/'response.json').read_text())
for item in export['files']:
 raw=(origin/item['path']).read_bytes()
 assert len(raw)==item['bytes'] and hashlib.sha256(raw).hexdigest()==item['sha256']
 save('evidence/board-results/'+item['path'],raw)
inputs=[json.loads(line) for line in (delivery/'evidence/board-results/replay.jsonl').read_text().splitlines()]
trace=[json.loads(line) for line in (delivery/'evidence/board-results/shadow.jsonl').read_text().splitlines()]
assert len(inputs)==len(trace)==90 and all(v['observation']['source_kind']=='fixture' for v in inputs)
assert sum(v['control']['accepted_commands']>0 for v in trace)==86
assert all(not row['control']['physical_actuation'] and 1460<=row['control']['pulse_us']<=1540 for row in trace)
board=json.loads((delivery/'evidence/board-results/result.json').read_text())
assert board['tests_run']==35 and not board['test_errors'] and not board['test_failures']
result={'status':'PASS_SOFTWARE_CANDIDATE_NOT_LIVE_FOLLOWING_OR_PHYSICAL_ACTUATION',
 'updated_at_utc':datetime.now(timezone.utc).isoformat(),'host_framework_tests_passed':324,
 'new_control_tests':35,'board_software_tests_passed':35,'board_http_fixture_routes_passed':2,
 'fixture_frames':90,'fixture_software_commands_accepted':86,'physical_actuation':False,
 'mechanical_calibration_verified':False,'live_camera_feed_installed':False,
 'live_following_verified':False,'active_fpga_has_vsrv':False,
 'windows_identity_sources_modified':False,'production_service_restarted_by_this_task':False,
 'board_test_boot_id':board['boot_id_unchanged'],'actual_camera_source_sha256':board['actual_camera_sha256'],
 'source_files_verified':len(manifest),'frozen_files_verified':len(records),'files':records,
 'new_source_files':['common/motion_observation.py','board/motion/camera_feed.py','board/motion/follow.py',
 'tools/board_camera_motion.py','tools/board_pan_follow.py','config/pan_follow.shadow.json','tests/framework/test_pan_follow.py'],
 'source_dependencies_unchanged':['board/motion/__init__.py','board/motion/vsrv_driver.py'],
 'remaining':['Coordinate optional camera entry deployment with Windows','Live-frame shadow validation',
              'Confirm actual mechanism/camera mounting and physical reference','Prepare matched DPU/VSRV platform',
              'Explicit physical start/stop integration and controlled mechanical validation']}
for item in records:
 raw=(delivery/item['path']).read_bytes()
 assert len(raw)==item['bytes'] and hashlib.sha256(raw).hexdigest()==item['sha256']
(delivery/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ['status','source_files_verified','frozen_files_verified','fixture_frames','fixture_software_commands_accepted']}))
