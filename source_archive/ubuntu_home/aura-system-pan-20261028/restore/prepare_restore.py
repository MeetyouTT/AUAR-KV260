"""Fresh context and existing immutable payload checks for this boot's restore."""
import hashlib,json,subprocess,urllib.request
from pathlib import Path
BOOT='5f167a36-a715-4bbb-9186-4dff2bff8ee3';ROOT=Path('/home/root/aura-system-pan-20261028/restore-5f167a36');OLD=Path('/home/root/aura-pan-vsrv2-20261024/778d2512-1236ccf4-r2');OPS=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def get(port,path):
 o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
 with o.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as r:return json.load(r)
def props(n):
 x=subprocess.check_output(['systemctl','show',n,'-p','MainPID','-p','ActiveState','-p','FragmentPath','-p','DropInPaths','-p','KillMode','-p','SendSIGKILL','-p','TimeoutStopUSec'],text=True)
 return dict(a.split('=',1) for a in x.splitlines() if '=' in a)
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT and not ROOT.exists()
assert Path('/sys/block/mmcblk1/device/cid').read_text().strip()=='0353445345333247805558c00401a100'
gui_startup=Path('/home/root/aura-windows-portrait-20261027/handoff-31b0c262c5b74d52966c00b978dfef3f/startup/config.json')
assert sha(gui_startup)=='3d84681a728617eea1cb28b619a376f9b3798a41c04d8fb57759947a3479294f'
gui_pins=json.loads(gui_startup.read_text())['component_sha256']
assert all(sha(gui_startup.parent.parent/'runtime/aura'/p)==h for p,h in gui_pins.items())
manifest=OLD/'candidate-manifest.json';assert sha(manifest)=='ed175a70735b4c445d6f86cbcd2909cdd1add349ba52f852f367a7602d30f9ab'
m=json.loads(manifest.read_text());assert all(sha(p)==h for p,h in m['runtime_files'].items())
assert all(sha(OLD/'driver'/n)==h for n,h in m['payload_files'].items())
baseline=json.loads((OLD/'payload.json').read_text())['baseline'];fdt=sha('/sys/firmware/fdt');assert fdt=='22516e08c2c862dfe3ee999a962ff62ed7830ad8e1183e36432cd22acde77762','FDT differs from fresh merged proof'
meta=json.loads((OPS/'meta.json').read_text());assert all(sha(OPS/n)==h for n,h in meta['source_pins'].items())
cfg=json.loads(Path(meta['candidate_config']).read_text());h=get(8790,'/health');u=get(8783,'/api/state');c=props('aura-camera-ui.service');g=props('aura-avatar-ui.service')
assert c['MainPID']==str(h['pid'])=='1334' and c['ActiveState']=='active' and g['MainPID']=='1297' and g['ActiveState']=='active'
assert h['dpu_schedule']['native_critical'] and not h['dpu_schedule']['owner_fenced'] and h['identity']['face_targets']['worker_alive']
assert u['phase']=='IDLE' and not u.get('playing') and u.get('audio_output_state')=='IDLE_READY' and not u.get('local_transcription',{}).get('service',{}).get('pending')
assert u.get('local_recording',{}).get('state')!='RECORDING' and not u.get('manual_pan',{}).get('automatic_following')
units={}
for n,p in [('aura-camera-ui.service',c),('aura-avatar-ui.service',g)]:
 units[n]={f:sha(f) for f in [p['FragmentPath']]+p['DropInPaths'].split() if f}
ROOT.mkdir(parents=True,mode=0o700)
context={'boot_id':BOOT,'fdt_sha256':fdt,'firmware_name':'aura-visual-servo-b4096-v2.bit.bin'}
(ROOT/'context.json').write_text(json.dumps(context,indent=2)+'\n')
s={'phase':'PREPARED','boot':BOOT,'checkpoint':cfg['native_execution']['checkpoint_output'],'camera_pid':h['pid'],'gui_pid':int(g['MainPID']),
 'old_root':str(OLD),'ops_root':str(OPS),'units':units,'database_path':baseline['database_path'],'database_sha256':sha(baseline['database_path']),
 'fdt_sha256':fdt,'vart_before':Path('/etc/vart.conf').read_text(),'unattended_no_motion':True,'previous_boot_history_gap':{'archive_primary_overruns':27,'last_verified_primary_overruns':29,'archive_source_pid':673020,'last_verified_source_pid':720342,'unknown_tail':True},'physical_position_known':False}
(ROOT/'state.json').write_text(json.dumps(s,indent=2)+'\n')
print(json.dumps({'phase':s['phase'],'existing_runtime_hashes_passed':True,'fresh_fdt_overlay_merge_passed':True,'camera_pid':h['pid'],'gui_pid':int(g['MainPID']),'sface_recovery_preserved':h['dpu_schedule']['optional']['sface']['recovery']['phase'],'ARM_sent':False}))
