"""Read-only inventory and archive/source comparisons for the shared AURA tree."""
import ast,collections,datetime,hashlib,json,os,zipfile
from pathlib import Path
OUT=Path(__file__).resolve().parent
ROOT=Path('/home/ghmd/Win共享文件');LIVE=ROOT/'共享文件夹'
def digest(data):return hashlib.sha256(data).hexdigest()
def save(name,data):(OUT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
skip={'.verysync','.git','__pycache__','node_modules','site-packages'}
index=[]
for base in (LIVE,ROOT/'方案',ROOT/'output'):
 for top,dirs,names in os.walk(base):
  dirs[:]=[d for d in dirs if d not in skip and not d.startswith('.venv')]
  for n in names:
   p=Path(top)/n;s=p.stat()
   index.append({'path':str(p.relative_to(ROOT)),'bytes':s.st_size,'mtime_ns':s.st_mtime_ns})
save('FILE_INDEX.json',{'recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':index})
syntax=[];hashes=[]
for p in sorted((LIVE/'aura').rglob('*.py')):
 if any(x in skip or x.startswith('.venv') for x in p.parts):continue
 raw=p.read_bytes();entry={'path':str(p),'sha256':digest(raw),'bytes':len(raw)};hashes.append(entry)
 try:ast.parse(raw,filename=str(p));syntax.append(dict(entry,syntax_ok=True))
 except (SyntaxError,UnicodeDecodeError) as e:syntax.append(dict(entry,syntax_ok=False,error=str(e)))
save('SOURCE_SYNTAX.json',syntax)
for base in (LIVE/'aura/docs',LIVE/'deliverables',ROOT/'output'):
 for p in base.rglob('*.md'):
  if p.stat().st_size<150000:
   raw=p.read_bytes();hashes.append({'path':str(p),'sha256':digest(raw),'bytes':len(raw)})
save('SOURCE_FINGERPRINTS.json',hashes)
archive=ROOT/'存档/汐蓝_实时演示移机基础包_2026-10-06_r1.zip'
rows=[];verified=0
with zipfile.ZipFile(archive) as z:
 manifest=json.loads(z.read('共享文件夹/package_manifest.json'))
 assert len(manifest['files'])==manifest['file_count']==903
 for f in manifest['files']:
  name=f['file'];raw=z.read('共享文件夹/'+name)
  assert len(raw)==f['bytes'] and digest(raw)==f['sha256'],name
  verified+=1;q=LIVE/name
  state='MISSING' if not q.is_file() else 'MATCH' if digest(q.read_bytes())==f['sha256'] else 'DIFFERENT'
  rows.append({'file':name,'current_state':state,'archive_sha256':f['sha256']})
 # Extract only authoritative reviewed text from the explicitly verified package.
 for name in ('aura/board/runtime/character.py','aura/board/runtime/audio/selected_voice.py',
              'aura/tools/facial_layers.py','aura/tools/realtime_metrics.py',
              'deliverables/2026-10-06_xilan_live/移机交接_汐蓝实时演示.md',
              'deliverables/2026-10-06_xilan_live/stage_config.json'):
  p=OUT/'archive-reference'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read('共享文件夹/'+name))
save('ARCHIVE_COMPARISON.json',{'archive':str(archive),'archive_sha256':digest(archive.read_bytes()),
 'payload_files_verified':verified,'counts':dict(collections.Counter(x['current_state'] for x in rows)),'files':rows})
launches=[]
for p in (LIVE/'deliverables/2026-10-06_xilan_live/evidence').glob('live_*.json'):
 d=json.loads(p.read_text());rows2=[]
 for name,expected in d.get('source_hashes_at_launch',{}).items():
  q=LIVE/'aura'/name
  rows2.append({'file':name,'expected_sha256':expected,'state':'MISSING' if not q.is_file() else 'MATCH' if digest(q.read_bytes())==expected else 'DIFFERENT'})
 launches.append({'evidence':str(p),'stats':d.get('stats'),'errors':d.get('errors'),
  'mode':d.get('mode'),'source_comparison':rows2})
save('LIVE_EVIDENCE_COMPARISON.json',launches)
important=['aura/board/runtime/character.py','aura/board/runtime/audio/selected_voice.py','aura/tools/facial_layers.py',
 'aura/tools/realtime_metrics.py','aura/tools/selected_voice_demo.py',
 'deliverables/2026-10-06_xilan_live/stage_config.json','deliverables/2026-10-06_xilan_live/移机交接_汐蓝实时演示.md',
 'deliverables/2026-10-08_chin_fix/README.md','deliverables/2026-10-06_voice_script_sync/acceptance.json']
save('MISSING_CURRENT_REFERENCES.json',[{'file':f,'exists':(LIVE/f).is_file()} for f in important])
print(json.dumps({'inventory_files':len(index),'python_files_parsed':len(syntax),'syntax_errors':sum(not x['syntax_ok'] for x in syntax),
 'archive_payloads_verified':verified,'current_vs_archive':dict(collections.Counter(x['current_state'] for x in rows)),
 'missing_important_references':[f for f in important if not (LIVE/f).is_file()],
 'launches':[{'name':Path(x['evidence']).name,'source_counts':dict(collections.Counter(y['state'] for y in x['source_comparison'])),'stats':x['stats']} for x in launches]},ensure_ascii=False))
