"""Project code/config metadata only; never read the face database or frames."""
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[3]
sys.path.insert(0, str(PROJECT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh

SCRIPT = r'''
import hashlib,json,subprocess
from pathlib import Path
ops=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735')
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
pid=int(subprocess.check_output(['systemctl','show','aura-camera-ui.service','-p','MainPID','--value'],text=True))
files={'meta':ops/'meta.json','native_entry':ops/'native_entry.py',
       'native_entry_operator':ops/'pan-face-edge-v5/native-operator-v1/native_entry_operator.py',
       'old_config':ops/'native-run-605eaf50-c66a-4559-bfc9-5ae177e0f305-1333/config.json',
       'current_config':ops/('native-run-'+boot+'-'+str(pid))/'config.json'}
for name in ('deployment-manifest.json','face_flow.py','face_timing.py','stage_timing.py','face_lock.py',
             'raw_capture.py','face_observation.py','direct_yunet_input.py'):
    files['r17_'+name]=ops/'pan-face-edge-v5/face-source-v17'/name
files['face_source']=ops/'pan-face-edge-v5/face_source.py'
files['native_entry_pan_face_v5']=ops/'native_entry_pan_face_v5.py'
files['identity_recovery']=ops/'pan-face-edge-v5/native-operator-v1/identity_recovery.py'
files['camera_wrapper']=ops/'pan-face-edge-v5/camera_wrapper.py'
meta=json.loads((ops/'meta.json').read_text())
for name in ('board/identity/face_targets.py','board/identity/camera_faces.py','board/vision/ui_camera_service.py','board/vision/dpu_yunet.py',
             'board/vision/native_startup.py','board/vision/native_binding.py','board/vision/native_runtime.py'):
    files['actual_'+name]=Path(meta['candidate_root'])/'aura'/name
out={'boot':boot,'pid':pid,'files':{},'read_only':True,'database_opened':False}
for key,p in files.items():
    data=p.read_bytes();assert len(data)<512*1024
    out['files'][key]={'path':str(p),'sha256':hashlib.sha256(data).hexdigest(),'content':data.decode()}
current=json.loads(out['files']['current_config']['content'])
native=current.get('native_execution',{});out['native_execution_keys']=sorted(native)
seed=native.get('seed') or {};out['seed_metadata']=seed
allowed=('schema_version','schema','scope','boot_id','source_pid','source_birth_ticks','source_unit_sha256',
         'source_manifest_sha256','firmware_sha256','fdt_sha256','vart_sha256')
for key,value in [('checkpoint_output',native.get('checkpoint_output')),('seed_path',seed.get('path'))]:
    if not isinstance(value,str):continue
    p=Path(value)
    if not p.is_file():out[key]={'path':value,'exists':False};continue
    data=p.read_bytes();record={'path':value,'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)}
    try:
        obj=json.loads(data);record['keys']=sorted(obj)
        record['metadata']={k:obj[k] for k in allowed if k in obj and not isinstance(obj[k],(dict,list))}
        for sub in ('seed','auxiliary'):
            if isinstance(obj.get(sub),dict):
                record[sub+'_keys']=sorted(obj[sub])
                record[sub+'_metadata']={k:obj[sub][k] for k in allowed if k in obj[sub] and not isinstance(obj[sub][k],(dict,list))}
    except (ValueError,UnicodeDecodeError):record['json']=False
    out[key]=record
p=Path('/sys/firmware/fdt');out['fdt_sha256']=hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
out['firmware_names']={}
for p in Path('/sys/class/fpga_manager').glob('*/firmware'):
    try:out['firmware_names'][str(p)]=p.read_text().strip().strip(chr(0))
    except OSError:out['firmware_names'][str(p)]='NOT_READABLE_SYSFS_ATTRIBUTE'
for key,p in [('operator_settings',ops/'pan-face-edge-v5/native-operator-v1/settings.json'),
              ('operator_manifest',ops/'pan-face-edge-v5/native-operator-v1/runtime-manifest.json')]:
    if not p.is_file():out[key]={'path':str(p),'exists':False};continue
    data=p.read_bytes();assert len(data)<512*1024
    out['files'][key]={'path':str(p),'sha256':hashlib.sha256(data).hexdigest(),'content':data.decode()}
extra_keys=('abi','purpose','checkpoint_kind','fenced','captured','primary','active','primary_waiting','pending_result_tokens')
if isinstance(native.get('checkpoint_output'),str):
    checkpoint=json.loads(Path(native['checkpoint_output']).read_bytes())
    for sub in ('seed','auxiliary'):
        if not isinstance(checkpoint.get(sub),dict):continue
        out['checkpoint_output'][sub+'_control_metadata']={k:v for k,v in checkpoint[sub].items()
            if k in extra_keys and isinstance(v,(str,int,float,bool,type(None)))}
        for k in extra_keys:
            v=checkpoint[sub].get(k)
            if isinstance(v,dict):out['checkpoint_output'][sub+'_'+k+'_scalars']={n:w for n,w in v.items() if isinstance(w,(int,float,bool,type(None)))}
marker_root=native.get('new_boot_marker_directory')
if isinstance(marker_root,str):
    marker=Path(marker_root)/('kernel-boot-'+boot+'.consumed')
    record={'path':str(marker),'exists':marker.is_file()}
    if marker.is_file():
        data=marker.read_bytes();record['sha256']=hashlib.sha256(data).hexdigest();obj=json.loads(data)
        record['metadata']={k:v for k,v in obj.items() if isinstance(v,(str,int,float,bool,type(None)))}
        record['metadata_complete']=len(record['metadata'])==len(obj)
        for key,value in record['metadata'].items():
            if 'archive' in key and isinstance(value,str) and Path(value).is_file():
                data=Path(value).read_bytes();rec={'path':value,'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)}
                try:
                    archived=json.loads(data);rec['metadata']={k:v for k,v in archived.items() if k in allowed and not isinstance(v,(list,dict))}
                    rec['seed_metadata']={k:v for k,v in archived.get('seed',{}).items() if k in allowed and not isinstance(v,(list,dict))}
                except (ValueError,UnicodeDecodeError):pass
                record['archive']=rec
    out['boot_marker']=record
recovery=ops/'pan-face-edge-v5/native-operator-v1/identity_recovery.py'
out['identity_recovery_sha256']=hashlib.sha256(recovery.read_bytes()).hexdigest()
print(json.dumps(out))
'''


def main():
    value = json.loads(ssh('python3 -B -', SCRIPT, timeout=18))
    (HERE/'actual_metadata_snapshot_v4.json').write_text(json.dumps(value, indent=2), encoding='utf-8')
    print(json.dumps(dict(status='METADATA_SAVED', boot=value['boot'], pid=value['pid'],
        files={k:v['sha256'] for k,v in value['files'].items()}, seed_metadata=value['seed_metadata'],
        checkpoint_keys=value.get('checkpoint_output',{}).get('keys')), ensure_ascii=True))


if __name__ == '__main__':
    main()
