import hashlib,json,os,re,subprocess,urllib.request
from pathlib import Path

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def get(port,path):
 try:
  with urllib.request.urlopen('http://127.0.0.1:'+str(port)+path,timeout=5) as r:return json.load(r)
 except Exception as e:return {'read_error':str(e)}
def props(unit):
 p=subprocess.run(['systemctl','show',unit,'-p','Id','-p','MainPID','-p','ActiveState','-p','SubState','-p','ExecStart','-p','UnitFileState'],capture_output=True,text=True,timeout=15)
 return dict(x.split('=',1) for x in p.stdout.splitlines() if '=' in x)
def doc(p):
 try:return {'path':str(p),'sha256':sha(p),'document':json.loads(Path(p).read_text())}
 except Exception as e:return {'path':str(p),'read_error':str(e)}
u=get(8783,'/api/state');h=get(8790,'/health')
units={n:props(n) for n in ['aura-avatar-ui.service','aura-camera-ui.service','aura-face-zone-editor.service']}
pid=units['aura-avatar-ui.service'].get('MainPID','0');args=(Path('/proc')/pid/'cmdline').read_bytes().decode().split('\0') if pid!='0' else []
result={'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'uptime':Path('/proc/uptime').read_text().split()[0],
 'firmware':Path('/proc/device-tree/fpga-full/firmware-name').read_bytes().rstrip(b'\0').decode(),
 'fdt_sha256':sha('/sys/firmware/fdt'),'kernel':os.uname().release,'units':units,'actual_launcher_args':args,
 'ui':{k:u.get(k) for k in ['phase','playing','paused','ui_page','audio_output_state','local_recording','local_transcription'] if k not in ['local_recording','local_transcription']},
 'manual_pan':u.get('manual_pan'), 'listening_enabled':u.get('handsfree_dialogue',{}).get('enabled'),
 'microphone_open':u.get('handsfree_dialogue',{}).get('microphone_open'),
 'camera':{k:h.get(k) for k in ['pid','capture_hz','detection_hz','capture_frames','detected_frames','camera_error','detector_error','camera_epoch','mirror_horizontal']},
 'dpu':{k:h.get('dpu_schedule',{}).get(k) for k in ['owner_fenced','protection_handoff','primary_period_overruns']},
 'read_errors':{k:v.get('read_error') for k,v in [('ui',u),('camera',h)] if v.get('read_error')}}
if '--config' in args:
 c=Path(args[args.index('--config')+1]);starter=doc(c);result['actual_startup']=starter
 cfg=starter.get('document',{});root=Path(cfg.get('runtime','/nonexistent'))/'aura';result['runtime']=str(root)
 result['actual_startup']={'path':str(c),'sha256':starter.get('sha256'),'runtime':cfg.get('runtime'),'component_count':len(cfg.get('component_sha256',{}))}
 result['motion_configs']={n:doc(root/'config'/n) for n in ['pan_manual.local.json','pan_face.local.json','pan_direction.current.json']}
 m=result['motion_configs']['pan_manual.local.json'].get('document',{})
 result['manual_release']=doc(m.get('release_manifest','/nonexistent'))
 f=result['motion_configs']['pan_face.local.json'].get('document',{})
 result['follow_context']=doc(f.get('arguments',{}).get('context','/nonexistent'))
 result['zone_settings']=doc(f.get('arguments',{}).get('zone-settings','/nonexistent'))
print(json.dumps(result,ensure_ascii=False))
