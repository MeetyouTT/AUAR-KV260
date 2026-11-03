"""Bounded metadata-only readiness; never starts/retries a service."""
from pathlib import Path
import json,hashlib,subprocess,http.client,time
HERE=Path(__file__).resolve().parent;E=json.loads((HERE/'expected.json').read_bytes());PUB=json.loads((HERE/'PUBLICATION.json').read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def owner(pid):
 p=Path('/proc')/str(pid);return dict(pid=int(pid),birth_ticks=p.joinpath('stat').read_text().rsplit(')',1)[1].split()[19],command_sha256=sha(p/'cmdline'))
def unit(n):
 s=subprocess.check_output(['systemctl','show',n,'--property=MainPID,ActiveState,SubState,Job,Result,ExecMainStatus']).decode();return dict(x.split('=',1) for x in s.splitlines() if '=' in x)
def get():
 c=http.client.HTTPConnection('127.0.0.1',8783,timeout=3)
 try:
  c.request('GET','/api/state');r=c.getresponse();assert r.status==200;raw=r.read(1048577);assert len(raw)<=1048576;return json.loads(raw)
 finally:c.close()
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==E['boot_id']
P=Path(E['startup_path']);assert sha(P)==PUB['startup_after'];cfg=json.loads(P.read_bytes());R=Path(cfg['runtime'])/'aura'
assert len(cfg['component_sha256'])==380 and all(sha(R/k)==v for k,v in cfg['component_sha256'].items())
assert owner(E['camera_owner']['pid'])==E['camera_owner']
samples=[];ready=False;started=time.monotonic()
while time.monotonic()-started<25:
 u=unit('aura-avatar-ui.service')
 try:
  s=get();a=s['avatar_display'];h=s['handsfree_dialogue'];p=s['manual_pan']
  row=dict(at=time.monotonic(),phase=s['phase'],main=s['ui_page']=='main',pair_ready=s['character_pair']['state']=='READY',avatar_visible=a['visible'],native_frames=a['frames'],native_paint_at=a['paint_at'],enabled=h['enabled'],microphone_open=h['microphone_open'],playing=s['playing'],following=p['automatic_following'],runtime_fault_count=s['runtime_faults']['count'])
  samples.append(row)
  ready=all(row[k] for k in ('main','pair_ready','avatar_visible')) and row['native_frames']>0 and not any(row[k] for k in ('enabled','microphone_open','playing','following','runtime_fault_count'))
  if ready and len(samples)>=3 and samples[-1]['native_frames']>samples[-3]['native_frames']:break
 except (OSError,ValueError,KeyError,AssertionError,http.client.HTTPException):pass
 if u['ActiveState']=='failed':break
 time.sleep(.6)
g=unit('aura-avatar-ui.service');c=unit('aura-camera-ui.service');gtk=None;mapped=False
if g['MainPID']!='0':
 launch=json.loads((Path(cfg['runtime'])/'launch.json').read_bytes());assert launch['boot_id']==E['boot_id'] and launch['supervisor_pid']==int(g['MainPID']);gtk=owner(launch['pid'])
 maps=Path('/proc',str(gtk['pid']),'maps').read_text();mapped=any(str(R/'tools/libaura_yuki.so') in line and '(deleted)' not in line for line in maps.splitlines())
result=dict(status='READY_WITH_NEW_NATIVE_LIBRARY' if ready and mapped else 'NOT_READY_NO_AUTOMATIC_RETRY',boot_id=E['boot_id'],startup_sha256=sha(P),component_count=380,all_380_pins_match=True,gui_unit=g,gui_owner=owner(g['MainPID']) if g['MainPID']!='0' else None,gtk_owner=gtk,camera_owner=owner(c['MainPID']),new_native_library_sha256=sha(R/'tools/libaura_yuki.so'),library_mapped_into_current_GTK=mapped,samples=samples,physical_screen_human_acceptance=False,axis_audio_or_model_commands=0)
assert result['camera_owner']==E['camera_owner']
print(json.dumps(result))
