"""Observe the already-requested normal GUI start; never resubmit it."""
import hashlib
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
assert json.loads((HERE/'CURRENT_GUI_RESTORE_REQUEST.json').read_text())['start_sent_once'] is True
code=r'''
import datetime,hashlib,http.client,json,subprocess,time
from pathlib import Path
root=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
startup_raw=(root/'startup/config.json').read_bytes()
assert hashlib.sha256(startup_raw).hexdigest()=='680fd752c74e75bfbbcd73a296f21f4f39134ce4863a6bc30643c7e77feae1c0'
startup=json.loads(startup_raw);runtime=Path(startup['runtime']);aura=runtime/'aura'
def unit():
    p=subprocess.run(['systemctl','show','aura-avatar-ui.service','--property=MainPID,ActiveState,SubState,Job,Result,ExecMainStatus'],capture_output=True,text=True,timeout=3)
    assert p.returncode==0
    return dict(line.split('=',1) for line in p.stdout.splitlines() if '=' in line)
def read():
    c=http.client.HTTPConnection('127.0.0.1',8783,timeout=2)
    try:
        c.request('GET','/api/state');r=c.getresponse();body=r.read(2097153)
        assert r.status==200 and len(body)<=2097152
        state=json.loads(body);pair=state.get('character_pair') or {};hf=state.get('handsfree_dialogue') or {};biz=state.get('board_business') or {};display=state.get('avatar_display') or {};pan=state.get('manual_pan') or {}
        value={'ui_page':state.get('ui_page'),'phase':state.get('phase'),'playing':state.get('playing'),
            'pair_ready':pair.get('state')=='READY','production_selected':pair.get('production_selected'),
            'avatar_visible':display.get('visible'),'avatar_frames':display.get('frames'),
            'listening_enabled':hf.get('enabled'),'microphone_open':hf.get('microphone_open'),'listening_state':hf.get('state'),
            'business_started':biz.get('started'),'writer_held':(biz.get('writer') or {}).get('held'),
            'clock_anchored':(biz.get('clock') or {}).get('anchored'),
            'memory_running':(biz.get('memory') or {}).get('running'),
            'runtime_fault_count':(state.get('runtime_faults') or {}).get('count'),
            'pan_state':pan.get('state'),'pan_following':pan.get('automatic_following'),
            'pan_flags':(pan.get('readback') or {}).get('flags'),'pan_lease_left_ms':(pan.get('readback') or {}).get('lease_left_ms')}
        return value
    finally:c.close()
started=time.monotonic();deadline=started+90;last=None;samples=[];ready=False;failed=False
while True:
    u=unit()
    if u['ActiveState']=='failed' and u['MainPID']=='0':failed=True;break
    try:
        last=read();samples.append(last)
        ready=(last['ui_page']=='main' and last['pair_ready'] and last['production_selected'] is True
            and last['avatar_visible'] is True and last['listening_enabled'] is False
            and last['microphone_open'] is False and last['listening_state']=='PAUSED'
            and last['playing'] is False and last['business_started'] is True
            and last['writer_held'] is True and last['clock_anchored'] is True
            and last['runtime_fault_count']==0)
        if ready:break
    except (OSError,ValueError,AssertionError,http.client.HTTPException):pass
    if time.monotonic()>=deadline:break
    time.sleep(1)
owners={}
if int(u['MainPID']):
    launch=json.loads((runtime/'launch.json').read_bytes())
    for label,pid in (('supervisor',int(u['MainPID'])),('gtk',launch['pid']),('camera',79866)):
        p=Path('/proc')/str(pid)
        owners[label]={'pid':pid,'birth_ticks':p.joinpath('stat').read_text().rsplit(')',1)[1].split()[19],
            'command_sha256':hashlib.sha256(p.joinpath('cmdline').read_bytes()).hexdigest()}
assert (root/'startup/config.json').read_bytes()==startup_raw
assert all(hashlib.sha256((aura/key).read_bytes()).hexdigest()==sha for key,sha in startup['component_sha256'].items())
print(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'status':'CURRENT_GUI_RESTORED_READY_PAUSED' if ready else 'GUI_FAILED' if failed else 'GUI_NOT_ALL_READY',
    'unit':u,'waited_seconds':time.monotonic()-started,'last_metadata':last,'owners':owners,
    'startup_sha256':hashlib.sha256(startup_raw).hexdigest(),'components_verified':380,
    'start_or_other_commands_sent':False,'sources_changed':False}))
'''
helper=HERE.parent.parent/'2026-10-18_board_dialogue/board_ssh.py'
spec=importlib.util.spec_from_file_location('ready_wait_transport',helper)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
output=HERE/'CURRENT_GUI_RESTORED_READY.json';assert not output.exists()
value=json.loads(module.ssh('/usr/bin/python3 -B -I -S -',code,timeout=105))
with output.open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2)
print(json.dumps(value))
