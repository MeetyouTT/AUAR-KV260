import json,subprocess,urllib.request
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with op.open('http://127.0.0.1:8790/health',timeout=4) as r:h=json.load(r)
f=h['identity']['face_targets']
print(json.dumps({'pid':h['pid'],'freshness':f['freshness_metrics'],
 'controller_journal':subprocess.check_output(['journalctl','-u','aura-video-trial-0dad262102329bfc.service','--no-pager','-n','8','-o','short-monotonic']).decode()[-1800:],
 'gui_start':subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','-p','ActiveEnterTimestampMonotonic']).decode()}))
