FDT_SHA='a42fca38fffcf87db0cb2e51b354127ef0959b54eb864792285f8cead552c294'
GUI_SHA='69fa9b565e9e37cbe7d8cb5a6f2aaa071ee2fb2842845c2d7b6e1cd232f2e444'
CAMERA_CONFIG='/home/root/aura-native-live-20261024/candidates/native-r4-metrics-fix/board_camera_ui.proposed.json'
CAMERA_CONFIG_SHA='e137bbb7894ecebcaadc8e57abc4bd8794c80dc3b9c1f87f09389a53ef88af20'
"""Validate that camera state is sealed before allowing a cold-boot test."""
def validate_checkpoint(document, before, boot, pid, birth, unit, alive, lock_free):
    if document.get('schema') != 'aura-native-protection-checkpoint-2' or document.get('scope') != 'final_quiescent_before_native_owner_close':
        raise ValueError('Missing sealed native checkpoint')
    s, a = document['seed'], document['auxiliary']
    if (s['boot_id'], s['source_pid'], s['source_birth_ticks'], s['checkpoint_kind']) != (boot, pid, birth, 1):
        raise ValueError('Stale checkpoint owner')
    if s['fenced'] or a['fenced'] or a['active'] or a['primary_waiting'] or any(a['pending_result_tokens']):
        raise ValueError('Unfinished native operation')
    if alive or not lock_free or any(unit.get(k) != v for k, v in [('MainPID','0'),('ExecMainStatus','0'),('Result','success')]):
        raise ValueError('Owner not stopped normally')
    schedule = before['dpu_schedule']
    for k in ['primary_calls','primary_period_overruns']:
        if s[k] < schedule[k]:raise ValueError('Primary history decreased')
    for i, task in [(1,'yunet'),(2,'sface')]:
        if s['admissions'][i] < schedule['optional'][task]['calls'] or s['overruns'][i] < schedule['optional'][task]['overruns']:
            raise ValueError('Optional history decreased')
    if a['sface_counters']['completed'] < before['identity']['feature_inference']['completed']:
        raise ValueError('Identity history decreased')
    return True

"""Fresh-boot wide-platform maintenance. No phase emits ARM or COMMIT."""
import fcntl,hashlib,json,os,subprocess,sys,time,urllib.request
from pathlib import Path
BOOT='55152f95-ea3a-4c6c-82e6-51bd553d96fd'
R=Path('/home/root/aura-pan-wide-resume-20261029/55152f95')
OLD_GUI=Path('/home/root/aura-device-skills-20261028/0cd7c3445a84475098b938d5b97175e0')
B=Path('/home/root/aura-pan-wide-20261028/release-6a4b645a5bbfd35c')
APP='aura-visual-servo-b4096-wide-v1';CAM='aura-camera-ui.service';GUI='aura-avatar-ui.service'
OPS=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(argv,timeout=12):
 p=subprocess.run(argv,capture_output=True,text=True,timeout=timeout)
 if p.returncode:raise RuntimeError('Command failed '+repr(argv)+' '+p.stderr[-500:])
 return p.stdout
def props(unit):
 return dict(s.split('=',1) for s in run(['systemctl','show',unit,'-p','MainPID','-p','ActiveState','-p','Result','-p','ExecMainStatus','-p','FragmentPath','-p','DropInPaths','-p','Restart','-p','KillMode','-p','SendSIGKILL','-p','TimeoutStopUSec']).splitlines() if '=' in s)
def get(port,path):
 with urllib.request.urlopen('http://127.0.0.1:'+str(port)+path,timeout=3) as f:return json.load(f)
def birth(pid):return int((Path('/proc')/str(pid)/'stat').read_text().rsplit(')',1)[1].split()[19])
def atomic(p,value):
 t=p.with_name(p.name+'.partial-'+str(os.getpid()))
 with t.open('x') as f:json.dump(value,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 os.replace(t,p)
def active():
 return [v[0] for v in (x.split() for x in run(['xmutil','listapps'],20).splitlines()) if len(v)==6 and v[1] in ('XRT_FLAT','PL_FLAT') and v[-1].rstrip(',')=='0']
def unit_pins():
 result={}
 for unit in [CAM,GUI]:
  p=props(unit);result[unit]={n:sha(n) for n in [p['FragmentPath']]+p['DropInPaths'].split() if n}
 return result
def fixed(s):
 assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
 assert sha('/sys/firmware/fdt')==FDT_SHA and sha(OLD_GUI/'startup/config.json')==GUI_SHA
 assert sha(CAMERA_CONFIG)==CAMERA_CONFIG_SHA
 assert all(sha(p)==h for rows in s['units'].values() for p,h in rows.items())
def prepare():
 assert not R.exists();assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
 assert sha('/sys/firmware/fdt')==FDT_SHA and sha(OLD_GUI/'startup/config.json')==GUI_SHA
 cfg=json.loads((OLD_GUI/'startup/config.json').read_text());a=Path(cfg['runtime'])/'aura'
 assert all(sha(a/n)==h for n,h in cfg['component_sha256'].items())
 manifest=json.loads((B/'candidate-manifest.json').read_text());assert sha(B/'candidate-manifest.json')=='6a4b645a5bbfd35c9107976edf27886cf8e0c91e40f48be6f052a95e1172c1cf'
 assert all(sha(p)==h for p,h in manifest['runtime_files'].items())
 assert all(sha(B/'driver'/n)==h for n,h in manifest['payload_files'].items())
 h=get(8790,'/health');u=get(8783,'/api/state');c=props(CAM);g=props(GUI)
 assert c['MainPID']==str(h['pid'])=='1332' and g['MainPID']=='1295'
 assert h['identity']['ready'] and h['dpu_schedule']['native_critical'] and not h['dpu_schedule']['owner_fenced']
 assert u['phase']=='IDLE' and u['audio_output_state']=='IDLE_READY' and not u['playing']
 assert not u['manual_pan']['automatic_following'] and not u['handsfree_dialogue']['enabled'] and not u['handsfree_dialogue']['microphone_open']
 assert u['local_recording']['state']!='RECORDING' and not u['local_transcription'].get('service',{}).get('pending')
 assert active()==['kv260-benchmark-b4096']
 R.mkdir(parents=True,mode=0o700)
 native=json.loads(Path(CAMERA_CONFIG).read_text())['native_execution']
 s={'phase':'PREPARED','boot_id':BOOT,'old_gui':str(OLD_GUI),'old_gui_pid':1295,'old_camera_pid':1332,'old_camera_birth':birth(1332),'gui_components':len(cfg['component_sha256']),'units':unit_pins(),'checkpoint_path':native['checkpoint_output'],'native_unit_sha256':h['dpu_schedule']['protection_handoff']['native_unit_sha256'],'old_vart':Path('/etc/vart.conf').read_text(),'before_health':h,'source_config_sha256':CAMERA_CONFIG_SHA,'fdt_sha256':FDT_SHA,'wide_manifest_sha256':sha(B/'candidate-manifest.json'),'wide_app':APP,'motor_commands':0}
 atomic(R/'state.json',s)
 atomic(R/'context.json',{'boot_id':BOOT,'fdt_sha256':FDT_SHA,'firmware_name':APP+'.bit.bin'})
 return {'phase':s['phase'],'camera_pid':1332,'gui_pid':1295,'gui_components_verified':s['gui_components'],'new_files_verified':True,'motion_commands':0}
def stop():
 s=json.loads((R/'state.json').read_text());fixed(s);assert s['phase']=='PREPARED'
 power=json.loads((R/'motor-power-off.json').read_text());assert power['boot_id']==BOOT and power['user_reported_power_off'] is True
 h=get(8790,'/health');u=get(8783,'/api/state');assert h['pid']==s['old_camera_pid'] and birth(h['pid'])==s['old_camera_birth']
 assert u['phase']=='IDLE' and not u['playing'] and not u['manual_pan']['automatic_following'] and not u['handsfree_dialogue']['enabled']
 c=props(CAM);assert c['Restart']=='no' and c['KillMode']=='process' and c['SendSIGKILL']=='no' and c['TimeoutStopUSec']=='infinity'
 s['before_health']=h;s['phase']='STOPPING';atomic(R/'state.json',s)
 for unit in [GUI,CAM]:
  run(['systemctl','stop','--no-block',unit]);until=time.monotonic()+60
  while props(unit)['MainPID']!='0' and time.monotonic()<until:time.sleep(.25)
  p=props(unit);assert p['MainPID']=='0' and p['Result']=='success' and p['ExecMainStatus']=='0','Normal service stop not confirmed'
 cp=Path(s['checkpoint_path']);doc=json.loads(cp.read_text());free=False
 with Path('/run/aura-person-dpu.lock').open('a+') as f:
  try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);free=True
  except BlockingIOError:pass
 validate_checkpoint(doc,h,BOOT,s['old_camera_pid'],s['old_camera_birth'],props(CAM),(Path('/proc')/str(s['old_camera_pid'])).exists(),free)
 assert doc['source_unit_sha256']==s['native_unit_sha256']
 assert Path('/sys/module/zocl/refcnt').read_text().strip()=='0'
 atomic(R/'stopped-checkpoint.json',doc);s.update(phase='STOPPED_CHECKPOINT_VERIFIED',checkpoint_sha256=sha(cp));atomic(R/'state.json',s)
 return {'phase':s['phase'],'checkpoint_sha256':s['checkpoint_sha256'],'old_native_counts_preserved':True,'gui_and_camera_stopped':True}
def switch():
 s=json.loads((R/'state.json').read_text());fixed(s);assert s['phase']=='STOPPED_CHECKPOINT_VERIFIED'
 assert props(CAM)['MainPID']==props(GUI)['MainPID']=='0' and sha(s['checkpoint_path'])==s['checkpoint_sha256']
 assert json.loads((R/'motor-power-off.json').read_text())['user_reported_power_off'] is True
 manifest=json.loads((B/'candidate-manifest.json').read_text());assert all(sha(p)==h for p,h in manifest['runtime_files'].items())
 with Path('/run/aura-person-dpu.lock').open('a+') as dpu,Path('/run/aura-vsrv.lock').open('a+') as motor:
  fcntl.flock(dpu,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(motor,fcntl.LOCK_EX|fcntl.LOCK_NB)
  assert Path('/sys/module/zocl/refcnt').read_text().strip()=='0' and active()==['kv260-benchmark-b4096']
  run(['xmutil','unloadapp'],45);assert active()==[]
  run(['xmutil','loadapp',APP],60);assert active()==[APP]
  assert Path('/sys/class/fpga_manager/fpga0/state').read_text().strip()=='operating'
  assert Path('/proc/device-tree/fpga-full/firmware-name').read_bytes().rstrip(b'\0').decode()==APP+'.bit.bin'
  assert Path('/etc/vart.conf').read_text()=='firmware: /lib/firmware/xilinx/'+APP+'/'+APP+'.xclbin\n'
 assert sha(B/'bench_identity_stop.py')==manifest['bench_sha256']
 run(['/usr/bin/python3','-B',str(B/'bench_identity_stop.py'),'--execute','--confirmation','ID_STOP_ONLY','--manifest',str(B/'candidate-manifest.json'),'--manifest-sha256',s['wide_manifest_sha256'],'--context',str(R/'context.json'),'--output',str(R/'id-stop.json')],20)
 proof=json.loads((R/'id-stop.json').read_text());assert proof['identity_stop_passed']
 proof.update(build_id=0x10282601,fdt_sha256=FDT_SHA);atomic(R/'wide-platform-proof.json',proof)
 s.update(phase='WIDE_LOADED_ID_STOP_PASS',after_stop=proof['after_stop']);atomic(R/'state.json',s)
 return {'phase':s['phase'],'after_stop':s['after_stop'],'ARM_sent':False,'COMMIT_sent':False,'new_range_us':[500,2500]}
def start_camera():
 s=json.loads((R/'state.json').read_text());fixed(s);assert s['phase'] in ('WIDE_LOADED_ID_STOP_PASS','WIDE_IDLE_WATCH_PASS')
 assert sha(s['checkpoint_path'])==s['checkpoint_sha256'] and props(CAM)['MainPID']=='0'
 run(['systemctl','reset-failed',CAM]);run(['systemctl','start','--no-block',CAM]);until=time.monotonic()+70;h=None
 while time.monotonic()<until:
  try:
   value=get(8790,'/health')
   if value['pid']==int(props(CAM)['MainPID']) and value['detected_frames']>=5 and value['identity']['ready'] and not value['dpu_schedule']['owner_fenced']:h=value;break
  except Exception:pass
  time.sleep(.5)
 assert h is not None,'Camera startup not confirmed; retain owner, do not force replace'
 old=s['before_health'];sched=h['dpu_schedule'];before=old['dpu_schedule']
 assert sched['primary_calls']>=before['primary_calls'] and sched['primary_period_overruns']>=before['primary_period_overruns']
 for n in ['yunet','sface']:
  assert sched['optional'][n]['calls']>=before['optional'][n]['calls'] and sched['optional'][n]['overruns']>=before['optional'][n]['overruns']
 assert h['identity']['feature_inference']['completed']>=old['identity']['feature_inference']['completed']
 s.update(phase='WIDE_CAMERA_RUNNING_GUI_HELD',camera_pid=h['pid']);atomic(R/'state.json',s)
 return {'phase':s['phase'],'camera_pid':h['pid'],'detection_hz':h['detection_hz'],'identity_ready':True,'native_counts_preserved':True,'gui_not_started_yet':True}
def watch():
 s=json.loads((R/'state.json').read_text());fixed(s);assert s['phase']=='WIDE_LOADED_ID_STOP_PASS'
 assert props(CAM)['MainPID']==props(GUI)['MainPID']=='0'
 sys.path.insert(0,str(B/'driver'));sys.path.insert(0,'/home/root/aura-pan-wide-20261028/control-10282601')
 from batch_transport import BatchRegisters
 from batch_driver import BatchDriver
 manifest=json.loads((B/'candidate-manifest.json').read_text());samples=[];started=time.monotonic()
 def leds():
  out={}
  for p in Path('/sys/class/leds').glob('*'):
   out[p.name]={n:(p/n).read_text().strip() for n in ['brightness','trigger'] if (p/n).exists()}
  return out
 with BatchRegisters(B/'driver/libvsrv.so',manifest['payload_files']['libvsrv.so'],BOOT,manifest['runtime_files']) as io:
  d=BatchDriver(io,0x10282601,BOOT)
  while time.monotonic()-started<90:
   assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
   rb=d.status();assert rb['flags']==0 and rb['lease_left_ms']==0
   sample={'elapsed_s':round(time.monotonic()-started,3),'uptime_s':float(Path('/proc/uptime').read_text().split()[0]),'readback':rb,'leds':leds()}
   samples.append(sample);atomic(R/'wide-idle-watch.json',{'status':'RUNNING','boot_id':BOOT,'samples':samples,'ARM_sent':False,'COMMIT_sent':False})
   time.sleep(5)
 s['phase']='WIDE_IDLE_WATCH_PASS';atomic(R/'state.json',s)
 result={'phase':s['phase'],'boot_id':BOOT,'elapsed_s':time.monotonic()-started,'samples':len(samples),'readback':samples[-1]['readback'],'leds':samples[-1]['leds'],'ARM_sent':False,'COMMIT_sent':False}
 atomic(R/'wide-idle-watch-result.json',result);return result

def main():
 assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
 lock=(OPS/'operation.lock').open('a+');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 phase=sys.argv[1] if len(sys.argv)>1 else 'prepare'
 functions={'prepare':prepare,'stop':stop,'switch':switch,'start-camera':start_camera,'watch':watch}
 assert phase in functions
 print(json.dumps(functions[phase]()))
if __name__=='__main__':main()
