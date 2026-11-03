"""Validate only local research artifacts and links; no network or production I/O."""
import hashlib,json,re
from pathlib import Path
H=Path(__file__).resolve().parent
for name in ('PROGRESS.json','EXPERIMENTS.json','SOURCES.json'):
    value=json.loads((H/name).read_text(encoding='utf-8'));assert isinstance(value,dict)
sources=json.loads((H/'SOURCES.json').read_text(encoding='utf-8'))
assert sources['sources'] and len({row['id'] for row in sources['sources']})==len(sources['sources'])
assert all(row['primary'] and row['url'].startswith('https://') for row in sources['sources'])
text=(H/'README.md').read_text(encoding='utf-8')
local=[]
for target in re.findall(r'\]\(([^)]+)\)',text):
    if target.startswith('https://'):continue
    assert (H/target.split('#',1)[0]).is_file(),target
    local.append(target)
for name in sources['local_project_evidence_read']:assert (H/name).is_file(),name
files={}
for path in H.iterdir():
    if path.is_file() and path.name not in ('VALIDATION.json','SOURCE_MANIFEST.json'):
        files[path.name]={'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
(H/'SOURCE_MANIFEST.json').write_text(json.dumps({'scope':'research artifacts only; no model or private data','files':files},indent=2),encoding='utf-8')
report={'status':'PASS','source_entries':len(sources['sources']),'local_report_links':len(local),'json_valid':True,
        'research_only':True,'experiments_executed':False,'no_production_io':True}
(H/'VALIDATION.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
