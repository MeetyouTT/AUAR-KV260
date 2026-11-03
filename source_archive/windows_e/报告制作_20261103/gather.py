from pathlib import Path
from datetime import datetime,timezone
import subprocess,json,shutil,hashlib,sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT=Path(r'E:\Win共享文件\协作任务\2026-11-03_technical_report_01a1a1a5')
for d in ['figures','evidence','sources','tools','qa','data','report']:(ROOT/d).mkdir(parents=True,exist_ok=True)
def remote(host,code,timeout=30):
    r=subprocess.run(['ssh','-o','BatchMode=yes',host,'python3 -'],input=code.encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout)
    if r.returncode: print(host,r.stderr.decode(errors='replace')[:1200])
    return r.stdout
idx=[]
def copy(p,target):
    if not p.is_file():return
    dest=ROOT/target;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
    idx.append({'source':str(p),'copy':str(dest.relative_to(ROOT)).replace('\\','/'),'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'bytes':dest.stat().st_size})
base=Path(r'E:\Win共享文件\协作任务')
for p in (base/'2026-11-02_dual_reports/evidence').iterdir():copy(p,'evidence/history/'+p.name)
for n in ['amd_design_report.md','metrics.csv','source_index.json']:
    copy(base/'2026-11-02_dual_reports'/n,'sources/previous_'+n)
copy(Path(r'D:\Download\writing_sample.md'),'sources/writing_sample.md')
curves=base/'2026-11-02_性能曲线与原生截图_01a19c53'
for p in (curves/'原生截图').glob('*.png'): copy(p,'figures/native_'+p.name)
for p in (curves/'数据').iterdir():copy(p,'data/history_'+p.name)
copy(curves/'图片索引与图注.txt','sources/history_figure_captions.txt')
for p in (base/'2026-11-02_dual_reports/figures').glob('*.png'):
    if 'pending' not in p.name:copy(p,'figures/old_'+p.name)
from PIL import Image
Image.open(r'C:\Users\REVO1\Downloads\10周年.psd').save(ROOT/'figures/competition_logo.png')
for n in ['report_outline.md','materials_checklist.md']:
    b=remote('aura-ubuntu',"from pathlib import Path\nimport sys\nsys.stdout.buffer.write(Path('/home/ghmd/Win共享文件/协作任务/2026-11-03_technical_report_outline/"+n+"').read_bytes())\n")
    (ROOT/'sources'/n).write_bytes(b)
release=Path(r'E:\Win共享文件\语音共享文件\deliverables\2026-11-03_scheme_a_source_release_9a4f\auar_xuefei')
for rel in ['README.md','report/dependencies.md','report/design_report.md','board/readme.md','build/reproduce.py','report/ai_collaboration.md']:
    copy(release/rel,'sources/release_'+rel.replace('/','_'))
code=r'''from pathlib import Path
import json,urllib.request,hashlib,subprocess,os
def get(port,path):
 try:
  raw=urllib.request.urlopen('http://127.0.0.1:'+str(port)+path,timeout=8).read()
  return {'status':'ok','value':json.loads(raw)}
 except Exception as e:return {'error':str(e)}
root=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
c=json.loads((root/'startup/config.json').read_text())
out={'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'uptime':Path('/proc/uptime').read_text().strip(),
 'config_sha256':hashlib.sha256((root/'startup/config.json').read_bytes()).hexdigest(),
 'config_fields':{k:v for k,v in c.items() if k!='component_sha256'},'component_count':len(c.get('component_sha256',{})),
 'gui':get(8783,'/health'),'camera':get(8790,'/health'),
 'os_release':Path('/etc/os-release').read_text(),'alsa':Path('/proc/asound/cards').read_text(),
 'python':subprocess.getoutput('python3 --version')}
print(json.dumps(out,ensure_ascii=False))
'''
b=remote('aura-kv260',code)
try:
 d=json.loads(b);d['host_received_utc']=datetime.now(timezone.utc).isoformat();(ROOT/'tmp_board.json').write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
 print('BOARD keys',d.keys());print('GUI keys',list(d.get('gui',{}).get('value',{})));print('CAM keys',list(d.get('camera',{}).get('value',{})))
except Exception as e:print('board parse',str(e),b[:500])
# Read the exact handler sources for read-only endpoints without copying business data.
code=r'''from pathlib import Path
import json
root=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13/runtime/aura/tools')
rows=[]
for f in root.glob('*.py'):
 t=f.read_text(errors='replace')
 if 'def do_GET' in t:
  lines=t.splitlines()
  rows.extend({'file':f.name,'line':i+1,'text':s.strip()} for i,s in enumerate(lines) if any(x in s for x in ['def do_GET','/health','/screen','/snapshot','/status','.png']))
print(json.dumps(rows,ensure_ascii=False))
'''
raw=remote('aura-kv260',code);(ROOT/'sources/gui_get_endpoints.json').write_bytes(raw)
print(raw.decode()[:2800])
(ROOT/'sources/source_manifest.json').write_text(json.dumps(idx,ensure_ascii=False,indent=2),encoding='utf-8')
print('ROOT',ROOT,'copied',len(idx))
