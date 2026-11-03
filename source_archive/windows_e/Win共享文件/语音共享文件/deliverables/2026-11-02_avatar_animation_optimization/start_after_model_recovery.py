"""One justified GUI start after the missing original dependency is recovered."""
from pathlib import Path
import hashlib,json,subprocess,os,time,http.client
HERE=Path(__file__).resolve().parent;E=json.loads((HERE/'expected.json').read_bytes());M=json.loads((HERE/'PUBLICATION.json').read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def unit(n):
 text=subprocess.check_output(['systemctl','show',n,'--property=MainPID,ActiveState,SubState,Job,Result,ExecMainStatus,Restart,KillMode,SendSIGKILL,TimeoutStopUSec']).decode();return dict(x.split('=',1) for x in text.splitlines() if '=' in x)
def owner(pid):
 p=Path('/proc')/str(pid);return dict(pid=int(pid),birth_ticks=p.joinpath('stat').read_text().rsplit(')',1)[1].split()[19],command_sha256=sha(p/'cmdline'))
def save(p,v):
 with p.open('xb') as f:f.write((json.dumps(v,sort_keys=True,indent=2)+'\n').encode());f.flush();os.fsync(f.fileno())
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==E['boot_id']
P=Path(E['startup_path']);assert sha(P)==M['startup_after'];cfg=json.loads(P.read_bytes());R=Path(cfg['runtime'])/'aura'
assert len(cfg['component_sha256'])==380 and all(sha(R/k)==v for k,v in cfg['component_sha256'].items())
u=unit('aura-avatar-ui.service');assert u['MainPID']=='0' and u['ActiveState']=='failed' and u['Result']=='exit-code' and u['ExecMainStatus']=='1' and not u['Job']
prior=json.loads((HERE/'START_RESULT_R2.json').read_bytes());assert prior['single_submission'] is True and prior['startup_sha256']==sha(P)
old=Path('/proc')/prior['unit']['MainPID'];assert not old.exists()
stop=json.loads((HERE/'STOP_RESULT_original.json').read_bytes());assert all(u[k]==v for k,v in stop['original_GUI_properties'].items())
c=unit('aura-camera-ui.service');assert c['MainPID']==str(E['camera_owner']['pid']) and c['ActiveState']=='active' and not c['Job'] and owner(c['MainPID'])==E['camera_owner']
connection=http.client.HTTPConnection('192.168.50.1',8797,timeout=4)
try:
 connection.request('GET','/health');response=connection.getresponse();data=response.read(262145);assert response.status==200 and len(data)<=262144
 h=json.loads(data);assert h['protocol_version']==1 and h['ok'] is True and h['role']=='model_inference_only'
 assert h['backend']['tts_ready'] is True;date=response.getheader('Date');assert isinstance(date,str) and date
finally:connection.close()
assert sha(P)==M['startup_after'] and unit('aura-avatar-ui.service')==u and owner(c['MainPID'])==E['camera_owner']
save(HERE/'START_AFTER_DEPENDENCY_INTENT.json',dict(reason='previous failed startup could not connect to original Windows model Date endpoint; actual endpoint now healthy',previous_gui_unit=u,startup_sha256=sha(P),source_count=380,model_endpoint='192.168.50.1:8797',verified_model_role='model_inference_only',TTS_ready=True,model_configuration_changed=False,force_kill_or_retry_loop=False,camera_owner=E['camera_owner']))
subprocess.run(['systemctl','start','--no-block','aura-avatar-ui.service'],check=True,timeout=7)
time.sleep(1);result=dict(status='ONE_GUI_START_AFTER_CONFIRMED_DEPENDENCY_RECOVERY',unit=unit('aura-avatar-ui.service'),startup_sha256=sha(P),camera_owner=owner(c['MainPID']),single_submission=True)
save(HERE/'START_AFTER_DEPENDENCY_RESULT.json',result);print(json.dumps(result))
