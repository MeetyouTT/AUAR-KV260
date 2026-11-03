import hashlib,http.client,json,os,subprocess,time
from pathlib import Path
ROOT=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13');TX=Path('/home/root/aura-5090-recovery-20261102-a6d4a069/cpu-optimization-1231')
OVERRIDE=Path('/run/systemd/system/aura-avatar-ui.service.d/zzzzzz-cpu-preview-graceful-1231.conf')
GUARD=b'[Service]\nKillMode=process\nSendSIGKILL=no\nTimeoutStopSec=infinity\n'
def show(name,props):
 r=subprocess.run(['systemctl','show',name,'--property='+props],capture_output=True,text=True,timeout=5);assert r.returncode==0
 return dict(v.split('=',1) for v in r.stdout.splitlines() if '=' in v)
def create(p,value):
 fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'wb') as f:f.write((json.dumps(value,sort_keys=True,indent=2)+'\n').encode());f.flush();os.fsync(f.fileno())
def proc(owner):
 p=Path('/proc')/str(owner['pid']);assert (p/'stat').read_text().rsplit(')',1)[1].split()[19]==owner['birth_ticks'];assert hashlib.sha256((p/'cmdline').read_bytes()).hexdigest()==owner['command_sha256']
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==EXPECTED['boot_id']
raw=(ROOT/'startup/config.json').read_bytes();assert hashlib.sha256(raw).hexdigest()==EXPECTED['startup_sha256'];s=json.loads(raw);aura=Path(s['runtime'])/'aura'
assert s['component_sha256']==EXPECTED['component_sha256'] and len(s['component_sha256'])==380
for n,h in s['component_sha256'].items():assert hashlib.sha256((aura/n).read_bytes()).hexdigest()==h
u=show('aura-avatar-ui.service','MainPID,ActiveState,SubState,Job,Result,ExecMainStatus');assert u=={'MainPID':'0','ActiveState':'failed','SubState':'failed','Job':'','Result':'exit-code','ExecMainStatus':'1'}
camera=show('aura-camera-ui.service','MainPID,ActiveState,SubState,Job,Result');assert camera=={'MainPID':str(EXPECTED['owners']['camera']['pid']),'ActiveState':'active','SubState':'running','Job':'','Result':'success'};proc(EXPECTED['owners']['camera'])
assert json.loads(Path('/home/root/.local/share/aura-board-business/listening_preference.json').read_bytes())=={'version':1,'enabled':False}
c=http.client.HTTPConnection('192.168.50.1',8797,timeout=3)
try:
 sent=time.monotonic();c.request('GET','/health');r=c.getresponse();received=time.monotonic();assert r.status==200 and received-sent<=1 and r.getheader('Date');body=r.read(1048577);assert len(body)<=1048576;h=json.loads(body);b=h['backend']
 assert h['ok'] is True and h['role']=='model_inference_only' and b['model']=='aura-qwen3.8-27b-abliterated:iq4_xs' and b['tts']=='omnivoice' and b['num_step']==16 and b['tts_ready'] is True and b['voice']['alive'] is True
finally:c.close()
assert not os.path.lexists(OVERRIDE)
intent=json.loads((TX/'stop-intent.json').read_bytes())
restored=show('aura-avatar-ui.service','KillMode,SendSIGKILL,TimeoutStopUSec')
assert restored=={k:intent['gui_before'][k] for k in restored}
assert (ROOT/'startup/config.json').read_bytes()==raw;proc(EXPECTED['owners']['camera'])
create(TX/'cpu-recovery-start-intent.json',{'boot_id':EXPECTED['boot_id'],'startup_sha256':EXPECTED['startup_sha256'],'board_monotonic':time.monotonic(),'single_submission':True,'guard_restored':restored})
r=subprocess.run(['systemctl','start','--no-block','aura-avatar-ui.service'],capture_output=True,timeout=6);assert r.returncode==0
result={'status':'GUI_DIAGNOSED_RTT_RECOVERY_START_SUBMITTED_ONCE','startup_sha256':EXPECTED['startup_sha256'],'guard_removed':True,'original_stop_properties_restored':restored,'camera_restarted':False,'axis_commands':False}
create(TX/'cpu-recovery-start-result.json',result);print(json.dumps(result))
