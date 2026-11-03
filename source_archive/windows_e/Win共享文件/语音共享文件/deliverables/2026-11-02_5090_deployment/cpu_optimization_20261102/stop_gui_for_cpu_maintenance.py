"""One guarded normal GUI stop, using the user's frozen axis handoff."""
import hashlib
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
handoff=json.loads((HERE/'AXIS_COORDINATION_HANDOFF.json').read_text(encoding='utf-8'))
assert handoff['status']=='AXIS_STOP_CONFIRMED_FROZEN_FOR_CPU_OPTIMIZATION'
expected={'boot':handoff['boot_id'],'startup_sha':handoff['startup_sha256'],
    'owners':handoff['owners'],'pan_pins':handoff['pan_component_pins']}
code='EXPECTED = '+repr(expected)+'\n'+r'''
import datetime,hashlib,http.client,json,os,subprocess,time
from pathlib import Path
TX=Path('/home/root/aura-5090-recovery-20261102-903cfade/cpu-optimization-20261102-v1')
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
conn=http.client.HTTPConnection('127.0.0.1',8783,timeout=3)
try:
    conn.request('GET','/api/state');response=conn.getresponse();body=response.read(2097153)
    assert response.status==200 and len(body)<=2097152
    state=json.loads(body)
finally:conn.close()
assert state.get('playing') is False and state.get('phase')=='IDLE'
hands=state['handsfree_dialogue'];pan=state['manual_pan']
assert hands.get('enabled') is False and hands.get('microphone_open') is False and hands.get('state')=='PAUSED'
assert pan.get('automatic_following') is False and pan.get('state')=='READY'
assert pan['readback']['flags']==0 and pan['readback']['lease_left_ms']==0
assert json.loads(Path('/home/root/.local/share/aura-board-business/listening_preference.json').read_bytes())=={'version':1,'enabled':False}
def create(path,raw):
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
assert not TX.exists();assert TX.parent.resolve(strict=True)==TX.parent
TX.mkdir(mode=0o700)
create(TX/'startup.before.json',raw)
intent={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'boot_id':EXPECTED['boot'],
    'argv':['systemctl','stop','--no-block','aura-avatar-ui.service'],
    'startup_before_sha256':EXPECTED['startup_sha'],'original_page':state.get('ui_page'),
    'axis_already_stopped':True,'axis_commands_requested':False,'camera_stop_requested':False}
create(TX/'gui-stop-intent.json',(json.dumps(intent,sort_keys=True,indent=2)+'\n').encode())
directory=os.open(TX,os.O_RDONLY|os.O_DIRECTORY);os.fsync(directory);os.close(directory)
result=subprocess.run(intent['argv'],capture_output=True,text=True,timeout=8)
assert result.returncode==0
deadline=time.monotonic()+20
while True:
    p=subprocess.run(['systemctl','show','aura-avatar-ui.service','--property=MainPID,ActiveState,SubState,Job,Result'],capture_output=True,text=True,timeout=4)
    assert p.returncode==0
    fields=dict(line.split('=',1) for line in p.stdout.splitlines() if '=' in line)
    stopped=fields=={'MainPID':'0','ActiveState':'inactive','SubState':'dead','Job':'','Result':'success'}
    if stopped or time.monotonic()>=deadline:break
    time.sleep(.4)
maps=[]
for root in Path('/proc').iterdir():
    if not root.name.isdigit():continue
    try:text=(root/'maps').read_text()
    except (FileNotFoundError,ProcessLookupError,PermissionError):continue
    if 'libvsrv.so' in text or '/dev/mem' in text:maps.append(int(root.name))
assert STARTUP.read_bytes()==raw
assert all(hashlib.sha256(Path(pin['path']).read_bytes()).hexdigest()==pin['actual_sha256'] for pin in EXPECTED['pan_pins'].values())
receipt={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'status':'GUI_NORMALLY_STOPPED' if stopped else 'GUI_NORMAL_STOP_PENDING',
    'normal_stop_sent_once':True,'unit':fields,'startup_sha256':EXPECTED['startup_sha'],
    'native_motion_map_owners_after':maps,'pan_pins_unchanged':True,
    'camera_stop_requested':False,'axis_commands_sent':False,'forced_action':False,
    'board_transaction_directory':str(TX)}
create(TX/'gui-stop-receipt.json',(json.dumps(receipt,sort_keys=True,indent=2)+'\n').encode())
print(json.dumps(receipt))
'''
helper=HERE.parent.parent/'2026-10-18_board_dialogue/board_ssh.py'
assert hashlib.sha256(helper.read_bytes()).hexdigest()=='6aefec94f620c6c86fa6b17c83613b22c8599e899cb2c2fcaf36c9cdd17c7373'
spec=importlib.util.spec_from_file_location('normal_gui_stop_transport',helper)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
output=HERE/'GUI_STOPPED_FOR_CPU.json';assert not output.exists()
result=json.loads(module.ssh('/usr/bin/python3 -B -I -S -',code,timeout=35))
with output.open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2)
print(json.dumps(result))
