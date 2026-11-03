"""Final read-only current owner, source pins, framebuffer and stopped output."""
import hashlib,json,os,subprocess,time,urllib.request
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/463c9307');N=R/'gui-face-edge-v5';A=N/'runtime/aura'
OPS=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735');op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(port,path):
 with op.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as r:return json.load(r)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
h=get(8790,'/health');s=h['dpu_schedule'];u=get(8783,'/api/state');m=u['manual_pan'];cfg=json.loads((N/'startup/config.json').read_text())
pins={name:sha(A/name)==digest for name,digest in cfg['component_sha256'].items()}
face=json.loads((A/'config/pan_face.local.json').read_text());root=Path(face['release_root']);manifest=root/'deployment-manifest.json'
assert sha(manifest)==face['manifest_sha256'];consumer=json.loads(manifest.read_text());assert all(sha(x['destination'])==x['sha256'] for x in consumer['files'])
assert m['state']=='READY' and not m['automatic_following'] and m['readback']['flags']==0 and m['readback']['lease_left_ms']==0
assert m['minimum_us']==1425 and m['maximum_us']==1505 and h['identity']['ready'] and not s['owner_fenced'] and all(pins.values())
unit=lambda name:subprocess.check_output(['systemctl','show',name,'-p','MainPID','-p','ActiveState'],text=True).strip()
logs=(N/'runtime/stage.log').read_text();editor_log=subprocess.run(['journalctl','-u','aura-face-zone-editor.service','-n','15','--no-pager','-o','cat'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True).stdout
report={'status':'FINAL_FACE_FOLLOW_READY_OUTPUT_STOPPED','boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
 'camera_pid':h['pid'],'camera_hz':h['detection_hz'],'camera_unit':unit('aura-camera-ui.service'),'gui_unit':unit('aura-avatar-ui.service'),
 'editor_unit':unit('aura-face-zone-editor.service'),'identity_ready':h['identity']['ready'],'identity_error':h['identity']['error'],
 'primary_overruns':s['primary_period_overruns'],'optional':{k:{n:s['optional'][k].get(n) for n in ('calls','native_completed','overruns','disabled','recovery')} for k in ('yunet','sface')},
 'pins_verified':sum(pins.values()),'pins_total':len(pins),'consumer_root':str(root),'consumer_manifest_sha256':face['manifest_sha256'],
 'gui_proxy_sha256':sha(A/'tools/face_pan_controls.py'),'manual':m,'native_canvas':u.get('native_canvas'),
 'preview':u['ui_runtime'].get('preview_metrics'),'page':u['ui_page'],'zone':json.loads((R/'face-zone-settings.json').read_text()),
 'render_errors':[x for x in logs.splitlines() if any(t in x for t in ('STAGE ERROR','Traceback','CRITICAL'))],
 'editor_errors':[x for x in editor_log.splitlines() if any(t in x for t in ('Traceback','Error:','CRITICAL'))],
 'mechanical_zero_calibrated':False,'external_waveform_verified':False,'new_human_physical_acceptance':False,'register_writes':0}
p=R/'current-face-follow-status.json';tmp=p.with_name(p.name+'.audit');tmp.write_text(json.dumps(report,indent=2)+'\n');os.replace(tmp,p)
print(json.dumps(report,sort_keys=True))
