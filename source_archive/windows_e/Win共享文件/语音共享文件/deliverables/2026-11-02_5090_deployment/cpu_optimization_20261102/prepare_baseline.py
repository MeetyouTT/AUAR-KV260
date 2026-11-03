"""Check frozen handoff and choose the baseline page once; no axis commands."""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
handoff = json.loads((HERE/'AXIS_COORDINATION_HANDOFF.json').read_text(encoding='utf-8'))
assert handoff['status'] == 'AXIS_STOP_CONFIRMED_FROZEN_FOR_CPU_OPTIMIZATION'
expected = {'boot':handoff['boot_id'],'startup_sha':handoff['startup_sha256'],
            'owners':handoff['owners'],'pan_pins':handoff['pan_component_pins']}
code = 'EXPECTED = '+repr(expected)+'\n'+r'''
import datetime,hashlib,http.client,json,time
from pathlib import Path
STARTUP=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13/startup/config.json')
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==EXPECTED['boot']
raw=STARTUP.read_bytes();assert hashlib.sha256(raw).hexdigest()==EXPECTED['startup_sha']
startup=json.loads(raw);aura=Path(startup['runtime'])/'aura'
assert len(startup['component_sha256'])==380
assert all(hashlib.sha256((aura/name).read_bytes()).hexdigest()==sha for name,sha in startup['component_sha256'].items())
for owner in EXPECTED['owners']:
    root=Path('/proc')/str(owner['pid'])
    assert (root/'stat').read_text().rsplit(')',1)[1].split()[19]==owner['birth']
    assert hashlib.sha256((root/'cmdline').read_bytes()).hexdigest()==owner['cmd_sha256']
for key,pin in EXPECTED['pan_pins'].items():
    assert startup['component_sha256'][key]==pin['pin_sha256']
    assert hashlib.sha256(Path(pin['path']).read_bytes()).hexdigest()==pin['actual_sha256']
ui=json.loads((aura/'config/board_avatar_gtk.json').read_bytes())
binding_spec=ui['board_business']['face_readback'];binding_raw=Path(binding_spec['path']).read_bytes()
assert hashlib.sha256(binding_raw).hexdigest()==binding_spec['sha256']
binding=json.loads(binding_raw)
assert len(binding['source_sha256'])==25
assert all(hashlib.sha256(Path(path).read_bytes()).hexdigest()==sha for path,sha in binding['source_sha256'].items())
def request(data=None):
    conn=http.client.HTTPConnection('127.0.0.1',8783,timeout=3)
    try:
        if data is None:conn.request('GET','/api/state')
        else:conn.request('POST','/api/command',json.dumps(data).encode(),{'Content-Type':'application/json','Origin':'http://127.0.0.1:8783'})
        resp=conn.getresponse();body=resp.read(2097153)
        assert resp.status==200 and len(body)<=2097152
        return json.loads(body)
    finally:conn.close()
state=request();pan=state['manual_pan'];hf=state['handsfree_dialogue']
assert state.get('playing') is False and state.get('phase')=='IDLE'
assert hf.get('enabled') is False and hf.get('microphone_open') is False
assert pan.get('automatic_following') is False and pan['readback']['flags']==0 and pan['readback']['lease_left_ms']==0
original_page=state.get('ui_page');changed=original_page!='vision'
if changed:
    response=request({'type':'ui_page','page':'vision'});assert response.get('ok') is True
    deadline=time.monotonic()+5
    while True:
        state=request()
        if state.get('ui_page')=='vision':break
        assert time.monotonic()<deadline
        time.sleep(.2)
assert state.get('ui_page')=='vision'
assert state['manual_pan'].get('automatic_following') is False
assert STARTUP.read_bytes()==raw
print(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'boot_id':EXPECTED['boot'],
    'startup_sha256':EXPECTED['startup_sha'],'runtime_aura':str(aura),'component_pins':startup['component_sha256'],
    'selected_binding':binding_spec,'selected_binding_sources_verified':25,'components_verified':380,
    'original_page':original_page,'baseline_page':'vision','ui_page_command_sent_once':changed,
    'axis_following':False,'saved_listening_enabled':False,'axis_commands_sent':False,
    'services_or_sources_changed':False}))
'''
helper = HERE.parent.parent/'2026-10-18_board_dialogue/board_ssh.py'
assert hashlib.sha256(helper.read_bytes()).hexdigest()=='6aefec94f620c6c86fa6b17c83613b22c8599e899cb2c2fcaf36c9cdd17c7373'
spec=importlib.util.spec_from_file_location('baseline_transport',helper)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
result=json.loads(module.ssh('/usr/bin/python3 -B -I -S -',code,timeout=20))
output=HERE/'BASELINE_PREPARED.json'
with output.open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2)
print(json.dumps({k:result[k] for k in ('utc','components_verified','selected_binding_sources_verified','original_page','baseline_page','axis_commands_sent')}))
