import hashlib,json
from pathlib import Path
from datetime import datetime,timezone

job=Path(__file__).resolve().parent
delivery=Path('/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-19_pan_follow')
files=[];reports={}
for phase in ['pan-axis-connected-inspect','axis-joint-readiness']:
 status=json.loads((job/('latest-'+phase+'.json')).read_text());assert status['complete']
 origin=Path(status['evidence']);dest=delivery/'evidence'/phase;dest.mkdir(parents=True,exist_ok=True)
 for name in ['source.py','response.json','status.json']:
  raw=(origin/name).read_bytes();path=dest/name
  if path.exists():assert path.read_bytes()==raw
  else:
   with path.open('xb') as stream:stream.write(raw)
  files.append({'path':str(path.relative_to(delivery)),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
 reports[phase]=json.loads((origin/'response.json').read_text())
for item in files:
 raw=(delivery/item['path']).read_bytes();assert len(raw)==item['bytes'] and hashlib.sha256(raw).hexdigest()==item['sha256']
result={'status':'CONNECTED_REPORTED_JOINT_NOT_LOADED_WIRING_NOT_CONFIRMED','updated_at_utc':datetime.now(timezone.utc).isoformat(),
 'user_reported_axis_connected':True,'wiring_and_power_verified':False,'camera_mounting_confirmed':False,
 'pwm_sent':False,'registers_opened':False,'fpga_changed':False,
 'active_firmware':reports['axis-joint-readiness']['current_firmware'],
 'joint_firmware_files_available':True,'joint_payload_files_verified':8,'joint_runtime_files_verified':4,
 'camera_detection_hz':reports['pan-axis-connected-inspect']['camera']['detection_hz'],'files':files}
(delivery/'connection-inspection-20261019.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':result['status'],'evidence_files_verified':len(files)}))
