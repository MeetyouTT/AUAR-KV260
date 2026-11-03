"""Passive metadata only; retain the user's listening selection and speech."""
import json,time,urllib.request,subprocess,re
rows=[]
for i in range(30):
 s=json.load(urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=5))
 rows.append({'at':time.monotonic(),'phase':s['phase'],'state':s.get('state'),'asset':s.get('asset'),
              'display':s['avatar_display'],'renderer':s['avatar_renderer'].get('profile'),
              'monitor':s['handsfree_dialogue']['enabled'],'listening':s['handsfree_dialogue']['state'],
              'microphone':s['handsfree_dialogue']['microphone_open'],'audio':s.get('audio_output_state'),
              'actions':[{'generation':t.get('generation'),'actions':t.get('actions',[]),'complete':t.get('audio_complete')} for t in s.get('turns',[])],
              'error':s.get('error')})
 if i<29:time.sleep(2)
entry=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','ExecStart','-p','DropInPaths'],text=True)
print(json.dumps({'effective':entry,'rows':rows}))
