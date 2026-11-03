import hashlib,json,os,subprocess,time,urllib.request
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/da36c36a')
G=Path('/home/root/aura-pan-current-20261024/16a07283/gui-manual-bound-v1');A=G/'runtime/aura'
F=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def get(port,path):
 o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
 with o.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as r:return json.load(r)
def props(unit):
 raw=subprocess.check_output(['systemctl','show',unit,'-p','MainPID','-p','ActiveState','-p','SubState','-p','NRestarts'],text=True)
 return dict(x.split('=',1) for x in raw.splitlines() if '=' in x)
s=json.loads((R/'state.json').read_text());boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert s['boot']==boot and s['phase'] in ('JOINT_NATIVE_RUNNING_GUI_STARTING','JOINT_BUSINESS_RESTORED_MOTION_UNBOUND')
assert Path('/proc/device-tree/fpga-full/firmware-name').read_bytes().rstrip(b'\0').decode()=='aura-visual-servo-b4096-v2.bit.bin'
assert sha(G/'startup/config.json')=='d12af30e70b75be8fd54d6d030e3b98a9df204bacb803fbf6fc5914e9f391594'
pins=json.loads((G/'startup/config.json').read_text())['component_sha256'];assert all(sha(A/n)==h for n,h in pins.items())
u=get(8783,'/api/state');m=u['manual_pan'];h=get(8790,'/health');d=h['dpu_schedule'];g=props('aura-avatar-ui.service')
assert h['pid']==s['current_camera_pid'] and not d['owner_fenced'] and h['identity']['ready']
assert g['ActiveState']=='active' and int(g['MainPID'])>0
assert m['state']=='FAULT' and not m['automatic_following'] and m.get('readback') is None
assert 'no MMIO' in m['error']
owned=[]
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:
  if any(os.path.realpath(fd)=='/dev/mem' for fd in (p/'fd').iterdir()):owned.append(int(p.name))
 except OSError:pass
assert not owned
proof=json.loads((R/'id-stop.json').read_text());assert proof['boot_id']==boot and proof['identity_stop_passed']
assert proof['after_stop']['flags']==0 and proof['after_stop']['lease_left_ms']==0
report=dict(status='JOINT_BUSINESS_RESTORED_MOTION_UNBOUND',boot_id=boot,camera_pid=h['pid'],gui_pid=int(g['MainPID']),
 firmware='aura-visual-servo-b4096-v2.bit.bin',gui_pins=len(pins),automatic_following=False,
 manual_state=m['state'],manual_error=m['error'],id_stop_after_load=proof['after_stop'],
 id_stop_readback_is_current_mechanical_position=False,physical_reference_bound=False,
 output_owner_pids=owned,ARM_sent=False,COMMIT_sent=False,BIND_sent=False,REFERENCE_sent=False,
 detection_hz=h['detection_hz'],identity_ready=h['identity']['ready'],camera_error=h['camera_error'],preview_error=h['preview_error'],
 primary_overruns=d['primary_period_overruns'],optional_overruns={k:v['overruns'] for k,v in d['optional'].items()},
 native_same_boot_counters_preserved=True,protection_handoff=d['protection_handoff'],
 prior_boot_history_gap=s['previous_boot_history_gap'],ui_phase=u['phase'],audio_state=u['audio_output_state'],
 read_only_audit=True,mmio_opened_by_audit=False,observed_mono_s=time.monotonic())
s.update(phase=report['status'],current_gui_pid=report['gui_pid'],automatic_following=False)
(R/'state.json').write_text(json.dumps(s,indent=2)+'\n')
(R/'current-restoration-status.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
