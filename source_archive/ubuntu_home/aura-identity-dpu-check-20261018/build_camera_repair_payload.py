"""Build a source-pinned two-file repair; stage only, activation is separate."""
import base64,difflib,gzip,hashlib,json
from pathlib import Path
J=Path(__file__).resolve().parent;A=Path('/home/ghmd/Win共享文件/语音共享文件/aura')
def sha(data):return hashlib.sha256(data).hexdigest()
old=(J/'evidence/20261020T095456.506003Z-axis-manual-ui-inspect/current-board-avatar-gtk.py').read_text()
new=(J/'camera-repair/board_avatar_gtk.py').read_text()
oldlines,newlines=old.splitlines(keepends=True),new.splitlines(keepends=True)
replacements=[]
for group in difflib.SequenceMatcher(None,oldlines,newlines).get_grouped_opcodes(3):
 before=''.join(oldlines[group[0][1]:group[-1][2]])
 after=''.join(newlines[group[0][3]:group[-1][4]])
 assert old.count(before)==1;replacements.append([before,after])
trial=old
for before,after in replacements:trial=trial.replace(before,after)
assert trial==new and len(replacements)==2
baseline=json.loads((J/'latest-camera-repair-baseline.json').read_text())
value=json.loads((Path(baseline['evidence'])/'response.json').read_text())
pan=(A/'tools/pan_controls.py').read_bytes()
payload={'baseline':{'boot_id':'3e1add36-b917-4289-91dc-699348528782',
 'aura_root':'/home/root/aura-voice-barge-in-20261020/candidate-667b70d586ca/runtime/aura',
 'startup':'/home/root/aura-pan-manual-ui-20261020/fix-v2/startup',
 'startup_config_sha256':value['config_hashes']['config.json']},
 'files':{'tools/board_avatar_gtk.py':{'old_sha256':sha(old.encode()),'sha256':sha(new.encode()),'replacements':replacements},
 'tools/pan_controls.py':{'old_sha256':'5ff08c15b9fcc10fe8afbdc6f2dc45e33fa543fe3bd7006a726bfa1245441f2b','sha256':sha(pan),'base64':base64.b64encode(pan).decode()}}}
raw=json.dumps(payload,ensure_ascii=False,indent=2).encode()+b'\n'
(J/'camera-repair/payload.json').write_bytes(raw)
diff=''.join(difflib.unified_diff(oldlines,newlines,fromfile='a/tools/board_avatar_gtk.py',tofile='b/tools/board_avatar_gtk.py'))
(J/'camera-repair/board-avatar-preview.patch').write_text(diff)
files={'payload.json':raw,'deploy.py':(J/'board_camera_repair_deploy.py').read_bytes()}
lines=['"""Stage reviewed repair only; production services unchanged."""','import base64,gzip,hashlib,json','from pathlib import Path',
 "assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='3e1add36-b917-4289-91dc-699348528782'",
 "p=Path('/home/root/aura-pan-manual-ui-20261020/camera-fix-v3');p.mkdir(parents=True,exist_ok=False)"]
for name,data in files.items():
 lines+=['raw=gzip.decompress(base64.b64decode(%r))'%base64.b64encode(gzip.compress(data,mtime=0)).decode(),
          'assert hashlib.sha256(raw).hexdigest()==%r'%sha(data),'with (p/%r).open("xb") as f:f.write(raw)'%name]
lines+=['print(json.dumps({"status":"STAGED_ONLY_NO_SERVICE_CHANGE","path":str(p)}),flush=True)']
(J/'board_camera_repair_stage.py').write_text('\n'.join(lines)+'\n')
activate='''"""Launch the prepared repair once; no direct motion."""
import hashlib,json,subprocess
from pathlib import Path
p=Path('/home/root/aura-pan-manual-ui-20261020/camera-fix-v3')
assert hashlib.sha256((p/'deploy.py').read_bytes()).hexdigest()==%r
with (p/'activation.json').open('x') as marker:
 with (p/'deployment.log').open('xb') as log:
  child=subprocess.Popen(['/usr/bin/python3','-B',str(p/'deploy.py')],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 value={'status':'LAUNCHED_ONCE_DO_NOT_RETRY','pid':child.pid,'path':str(p)}
 marker.write(json.dumps(value)+'\\n')
print(json.dumps(value),flush=True)
'''%sha(files['deploy.py'])
(J/'board_camera_repair_activate.py').write_text(activate)
print(json.dumps({'payload_sha256':sha(raw),'files':{k:v['sha256'] for k,v in payload['files'].items()},'stage_bytes':len('\n'.join(lines))}))
