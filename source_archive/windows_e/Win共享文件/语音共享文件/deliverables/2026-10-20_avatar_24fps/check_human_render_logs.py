import json,subprocess,re,urllib.request,time
from pathlib import Path
entry=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','ExecStart','-p','DropInPaths'],text=True)
cfg=Path(re.search(r'--config (\S+) ',entry).group(1));root=Path(json.loads(cfg.read_text())['runtime'])
s=json.load(urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=5))
keys=('phase','state','asset','audio_output_state','avatar_display','avatar_renderer','handsfree_dialogue','error')
turns=[{k:t.get(k) for k in ('generation','actions','audio_complete','duration_seconds','request_to_answer_seconds','request_to_feedback_or_audio_seconds')} for t in s.get('turns',[])]
files=[]
for p in sorted((root/'managed-runs').glob('*/evidence/*.json'),key=lambda p:p.stat().st_mtime,reverse=True)[:8]:
 try:
  data=json.loads(p.read_text());files.append({'path':str(p),'keys':list(data),'samples':data.get('samples',[]),'display':data.get('avatar_display'),'renderer':data.get('avatar_renderer')})
 except Exception as e:files.append({'path':str(p),'error':str(e)})
print(json.dumps({'effective':entry,'runtime':str(root),'at_monotonic':time.monotonic(),'state':{k:s.get(k) for k in keys},'turns':turns,'log':[ {k:v for k,v in e.items() if k not in ('text','reply','reply_text')} for e in s.get('log',[])],'saved_reports':files,'runs':[str(p) for p in (root/'managed-runs').glob('*/stage.log')]}))
