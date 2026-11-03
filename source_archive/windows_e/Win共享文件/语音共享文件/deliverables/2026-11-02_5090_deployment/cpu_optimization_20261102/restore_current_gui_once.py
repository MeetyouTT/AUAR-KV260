"""Restore the unchanged current GUI while local CPU candidates are prepared."""
import hashlib
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
code=r'''
import datetime,email.utils,hashlib,http.client,json,os,subprocess,time
from pathlib import Path
BOOT='903cfade-b93c-48fa-804e-379be1967313'
SHA='680fd752c74e75bfbbcd73a296f21f4f39134ce4863a6bc30643c7e77feae1c0'
ROOT=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
TX=Path('/home/root/aura-5090-recovery-20261102-903cfade/cpu-opt-current-gui-restore-v1')
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
raw=(ROOT/'startup/config.json').read_bytes();assert hashlib.sha256(raw).hexdigest()==SHA
startup=json.loads(raw);aura=Path(startup['runtime'])/'aura'
assert len(startup['component_sha256'])==380
assert all(hashlib.sha256((aura/key).read_bytes()).hexdigest()==sha for key,sha in startup['component_sha256'].items())
assert startup['component_sha256']['board/identity/voice_enrollment.py']=='a9113ba40efc49828ee158554b2dae70485858396680918458f6f96bba16bacb'
ui=json.loads((aura/'config/board_avatar_gtk.json').read_bytes())
selected=ui['board_business']['face_readback'];binding_raw=Path(selected['path']).read_bytes()
assert hashlib.sha256(binding_raw).hexdigest()==selected['sha256']
binding=json.loads(binding_raw);assert len(binding['source_sha256'])==25
assert all(hashlib.sha256(Path(path).read_bytes()).hexdigest()==sha for path,sha in binding['source_sha256'].items())
def unit(name):
    p=subprocess.run(['systemctl','show',name,'--property=MainPID,ActiveState,SubState,Job'],capture_output=True,text=True,timeout=4)
    assert p.returncode==0
    return dict(line.split('=',1) for line in p.stdout.splitlines() if '=' in line)
before=unit('aura-avatar-ui.service')
assert before['MainPID']=='0' and before['ActiveState'] in ('failed','inactive') and not before['Job']
assert unit('aura-camera-ui.service')=={'MainPID':'79866','ActiveState':'active','SubState':'running','Job':''}
assert (Path('/proc/79866/stat')).read_text().rsplit(')',1)[1].split()[19]=='2265436'
assert hashlib.sha256(Path('/proc/79866/cmdline').read_bytes()).hexdigest()=='acf3ee123d7674fdea6e90e79252909ca396249c870269169910879d940c27dd'
assert json.loads(Path('/home/root/.local/share/aura-board-business/listening_preference.json').read_bytes())=={'version':1,'enabled':False}
rtts=[]
for index in range(2):
    conn=http.client.HTTPConnection('192.168.50.1',8797,timeout=3);started=time.monotonic()
    try:
        conn.request('GET','/health');response=conn.getresponse();date=response.getheader('Date');body=response.read(1048577)
        rtt=time.monotonic()-started
        assert response.status==200 and date and len(body)<=1048576 and rtt<1
        assert abs((datetime.datetime.now(datetime.timezone.utc)-email.utils.parsedate_to_datetime(date)).total_seconds())<5
        rtts.append(rtt*1000)
    finally:conn.close()
assert not TX.exists();TX.mkdir(mode=0o700)
def create(name,value):
    path=TX/name;fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb') as stream:stream.write((json.dumps(value,sort_keys=True,indent=2)+'\n').encode());stream.flush();os.fsync(stream.fileno())
intent={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'startup_sha256':SHA,
    'argv':['systemctl','start','--no-block','aura-avatar-ui.service'],'health_rtt_ms':rtts,
    'components_verified':380,'selected_sources_verified':25,'sources_changed':False,'axis_start_requested':False}
create('intent.json',intent)
directory=os.open(TX,os.O_RDONLY|os.O_DIRECTORY);os.fsync(directory);os.close(directory)
result=subprocess.run(intent['argv'],capture_output=True,text=True,timeout=8)
receipt={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'start_sent_once':True,
    'returncode':result.returncode,'stderr_present':bool(result.stderr),'unit':unit('aura-avatar-ui.service'),
    'startup_sha256':SHA,'components_verified':380,'selected_sources_verified':25,
    'sources_changed':False,'clock_policy_changed':False,'axis_commands_sent':False,
    'camera_restarted':False,'board_transaction':str(TX)}
create('request.json',receipt);print(json.dumps(receipt))
'''
helper=HERE.parent.parent/'2026-10-18_board_dialogue/board_ssh.py'
assert hashlib.sha256(helper.read_bytes()).hexdigest()=='6aefec94f620c6c86fa6b17c83613b22c8599e899cb2c2fcaf36c9cdd17c7373'
spec=importlib.util.spec_from_file_location('gui_restore_transport',helper)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
output=HERE/'CURRENT_GUI_RESTORE_REQUEST.json';assert not output.exists()
value=json.loads(module.ssh('/usr/bin/python3 -B -I -S -',code,timeout=20))
with output.open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2)
print(json.dumps(value))
