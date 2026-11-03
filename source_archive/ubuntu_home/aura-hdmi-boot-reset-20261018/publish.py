from datetime import datetime,timezone
import base64,hashlib,json
from pathlib import Path

job=Path('/home/ghmd/aura-identity-dpu-check-20261018')
delivery=Path('/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-18_hdmi_boot_reset')
delivery.mkdir(exist_ok=True)
records=[]
def save(name,raw):
 p=delivery/name;p.parent.mkdir(exist_ok=True,parents=True)
 if p.exists():assert p.read_bytes()==raw,name
 else:
  with p.open('xb') as stream:stream.write(raw)
 records.append({'path':name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
def encode(value):return (json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode()
reports={}
for phase,label in [('hdmi-boot-precheck','precheck'),('hdmi-boot-install','install')]:
 status=json.loads((job/('latest-'+phase+'.json')).read_text());assert status['complete']
 origin=Path(status['evidence']);report=json.loads((origin/'response.json').read_text())
 for name,artifact in report.pop('artifacts',{}).items():
  raw=base64.b64decode(artifact['base64'],validate=True)
  assert hashlib.sha256(raw).hexdigest()==artifact['sha256']
  save('installed/'+name,raw)
 save('evidence/'+label+'/response.json',encode(report))
 for name in ('source.py','status.json'):save('evidence/'+label+'/'+name,(origin/name).read_bytes())
 reports[label]=report
origin=Path(json.loads((job/'latest-hdmi-boot-precheck.json').read_text())['evidence'])
for name in ('actual-config.json','actual-launcher.py'):save('baseline/'+name,(origin/name).read_bytes())
old=json.loads((delivery/'baseline/actual-config.json').read_text())
new=json.loads((delivery/'installed/installed-startup-config.json').read_text())
assert [k for k in old if old[k]!=new[k]]==['display_retrain_off_seconds']
assert new['display_retrain_off_seconds']==2 and new['startup_display_retrain'] is True
assert reports['install']['status']=='PASS_PERSISTED_NEXT_BOOT_HDMI_RESET_2S'
result={'status':reports['install']['status'],'updated_at_utc':datetime.now(timezone.utc).isoformat(),
 'changed_config_keys':['display_retrain_off_seconds'],'before_seconds':1,'after_seconds':2,
 'startup_enabled':True,'board_preflight':'PASS','boot_and_current_service_pids_unchanged':True,
 'host_tests':{'command':'python3 -B -m unittest test_display_fallback test_display_startup -v',
               'working_directory':'aura/scripts/board_ui_startup','passed':17,'display_commands_are_fixtures':True},
 'reboot_performed':False,'physical_cold_boot_verified':False,'files':records}
for record in records:
 raw=(delivery/record['path']).read_bytes()
 assert len(raw)==record['bytes'] and hashlib.sha256(raw).hexdigest()==record['sha256']
(delivery/'verification.json').write_bytes(encode(result))
print(json.dumps({'status':result['status'],'frozen_files_verified':len(records),'changed_keys':result['changed_config_keys']}))
