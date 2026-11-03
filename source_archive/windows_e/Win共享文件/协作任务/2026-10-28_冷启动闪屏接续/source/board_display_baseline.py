import hashlib,json,os,subprocess,urllib.request
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='230ae5f0-997b-432b-a738-0065c0cb5238'
def run(a):
 p=subprocess.run(a,env=dict(os.environ,DISPLAY=':0'),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=6)
 return {'rc':p.returncode,'text':p.stdout}
def get(port,path):
 try:
  with urllib.request.urlopen('http://127.0.0.1:'+str(port)+path,timeout=3) as r:return json.load(r)
 except Exception as e:return {'error':type(e).__name__}
u=get(8783,'/api/state');h=get(8790,'/health')
fields=['boot_id','pid','frame_id','fps','capture_fps','detection_fps','ready','status','last_error']
d={'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'health':{k:h.get(k) for k in fields},'health_keys':list(h),'ui_keys':list(u)}
d['ui_sections']={k:list(v) for k,v in u.items() if isinstance(v,dict)}
d['ui_activity']={k:u.get(k) for k in ['phase','audio_output_state','playing','local_recording']}
d['camera_unit']=run(['systemctl','show','aura-camera-ui.service','-p','MainPID','-p','ActiveState','-p','ExecStart','-p','NRestarts'])
e=run(['systemctl','show','aura-avatar-ui.service','-p','ExecStart','--value'])['text'];cfg=e.split('--config ',1)[1].split(' ;',1)[0].strip();p=Path(cfg);c=json.loads(p.read_text())
d['ui_config_path']=cfg;d['ui_config_sha256']=hashlib.sha256(p.read_bytes()).hexdigest();d['ui_display_config']={k:v for k,v in c.items() if any(s in k for s in ['display','mode','output','retrain','state_file','lock_file'])}
d['launcher_sha256']=hashlib.sha256((p.parent/'launcher.py').read_bytes()).hexdigest();d['launcher_source']=(p.parent/'launcher.py').read_text()
d['aux_nodes']=[str(p) for p in Path('/dev').glob('drm_dp_aux*')];d['aux_sysfs']=[str(p) for p in Path('/sys/class/drm_dp_aux_dev').glob('*')]
d['wake']=run(['xset','dpms','force','on'])
d['xset_after']=run(['xset','q']);d['display_state']=Path('/sys/kernel/debug/dri/0/state').read_text()
d['scan_clock']=[s for s in Path('/sys/kernel/debug/clk/clk_summary').read_text().splitlines() if 'dp_video_ref' in s]
d['connector']={k:(Path('/sys/class/drm/card0-DP-1')/k).read_text().strip() for k in ['status','enabled','dpms']}
print(json.dumps(d))
