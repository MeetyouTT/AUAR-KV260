"""Refresh documentary archive bytes and verify local report links."""
import hashlib,json,re,zipfile
from pathlib import Path
H=Path(__file__).resolve().parent.resolve()
manifest=json.loads((H/'archive_manifest.json').read_text(encoding='utf-8'))
archive=H/manifest['file'];assert archive.parent==H
with zipfile.ZipFile(archive) as old:names=old.namelist()
names=sorted(set(names+['verify_delivery_artifacts.py']))
allowed={'.py','.ps1','.md','.json','.xml','.log'}
for name in names:
 path=(H/name).resolve();assert path.is_relative_to(H) and path.is_file()
 assert path.suffix.lower() in allowed and path.stat().st_size<2*1024*1024
temporary=H/(archive.name+'.part')
with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED) as output:
 for name in names:output.write(H/name,name)
with zipfile.ZipFile(temporary) as output:
 assert output.testzip() is None
 assert all(output.read(name)==(H/name).read_bytes() for name in names)
temporary.replace(archive)
manifest.update(files=len(names),bytes=archive.stat().st_size,sha256=hashlib.sha256(archive.read_bytes()).hexdigest())
(H/'archive_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
for name in ('README.md','CONTINUE.md'):
 for target in re.findall(r'\]\(([^)]+)\)',(H/name).read_text(encoding='utf-8')):
  if '://' in target or target.startswith('#'):continue
  assert (H/target).is_file(),(name,target)
assert json.loads((H/'PROGRESS.json').read_text(encoding='utf-8'))['revision']=='voice-chat-memory-20261029-r9'
print(json.dumps({'status':'PASS','local_report_links':'valid','archive_matches_current_sources':True,'manifest':manifest}))
