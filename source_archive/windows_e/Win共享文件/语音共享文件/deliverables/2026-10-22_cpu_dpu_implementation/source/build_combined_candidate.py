import ast,hashlib,json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
CAL=Path('/home/ghmd/aura-sface-calibration-20261022')
assert hashlib.sha256((CAL/'patch-manifest.json').read_bytes()).hexdigest()=='ee72779ef73f860d73517941efa2f65d75d9551d2321f639a3bba1a287a541af'
manifest=json.loads((CAL/'patch-manifest.json').read_text())
files={}
for item in manifest['source_files']:
    source=CAL/item['path'];assert hashlib.sha256(source.read_bytes()).hexdigest()==item['sha256']
    name=str(source.relative_to(CAL/'candidate/aura'));files[name]=source.read_text()
for source in (ROOT/'metrics-candidate/aura').rglob('*.py'):
    name=str(source.relative_to(ROOT/'metrics-candidate/aura'))
    body=source.read_text()
    if name=='board/vision/ui_camera_service.py':
        assert body.count('    return Handler\n')==1
        body=body.replace('    return Handler\n',
            '    from board.identity.calibration_http import wrap_handler\n    return wrap_handler(Handler,state)\n',1)
    files[name]=body
out=ROOT/'combined-candidate/aura'
for name,body in files.items():
    ast.parse(body,filename=name);target=out/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(body)
value={'status':'SOFTWARE_MERGED_NOT_DEPLOYED','calibration_manifest_sha256':hashlib.sha256((CAL/'patch-manifest.json').read_bytes()).hexdigest(),
    'merge_rule':'Retain all9 calibration sources; add metrics module/runtime; merge only handler wrapper into measured UI',
    'calibration_default_enabled':False,'metrics_default_enabled':False,'board_runtime_verified':False,
    'files':{name:{'sha256':hashlib.sha256(body.encode()).hexdigest(),'bytes':len(body.encode())} for name,body in sorted(files.items())}}
(ROOT/'combined-manifest.json').write_text(json.dumps(value,indent=2)+'\n')
print(json.dumps({'files':len(files),'status':value['status']}))
