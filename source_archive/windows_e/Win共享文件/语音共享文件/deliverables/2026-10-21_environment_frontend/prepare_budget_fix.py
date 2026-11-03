"""Preserve the active integration; overlay only the capture budget correction."""
import base64,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[1]
sys.path.insert(0,str(PROJECT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
for name in ('integration_candidate.json','integration_board_baseline.json','integration_deployment.json','integration_smoke.json','integration_tests_log.log'):
 src=HERE/name;dst=HERE/'initial_integration'/name;dst.parent.mkdir(exist_ok=True)
 if not dst.exists():dst.write_bytes(src.read_bytes())
base=json.loads(ssh('python3 -B -',r'''
import json,re,subprocess
from pathlib import Path
unit=subprocess.check_output(['systemctl','cat','aura-avatar-ui.service'],text=True)
config=Path(re.findall(r'--config (\S+)',unit)[-1]);cfg=json.loads(config.read_text())
assert str(config) in subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','ExecStart'],text=True)
print(json.dumps({'ui_unit':unit,'runtime':cfg['runtime'],'config_path':str(config),'startup_config':cfg,'baseline_files':{}}))
''',timeout=20))
assert 'candidate-0a4d1ec72b51' in base['runtime']
(HERE/'integration_board_baseline.json').write_text(json.dumps(base,indent=2)+'\n',encoding='utf-8')
names=['aura/board/runtime/audio/automatic_capture.py','aura/tests/framework/test_remote_frontend.py']
payload={}
for n in names:
 data=(PROJECT/n).read_bytes();(HERE/'integration_sources'/n).write_bytes(data)
 payload[n]=base64.b64encode(data).decode()
template=(PROJECT/'deliverables/2026-10-20_listening_timing/prepare.py').read_text(encoding='utf-8')
remote=template.split("remote=r'''",1)[1].split("'''.replace('BASE'",1)[0]
remote=remote.replace('aura-listening-timing-20261020','aura-audio-frontend-20261021')
remote=remote.replace("modules=['test_listening_timing'","modules=['test_remote_frontend','test_barge_verification','test_listening_timing'",1)
remote=remote.replace('base=BASE;p=PAYLOAD','base='+repr(base)+';p='+repr(payload),1)
r=json.loads(ssh('python3 -B -',remote,timeout=250))
for key in ('tests_log','preflight_log'):(HERE/('integration_'+key+'.log')).write_text(r.pop(key),encoding='utf-8')
(HERE/'integration_candidate.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:r[k] for k in ('runtime','tests_passed','preflight_passed')}))
assert r['tests_passed'] and r['preflight_passed']
