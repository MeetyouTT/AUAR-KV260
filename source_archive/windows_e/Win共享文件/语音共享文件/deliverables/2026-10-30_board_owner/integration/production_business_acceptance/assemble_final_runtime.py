"""Root transport for final source-only assembly; the UI publisher is separate."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[3]
sys.path.insert(0,str(PROJECT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
BASE=HERE.parent/'production_business_overlay'
PRESENTATION=HERE.parent/'production_presentation_patch'
INCOMING='/home/root/aura-board-business-20261030/incoming-production-dc87c7f9'
ZIP_SHA='cbf0dc69a97e27dd3e98ee847b1a3bd7f2709d46a24f9c4e1beb231e159519ae'
MANIFEST_SHA='7e74bf960205e114f889edb205c88a1717d687418a08c308902572904ae69961'
ASSEMBLER_SHA='bf5e9240132f659b08328f0ef2dc728d8634d78a0378a5c9940adc4c853feb60'
PRESENTATION_PARENT_SHA='6925a7262db0a34d4e129f5a1976e82f08d6b10c552e4eb577f33685a143f8c1'
PRESENTATION_MANIFEST_SHA='ef0553734c252df451f60b5b5b9d3203655d3bb37aebf6402ab07576cb903cbc'

REMOTE=r'''
import base64,hashlib,json,os,subprocess
from pathlib import Path,PurePosixPath
root=Path(INCOMING);assert root.resolve()==root and root.stat().st_mode&0o077==0
def put(name,encoded,pin):
 p=root/name;raw=base64.b64decode(encoded,validate=True);assert hashlib.sha256(raw).hexdigest()==pin
 p.parent.mkdir(mode=0o700,parents=True,exist_ok=True);assert p.resolve()==p and not p.is_symlink()
 if p.exists():assert p.read_bytes()==raw
 else:
  fd=os.open(str(p),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
  with os.fdopen(fd,'wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
for name,(encoded,pin) in FILES.items():put(name,encoded,pin)
assert hashlib.sha256(Path(CONFIG_PATH).read_bytes()).hexdigest()==CONFIG_SHA
cmd=['/usr/bin/python3','-B',str(root/'assemble_production_v2.py'),ACTION,
 '--manifest',str(root/'production_business.source_only.manifest.json'),'--manifest-sha256',MANIFEST_SHA,
 '--overlay',str(root/'production_business.source_only.overlay.zip'),'--config',CONFIG_PATH,'--config-sha256',CONFIG_SHA,
 '--target',TARGET,'--extra-sources',str(root/'extra_sources.json'),'--extra-sources-sha256',EXTRA_SHA]
env=dict(os.environ,PATH='/usr/sbin:/usr/bin:/sbin:/bin',PYTHONDONTWRITEBYTECODE='1')
r=subprocess.run(cmd,capture_output=True,text=True,env=env,timeout=75)
try:v=json.loads(r.stdout)
except ValueError:v=dict(status='ASSEMBLER_OUTPUT_INVALID',stderr_type='non_json')
print(json.dumps(dict(returncode=r.returncode,result=v),ensure_ascii=True))
'''

def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=('inspect','stage','startup-check'));args=p.parse_args()
    config=json.loads((HERE/'production_config_staged.json').read_text(encoding='utf-8'))
    manifest=(PRESENTATION/'overlay_manifest.json').read_bytes()
    assert hashlib.sha256(manifest).hexdigest()==PRESENTATION_MANIFEST_SHA
    v=json.loads(manifest);assert v['base_manifest_sha256']==PRESENTATION_PARENT_SHA and len(v['files'])==3
    clean_raw=(BASE/'production_business.source_only.manifest.json').read_bytes()
    assert hashlib.sha256(clean_raw).hexdigest()==MANIFEST_SHA
    clean=json.loads(clean_raw)
    assert len(clean['files'])==367 and not any('__pycache__' in name for name in clean['files'])
    for row in v['files']:
        if row['target'] in clean['files']:
            assert clean['files'][row['target']]['sha256']==row['input_sha256']
        else:assert row['target']=='aura/tools/production_memory_presentation.py'
    files={}
    def add(name,path,pin):
        raw=Path(path).read_bytes();assert hashlib.sha256(raw).hexdigest()==pin
        files[name]=(base64.b64encode(raw).decode(),pin)
    add('assemble_production_v2.py',BASE/'assemble_production_v2.py',ASSEMBLER_SHA)
    add('production_business.source_only.overlay.zip',BASE/'production_business.source_only.overlay.zip',ZIP_SHA)
    add('production_business.source_only.manifest.json',BASE/'production_business.source_only.manifest.json',MANIFEST_SHA)
    extra={'schema':'aura.production-source-dependencies.v1','files':{}}
    for row in v['files']:
        name=row['target'];assert name.startswith('aura/') and '..' not in Path(name).parts
        add('extra/'+name,row['source'],row['sha256'])
        extra['files'][name]={'path':INCOMING+'/extra/'+name,'sha256':row['sha256']}
    raw=(json.dumps(extra,sort_keys=True,indent=2)+'\n').encode();extra_sha=hashlib.sha256(raw).hexdigest()
    files['extra_sources.json']=(base64.b64encode(raw).decode(),extra_sha)
    identity=hashlib.sha256((MANIFEST_SHA+PRESENTATION_MANIFEST_SHA+config['sha256']).encode()).hexdigest()[:16]
    target='/home/root/aura-board-business-20261030/production-'+identity
    values=dict(FILES=files,INCOMING=INCOMING,CONFIG_PATH=config['path'],CONFIG_SHA=config['sha256'],
        MANIFEST_SHA=MANIFEST_SHA,EXTRA_SHA=extra_sha,TARGET=target,ACTION=args.action)
    result=json.loads(ssh('python3 -B -','\n'.join(k+'='+repr(v) for k,v in values.items())+'\n'+REMOTE,timeout=90))
    (HERE/('assembly_'+args.action+'.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=True));assert result['returncode']==0
    if args.action=='stage':
        value=result['result'];assert value['status']=='PRODUCTION_SOURCE_STAGED_NOT_STARTED'
        spec=dict(boot_id='8100a7fd-0c6a-46c4-82b8-f874988a1521',target=target,
            startup_sha256=value['startup_sha256'],component_pins=value['component_pins'],retention_enabled=False,
            configuration_sha256=config['sha256'],presentation_manifest_sha256=PRESENTATION_MANIFEST_SHA)
        (HERE/'spec.json').write_text(json.dumps(spec,indent=2)+'\n',encoding='utf-8')

if __name__=='__main__':main()
