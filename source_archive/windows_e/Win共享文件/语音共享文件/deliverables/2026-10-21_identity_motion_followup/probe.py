"""Read-only board snapshot; omit names, templates, images and dialogue."""
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'2026-10-18_board_dialogue'))
from board_ssh import ssh

SCRIPT = r'''
import json,urllib.request,subprocess
def get(port,path):
 try:return json.load(urllib.request.urlopen('http://127.0.0.1:'+str(port)+path,timeout=4))
 except Exception as e:return {'probe_error':type(e).__name__}
def summary(value):
 if isinstance(value,dict):
  return {k:summary(v) for k,v in value.items() if k not in
   ('people','display_name','person_id','name','embedding','templates','text','transcript','history','messages','face_preview','subtitle','answer')}
 if isinstance(value,list):return {'list_length':len(value)}
 if isinstance(value,str) and len(value)>240:return '<long string omitted>'
 return value
ui=get(8783,'/api/state');cam=get(8790,'/health')
print(json.dumps({'boot_id':open('/proc/sys/kernel/random/boot_id').read().strip(),
 'camera':summary(cam),'ui_keys':list(ui),
 'ui':{k:summary(v) for k,v in ui.items() if any(s in k for s in ('pan','motion','identity','camera','monitor'))},
 'processes':subprocess.check_output(['ps','-eo','pid,args'],text=True).splitlines()[:1]+[
 r for r in subprocess.check_output(['ps','-eo','pid,args'],text=True).splitlines()
 if 'python' in r and any(s in r for s in ('camera','avatar_pan','launcher'))]},ensure_ascii=True))
'''
if __name__=='__main__':
    value=json.loads(ssh('python3 -',SCRIPT,timeout=25))
    (Path(__file__).parent/'board_snapshot.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
    print(json.dumps(value,indent=2))
