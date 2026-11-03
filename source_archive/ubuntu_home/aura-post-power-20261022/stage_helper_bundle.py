"""Use the existing reviewed framed UART transfer for one hash-pinned helper."""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile

ROOT=Path(__file__).resolve().parent
PRIVATE=Path('/home/ghmd/aura-dpu-vision-20261021')
PROBES=Path('/home/ghmd/aura-model-inventory-20261021')
STAGER=Path('/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-21_dpu_vision_start/source/stage_board.py')


def main():
    if sys.flags.optimize:raise RuntimeError('Helper staging requires assertions enabled')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path)
    parser.add_argument('--boot',required=True)
    parser.add_argument('--label',required=True)
    args=parser.parse_args()
    raw=args.source.read_bytes();compile(raw,str(args.source),'exec')
    digest=hashlib.sha256(raw).hexdigest()
    archive=io.BytesIO()
    with tarfile.open(fileobj=archive,mode='w') as out:
        info=tarfile.TarInfo('source.py');info.size=len(raw);info.mode=0o600;info.mtime=0
        out.addfile(info,io.BytesIO(raw))
    blob=gzip.compress(archive.getvalue(),mtime=0)
    sha=hashlib.sha256(blob).hexdigest();bundle=PRIVATE/'work'/('postpower-helper-'+digest[:16]+'.tar.gz')
    if bundle.exists():
        if bundle.read_bytes()!=blob:raise ValueError('Existing helper bundle differs')
    else:bundle.write_bytes(blob)
    folder=ROOT/('transfer-'+args.label);folder.mkdir(exist_ok=False)
    with (folder/'stage.log').open('w') as output:
        stage=subprocess.run([sys.executable,'-B',str(STAGER),str(bundle),'--boot',args.boot],stdout=output,stderr=subprocess.STDOUT)
    if stage.returncode:raise RuntimeError('Framed staging failed; see private stage log')
    staged=json.loads((PRIVATE/'latest-stage.json').read_text())
    assert staged['complete'] and staged['sha256']==sha
    remote='/home/root/aura-post-power-20261022/helpers/'+digest[:16]+'/source.py'
    probe=PROBES/('bundle_launch_'+digest[:16]+'.py')
    code='''import hashlib,json,runpy,tarfile
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
p=Path(BUNDLE);assert hashlib.sha256(p.read_bytes()).hexdigest()==BUNDLE_SHA
with tarfile.open(p,'r:gz') as a:
 assert a.getnames()==['source.py']
 m=a.getmember('source.py');assert m.isfile() and m.size<300000
 raw=a.extractfile(m).read();assert hashlib.sha256(raw).hexdigest()==SOURCE_SHA
target=Path(TARGET);assert Path('/home/root/aura-post-power-20261022/helpers') in target.parents
assert target.parent.resolve()==target.parent and not target.is_symlink()
target.parent.mkdir(parents=True,exist_ok=True);assert target.parent.resolve()==target.parent
if target.exists():assert target.read_bytes()==raw
else:
 with target.open('xb') as f:f.write(raw)
runpy.run_path(str(target),run_name='__main__')
'''
    constants={'BOOT':args.boot,'BUNDLE':staged['destination'],'BUNDLE_SHA':sha,'SOURCE_SHA':digest,'TARGET':remote}
    code='\n'.join(key+'='+repr(value) for key,value in constants.items())+'\n'+code
    if probe.exists():assert probe.read_text()==code
    else:probe.write_text(code)
    with (folder/'launch.log').open('w') as output:
        result=subprocess.run([sys.executable,str(PROBES/'run_probe.py'),probe.name],stdout=output,stderr=subprocess.STDOUT)
    status=json.loads(probe.with_suffix('.status.json').read_text())
    if result.returncode or status.get('exit_code')!=0:raise RuntimeError('Helper launch failed; see private launch log')
    response=json.loads(probe.with_suffix('.response.json').read_text())
    manifest={'source_sha256':digest,'bundle_sha256':sha,'remote_helper':remote,
        'stage_evidence':staged['evidence'],'stage_retries':staged['retries'],
        'console_echo_restored':status.get('console_echo_restored'),'launch':response}
    (folder/'result.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(manifest))


if __name__=='__main__':main()
