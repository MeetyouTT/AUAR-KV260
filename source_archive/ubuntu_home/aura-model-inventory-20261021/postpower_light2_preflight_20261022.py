import base64,gzip,hashlib,json,subprocess,tarfile,urllib.request
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='7924ac9f-311d-4fcd-98be-57bf023cf1aa'
sha='9b7373edd1316069a45728f62f82c600927ef5853f75d24cea895ae4d5df40e4'
p=Path('/home/root/aura-dpu-vision-20261021/staging')/sha[:16]/'bundle.tar.gz';assert hashlib.sha256(p.read_bytes()).hexdigest()==sha
root=Path('/home/root/aura-post-power-20261022/light2-preflight')/sha[:16];work=root/'work';work.mkdir(parents=True,exist_ok=True)
assert not (root/'report.json').exists()
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def health():
 with op.open('http://127.0.0.1:8790/health',timeout=3) as f:return json.load(f)
def units():
 return {n:subprocess.check_output(['systemctl','show',n,'-p','MainPID','-p','NRestarts','-p','ActiveState'],timeout=3).decode().strip() for n in ('aura-camera-ui.service','aura-avatar-ui.service','xserver-nodm.service')}
before=health();protected=units();assert before['identity']['face_targets']['backend']=='DPU_YUNET_INT8'
with tarfile.open(p,'r:gz') as a:
 for m in a.getmembers():
  name=Path(m.name);assert not name.is_absolute() and '..' not in name.parts and m.isfile() and m.size<100000
  target=work/name;target.parent.mkdir(parents=True,exist_ok=True);assert not target.is_symlink();data=a.extractfile(m).read()
  if target.exists():assert target.read_bytes()==data
  else:target.write_bytes(data)
result=subprocess.run(['/usr/bin/python3','-B',str(work/'run_preflight.py'),'--output',str(root/'results')],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=25)
after=health();report={'scope':'TARGET_BOARD_LIGHT2_SYNTHETIC_PREFLIGHT','returncode':result.returncode,
 'stderr':result.stderr.decode(errors='replace')[-2000:],'stdout':result.stdout.decode(errors='replace')[-1000:],
 'protected_before':protected,'protected_after':units(),'before_pid':before['pid'],'after_pid':after['pid'],
 'same_camera_advanced':before['pid']==after['pid'] and after['detected_frames']>before['detected_frames'],
 'new_native_jobs_created':0,'production_sources_changed':False,'bundle_sha256':sha}
for key,file in [('benchmark_report','report.json'),('assessment','assessment.json')]:
 if (root/'results'/file).is_file():report[key]=json.loads((root/'results'/file).read_text())
report['passed']=bool(result.returncode==0 and report.get('assessment',{}).get('passed') and report['same_camera_advanced'] and report['protected_before']==report['protected_after'])
(root/'report.json').write_text(json.dumps(report,indent=2)+'\n');raw=json.dumps(report,separators=(',',':')).encode()
print(json.dumps({'passed':report['passed'],'decoded_bytes':len(raw),'gzip_base64':base64.b64encode(gzip.compress(raw,mtime=0)).decode()}))
