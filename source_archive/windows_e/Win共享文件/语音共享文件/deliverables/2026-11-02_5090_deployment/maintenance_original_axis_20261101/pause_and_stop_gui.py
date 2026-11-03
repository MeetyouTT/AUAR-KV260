"""Normal GUI pause/stop for the authorized maintenance window; no camera or axis control."""
import datetime
import hashlib
import http.client
import json
from pathlib import Path
import subprocess
import time

BOOT='903cfade-b93c-48fa-804e-379be1967313'
STARTUP=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13/startup/config.json')
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
assert hashlib.sha256(STARTUP.read_bytes()).hexdigest()=='3fd124287463650f48232cb387c78d01399bad7ddcda483db725163298de4591'
for pid,birth in ((16314,'1738385'),(16318,'1738515'),(1333,'2359')):
    assert (Path('/proc')/str(pid)/'stat').read_text().rsplit(')',1)[1].split()[19]==birth

def request(command=None):
    connection=http.client.HTTPConnection('127.0.0.1',8783,timeout=3)
    try:
        headers={'Origin':'http://127.0.0.1:8783','Host':'127.0.0.1:8783','Content-Type':'application/json'}
        if command:connection.request('POST','/api/command',json.dumps({'type':command}).encode(),headers)
        else:connection.request('GET','/api/state')
        response=connection.getresponse();raw=response.read(2097153)
        assert response.status==200 and len(raw)<=2097152
        return json.loads(raw)
    finally:connection.close()

state=request();dialogue=state.get('board_business',{}).get('dialogue',{})
assert state.get('playing') is False and state.get('phase')=='IDLE' and dialogue.get('pending') is False
assert state.get('automatic_conversation',{}).get('speech_active') is False
initial_enabled=state['handsfree_dialogue']['enabled']
if initial_enabled:request('conversation_toggle')
deadline=time.monotonic()+12
while True:
    state=request();hands=state['handsfree_dialogue']
    if hands['enabled'] is False and hands['state']=='PAUSED' and hands['microphone_open'] is False:break
    assert time.monotonic()<deadline,'Pause still pending; no stop sent'
    time.sleep(.25)
assert state.get('playing') is False and state.get('board_business',{}).get('dialogue',{}).get('pending') is False
assert json.loads(Path('/home/root/.local/share/aura-board-business/listening_preference.json').read_bytes())=={'version':1,'enabled':False}
assert hashlib.sha256(STARTUP.read_bytes()).hexdigest()=='3fd124287463650f48232cb387c78d01399bad7ddcda483db725163298de4591'
result=subprocess.run(['systemctl','stop','--no-block','aura-avatar-ui.service'],capture_output=True,text=True,timeout=8)
assert result.returncode==0
deadline=time.monotonic()+20
while True:
    unit=subprocess.run(['systemctl','show','aura-avatar-ui.service','--property=MainPID,ActiveState,SubState,Job,Result'],capture_output=True,text=True,timeout=4)
    assert unit.returncode==0
    fields=dict(line.split('=',1) for line in unit.stdout.splitlines() if '=' in line)
    stopped=(fields.get('MainPID')=='0' and fields.get('ActiveState')=='inactive' and fields.get('SubState')=='dead' and not fields.get('Job'))
    if stopped or time.monotonic()>=deadline:break
    time.sleep(.4)
print(json.dumps({'schema':'aura-normal-gui-maintenance-stop-1','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'boot_id':BOOT,'initial_listening_enabled':initial_enabled,'saved_listening_enabled':False,
    'normal_stop_sent_once':True,'status':'GUI_STOPPED' if stopped else 'GUI_STOP_PENDING',
    'unit':fields,'camera_stop_requested':False,'fpga_or_motion_requested':False,'forced_action':False}))
