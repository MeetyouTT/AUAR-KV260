import concurrent.futures, hashlib, json, os, stat, time
from pathlib import Path
ROOT=Path('E:/Win共享文件')
PACKAGE=ROOT/'5090主机迁移包_20261101'
OUT=ROOT/'语音共享文件/deliverables/2026-11-02_5090_deployment'

def check(item):
    p, expected=item
    try:
        s=p.lstat()
        if getattr(s,'st_file_attributes',0)&stat.FILE_ATTRIBUTE_REPARSE_POINT:
            return {'path':str(p),'issue':'reparse_point_not_followed'}
        if s.st_size!=expected['bytes']:
            return {'path':str(p),'issue':'size','actual':s.st_size,'expected':expected['bytes']}
        if expected.get('sha256'):
            h=hashlib.sha256()
            with p.open('rb') as f:
                for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
            if h.hexdigest()!=expected['sha256']:
                return {'path':str(p),'issue':'sha256','actual':h.hexdigest(),'expected':expected['sha256']}
        return None
    except OSError as e:
        return {'path':str(p),'issue':type(e).__name__,'errno':e.errno}

def verify(name, items):
    started=time.monotonic()
    failures=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        for result in pool.map(check,items):
            if result:failures.append(result)
    return {'name':name,'files_checked':len(items),'sha256_checked':sum(bool(x[1].get('sha256')) for x in items),
            'bytes_expected':sum(x[1]['bytes'] for x in items),'issues_count':len(failures),
            'issues':failures,'elapsed_seconds':round(time.monotonic()-started,3)}

workspace=[json.loads(line) for line in (PACKAGE/'verification/WORKSPACE_FILES.jsonl').open(encoding='utf-8-sig')]
external=json.loads((PACKAGE/'environment/EXTERNAL_COPY_MANIFEST.json').read_bytes())
package=json.loads((PACKAGE/'PACKAGE_MANIFEST.json').read_bytes())['files']
tts=ROOT/'语音共享文件/aura/models/tts/OmniVoice'
identity=json.loads((tts/'download_identity.json').read_bytes())
groups=[('workspace',[(ROOT/x['path'],x) for x in workspace]),
        ('external_dependencies',[(Path(x['target']),x) for x in external]),
        ('sealed_migration_package',[(PACKAGE/x['path'],x) for x in package]),
        ('formal_omnivoice',[(tts/x['path'],x) for x in identity['files']])]
report={'created_utc':__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),
        'large_workspace_files_size_only_unless_manifest_hashed':True,'results':[]}
for name,items in groups:
    result=verify(name,items);report['results'].append(result)
    print(json.dumps({k:v for k,v in result.items() if k!='issues'}),flush=True)
    (OUT/'payload_verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
report['passed']=all(x['issues_count']==0 for x in report['results'])
(OUT/'payload_verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'passed':report['passed']}),flush=True)
