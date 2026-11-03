"""Read the original GUI's cached stopped position; no actuator commands."""
import hashlib,http.client,json
from pathlib import Path
B=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13');A=B/'runtime/aura'
BOOT='a6d4a069-e9b0-4065-8df7-dc23556b168e';STARTUP='c1154308fcd25a9c8d957f33c5e2a4db0a0ef73e7656eb5aa437e29af9cd123b'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def get(port,path):
    c=http.client.HTTPConnection('127.0.0.1',port,timeout=3)
    try:
        c.request('GET',path);r=c.getresponse();data=r.read(2097153);assert r.status==200 and len(data)<=2097152
        return json.loads(data)
    finally:c.close()
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
assert sha(B/'startup/config.json')==STARTUP
startup=json.loads((B/'startup/config.json').read_bytes());pins=startup['component_sha256'];assert len(pins)==380
assert all(sha(A/name)==value for name,value in pins.items())
owners={}
for name,pid,birth,cmd in [('GUI',363452,'2933733','48a28efa32b2050901e73e85a80a30a90dcfbce0b7249bde5d6d90902740631d'),('GTK',363456,'2933846','b5b35a22c021086df5a2782bbdd4932ba1f18f14c6374717d7ed120a1befda32'),('camera',362659,'2850120','acf3ee123d7674fdea6e90e79252909ca396249c870269169910879d940c27dd')]:
    p=Path('/proc')/str(pid);assert (p/'stat').read_text().rsplit(')',1)[1].split()[19]==birth and sha(p/'cmdline')==cmd
    owners[name]={'pid':pid,'birth_ticks':birth,'command_sha256':cmd}
face=json.loads((A/'config/pan_face.local.json').read_bytes());root=Path(face['release_root']);manifest=root/'deployment-manifest.json'
assert sha(manifest)==face['manifest_sha256']=='9cd35b967bf9c859ed3f1f4de4dc5dad199e81ddfed845435fc8745a41be0ba9'
files=json.loads(manifest.read_bytes())['files'];assert len(files)==25 and all(sha(f['destination'])==f['sha256'] for f in files)
context=json.loads(Path(face['arguments']['context']).read_bytes());assert context['boot_id']==BOOT and context['fdt_sha256']==sha('/sys/firmware/fdt')
assert Path('/proc/device-tree/fpga-full/firmware-name').read_bytes().rstrip(b'\0').decode()==context['firmware_name']=='aura-visual-servo-b4096-wide-v1.bit.bin'
assert Path('/sys/class/fpga_manager/fpga0/state').read_text().strip()=='operating'
assert Path('/etc/vart.conf').read_text()=='firmware: /lib/firmware/xilinx/aura-visual-servo-b4096-wide-v1/aura-visual-servo-b4096-wide-v1.xclbin\n'
state=get(8783,'/api/state');pan=state.get('manual_pan') or {};rb=pan.get('readback')
backend_pid=pan.get('backend_pid');backend_path=Path('/proc')/str(backend_pid)
if type(backend_pid) is int:
    try:
        parts=(backend_path/'stat').read_text().rsplit(')',1)[1].split()
        owners['manual']={'pid':backend_pid,'birth_ticks':parts[19],'parent_pid':int(parts[1]),'command_sha256':sha(backend_path/'cmdline'),'alive':True}
    except (FileNotFoundError,ProcessLookupError):owners['manual']={'pid':backend_pid,'alive':False}
health=get(8790,'/health');assert health['pid']==362659 and health['board_boot_id']==BOOT
projection={k:pan.get(k) for k in ['state','automatic_following','pulse_us','target_us','readback','backend_pid','error']}
ready=(pan.get('state')=='READY' and pan.get('automatic_following') is False and isinstance(rb,dict) and rb.get('flags')==0 and rb.get('lease_left_ms')==0 and (owners.get('manual') or {}).get('alive') is True)
print(json.dumps({'status':'CURRENT_POSITION_STOPPED_READY_FOR_MAIN_START_GATE' if ready else 'CURRENT_POSITION_NOT_READY','boot_id':BOOT,'startup_sha256':STARTUP,'owners':owners,'all380_and_control25_verified':True,'platform_context':context,'manual_pan':projection,'runtime_fault_count':(state.get('runtime_faults') or {}).get('count'),'camera':{k:health.get(k) for k in ['pid','board_boot_id','camera_epoch','service_epoch','capture_frames','detected_frames','camera_error','detector_error','preview_error']},'initialization_submitted':False,'standalone_REFERENCE_sent':False,'MMIO_opened_by_this_observer':False,'axis_commands_sent':0,'follow_started':False,'ready_for_main_START_GATE':ready,'position_is_command_readback_not_measured_mechanical_zero':True}))
