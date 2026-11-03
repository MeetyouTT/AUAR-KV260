import base64,gzip,hashlib,json,os,subprocess,urllib.request
from pathlib import Path
def get(url):
    with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(url,timeout=3) as r:return json.load(r)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
pid=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True).strip()
args=Path('/proc/'+pid+'/cmdline').read_bytes().decode().split('\0')
cfg=Path(args[args.index('--config')+1]);c=json.loads(cfg.read_text());root=Path(c['runtime'])
if root.name!='aura':root=root/'aura'
out={'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'root':str(root),'config_path':str(cfg),'config_sha256':sha(cfg),'source':{},'processes':[]}
names=['tools/board_avatar_gtk.py','tools/board_avatar_pan.py','tools/gstreamer_audio_worker.py','tools/gstreamer_audio_engine.py','tools/persistent_audio.py','tools/realtime_audio.py','tools/realtime_controller.py']
for name in names:
    p=root/name
    if p.exists():out['source'][name]={'sha256':sha(p),'gzbase64':base64.b64encode(gzip.compress(p.read_bytes())).decode()}
for p in Path('/proc').iterdir():
    if not p.name.isdigit():continue
    try:
        a=(p/'cmdline').read_bytes().decode(errors='replace').split('\0')
        if not any(Path(x).name in ('board_avatar_gtk.py','board_avatar_pan.py','gstreamer_audio_worker.py') for x in a if x):continue
        fds=[]
        for f in (p/'fd').iterdir():
            try:t=os.readlink(str(f))
            except OSError:continue
            if t.startswith('/dev/snd/'):fds.append(t)
        out['processes'].append({'pid':int(p.name),'args':a,'alsa_fds':sorted(set(fds))})
    except OSError:continue
try:
    s=get('http://127.0.0.1:8783/api/state');out['state_keys']=list(s)
    out['state']={k:s.get(k) for k in ('phase','playing','paused','audio','audio_state','audio_backend','persistent_audio','handsfree','auto_turns','voice_barge_in') if k in s}
    for k in ('recording','realtime','audio_frontend'):
        v=s.get(k,{})
        if isinstance(v,dict):out['state'][k]={n:x for n,x in v.items() if isinstance(x,(int,float,bool)) or n in ('state','backend','status','device_state','error')}
except Exception as e:out['state_error']=type(e).__name__+': '+str(e)
print(json.dumps(out))
