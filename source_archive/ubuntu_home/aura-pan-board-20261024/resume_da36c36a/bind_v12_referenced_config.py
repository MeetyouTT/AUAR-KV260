import fcntl,hashlib,json,os,re,subprocess,urllib.request
from pathlib import Path
O=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735');R=Path('/home/root/aura-pan-current-20261024/da36c36a')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
raw=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','ExecStart','--value'],text=True)
sc=Path(re.search(r'--config (/[^ ;]+)',raw).group(1));active=json.loads(sc.read_text());app=Path(active['runtime'])/'aura'
manual=json.loads((app/'config/pan_manual.local.json').read_text());q=Path(manual['face_follow_config']);refsc=q.parents[3]/'startup/config.json'
assert q==R/'gui-reference-bound-v2/runtime/aura/config/pan_face.local.json'
ref=json.loads(refsc.read_text());refapp=Path(ref['runtime'])/'aura'
assert all(sha(app/n)==v for n,v in active['component_sha256'].items())
assert all(sha(refapp/n)==v for n,v in ref['component_sha256'].items())
old=q.read_bytes();oldsc=refsc.read_bytes();cfg=json.loads(old)
assert cfg['release_root'].endswith('/continuous-v11r1') and cfg['manifest_sha256']=='524ad777aec14dc2d853708412bcef4f75e1e6937d528674cc154b361b8ce76d'
new=json.loads((app/'config/pan_face.local.json').read_text())
assert new['release_root'].endswith('/continuous-v12r1') and new['duration_s']==60 and new['manifest_sha256']=='b307e8b19d2fd157286ce96e6b3eb867b01cb7002bbdda1050bb0f60e1b22923'
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with op.open('http://127.0.0.1:8783/api/state',timeout=3) as f:u=json.load(f)
m=u['manual_pan'];assert m['state']=='READY' and not m['automatic_following'] and m['readback']['flags']==0 and m['readback']['lease_left_ms']==0
def atomic(p,v):
 t=p.with_name(p.name+'.v12-ref-'+str(os.getpid()));t.write_text(json.dumps(v,indent=2)+'\n');os.replace(t,p)
with (O/'operation.lock').open('a+') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 assert q.read_bytes()==old and refsc.read_bytes()==oldsc
 backup=R/'v12-reference-path-backup';backup.mkdir(exist_ok=False)
 (backup/'pan_face.local.json').write_bytes(old);(backup/'startup.json').write_bytes(oldsc)
 atomic(q,new);ref['component_sha256']['config/pan_face.local.json']=sha(q);atomic(refsc,ref)
 assert all(sha(refapp/n)==v for n,v in ref['component_sha256'].items())
 assert all(sha(app/n)==v for n,v in active['component_sha256'].items())
print(json.dumps(dict(status='V12_ACTUAL_CACHED_GUI_REFERENCE_BOUND',referenced_config=str(q),release_root=new['release_root'],manifest_sha256=new['manifest_sha256'],duration_s=new['duration_s'],readback=m['readback'],gui_restart=False,motor_commands_sent=0),ensure_ascii=False))
