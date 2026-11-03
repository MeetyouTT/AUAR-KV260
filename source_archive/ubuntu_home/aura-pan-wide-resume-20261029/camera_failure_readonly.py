import hashlib,json,os,subprocess
from pathlib import Path
d={'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'uptime':Path('/proc/uptime').read_text().split()[0]}
for label,args in [('camera_unit',['systemctl','show','aura-camera-ui.service','-p','MainPID','-p','ActiveState','-p','Result','-p','ExecMainStatus','-p','NRestarts']),('journal',['journalctl','-b','-u','aura-camera-ui.service','-n','70','--no-pager','-o','cat'])]:
 p=subprocess.run(args,capture_output=True,text=True,timeout=6);d[label]=p.stdout[-16000:]
d['usb_video']=[str(p) for p in Path('/dev').glob('video*')]
d['zocl_refcnt']=Path('/sys/module/zocl/refcnt').read_text().strip()
o=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735');m=json.loads((o/'meta.json').read_text());cfg=json.loads(Path(m['candidate_config']).read_text());cp=Path(cfg['native_execution']['checkpoint_output']);doc=json.loads(cp.read_text())
d['checkpoint']={'sha256':hashlib.sha256(cp.read_bytes()).hexdigest(),'scope':doc.get('scope'),'source_boot':doc['seed']['boot_id'],'source_pid':doc['seed']['source_pid'],'fenced':doc['seed']['fenced'],'primary_calls':doc['seed']['primary_calls'],'primary_overruns':doc['seed']['primary_period_overruns'],'optional_overruns':doc['seed']['overruns'],'pending':doc['auxiliary']['pending_result_tokens']}
print(json.dumps(d))
