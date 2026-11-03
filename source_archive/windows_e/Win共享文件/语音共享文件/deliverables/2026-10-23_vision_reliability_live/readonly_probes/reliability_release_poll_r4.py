import hashlib,json,subprocess,urllib.request
from pathlib import Path
out={'read_only':True,'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip()}
root=Path('/home/root/aura-vision-reliability-20261023/f7624754038f3669')
p=root/'report.json';out['report_exists']=p.exists()
if p.exists():
 d=json.loads(p.read_text())
 out['report']={k:d.get(k) for k in ('complete','passed','accepted','phase','error','error_location','restore_error','guard_left_armed','release','camera_pid','gui_pid','xserver_pid','board_isolated','rollback','rollback_sha256','unit_sha256','identity_config_sha256','database_sha256')}
 if d.get('observation'):
  stage=d['observation'];out['report']['observation']={k:v for k,v in stage.items() if k!='samples'}
  out['report']['sample_count']=len(stage.get('samples',[]))
  out['report']['last_sample']=stage.get('samples',[])[-1] if stage.get('samples') else None
 if d.get('restoration'):out['report']['restoration']=d['restoration']
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
try:
 with op.open('http://127.0.0.1:8790/health',timeout=3) as r:h=json.load(r)
 i=h['identity'];f=i['face_targets'];s=h['dpu_schedule']
 out['current']={'pid':h['pid'],'yolo_hz':h['detection_hz'],'identity_backend':i['backend'],'identity_ready':i['ready'],
 'feature_status':i.get('feature_status'),'feature_inference':i.get('feature_inference'),'face_backend':f['backend'],
 'worker_alive':f.get('worker_alive'),'fault_latched':f.get('fault_latched'),'face_source_age_ms':f['source_age_ms'],
 'gaps':f['freshness_metrics']['counters']['observed_gap_intervals'],'optional':s['optional'],
 'primary_period_overruns':s['primary_period_overruns'],'diagnostic_failures':s.get('diagnostic_failures'),
 'owner_fenced':s.get('owner_fenced')}
except Exception as e:out['current_error']=type(e).__name__
out['unit_sha256']=hashlib.sha256(Path('/etc/systemd/system/aura-camera-ui.service').read_bytes()).hexdigest()
out['services']={name:subprocess.check_output(['systemctl','show',name,'-p','ActiveState','-p','MainPID','-p','NRestarts']).decode().strip() for name in ('aura-camera-ui.service','aura-avatar-ui.service','xserver-nodm.service')}
print(json.dumps(out))
