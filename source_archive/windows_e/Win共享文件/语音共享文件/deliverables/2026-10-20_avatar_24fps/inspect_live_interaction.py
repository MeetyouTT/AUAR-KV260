import json,time,urllib.request,subprocess
def get(port,path):return json.load(urllib.request.urlopen('http://127.0.0.1:%s%s'%(port,path),timeout=5))
rows=[]
for i in range(12):
 s=get(8783,'/api/state')
 rows.append({k:s.get(k) for k in ('phase','state','display_state','asset','playing','paused','audio_output_state','avatar_display','avatar_renderer','handsfree_dialogue','automatic_conversation','voice_barge_in','local_transcription','log','turns','error')})
 if i<11:time.sleep(2)
print(json.dumps({'rows':rows,'camera':get(8790,'/health'),'cpu':subprocess.check_output(['ps','-eo','pid,pcpu,comm','--sort=-pcpu'],text=True).splitlines()[:12]}))
