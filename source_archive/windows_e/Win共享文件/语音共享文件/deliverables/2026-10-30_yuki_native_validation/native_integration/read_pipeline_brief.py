from pathlib import Path
import json,time
root=Path('/home/root/aura-yuki-validation-20261030/native_integration')
for name in ('precision-validation-result.json','continuous.json','gtk-clock.json'):
    p=root/'results'/name
    if not p.exists():continue
    value=json.loads(p.read_text())
    if name=='precision-validation-result.json':
        value={k:value[k] for k in ('status','error') if k in value}|{'completed_steps':len(value.get('steps',[])),'last_step':value.get('steps',[])[-1:]}
    else:value={k:value[k] for k in ('status','duration','frames','actual_fps','interval_ms','checks','errors') if k in value}
    print(json.dumps({'file':name,'age_seconds':round(time.time()-p.stat().st_mtime,1),'result':value}))
