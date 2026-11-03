#!/usr/bin/env python3
"""Freeze this run's reviewed sources with the exact previous board-tested binaries."""
import hashlib
import json
from pathlib import Path
import shutil
import tarfile
from prepare_live import ROOT,manifest

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

cfg=json.loads((ROOT/'config.json').read_text())
cfg.update(agent_helpers=cfg['work']+'/agent_helpers.py',
           agent_helpers_sha256=sha(ROOT/'agent_review/agent_helpers.py'),
           common_sha256=sha(ROOT/'live_common.py'),sustained_seconds=1800,
           sample_interval_seconds=30,candidate_log=cfg['work']+'/candidate-manager.log')
payload=ROOT/'reviewed_payload';payload.mkdir(exist_ok=False)
stage=payload/'candidate-stage';stage.mkdir()
original=Path('/home/ghmd/kv260-runtime-enable-20261002/bundle/kv260-runtime-reviewed.tar.gz')
assert sha(original)=='09b0ae9666e36724c2f45c882dc08daf88d2a7ca480e35e0a0984941a8902932'
with tarfile.open(original) as archive:
    for member in archive.getmembers():
        if Path(member.name).name in ['dfx-mgrd','zocl.ko']:
            assert member.isfile()
            (stage/Path(member.name).name).write_bytes(archive.extractfile(member).read())
assert sha(stage/'dfx-mgrd')==cfg['manager_sha256']
assert sha(stage/'zocl.ko')==cfg['module_sha256']
actions=payload/'actions';actions.mkdir()
shutil.copy2(ROOT/'action_sources/start_candidate_body.py',actions/'10_start.py')
body="""p=Path(CFG['agent_helpers'])
assert digest(p)==CFG['agent_helpers_sha256']
exec(compile(p.read_bytes(),str(p),'exec'))
begin_phase('20-official-functional')
query=dpu_query(OFFICIAL_APP,'official-query')
top5=classify(OFFICIAL_APP,'official-classification')
state=sample('official')
kernel_check('official-functional')
finish_phase({'query':query,'top5':top5,'sample':state})
"""
(actions/'20_functional.py').write_text(body)
for path in (ROOT/'agent_review/action_sources').glob('*.py'):
    shutil.copy2(path,actions/path.name)
for name,source in [('live_common.py',ROOT/'live_common.py'),('agent_helpers.py',ROOT/'agent_review/agent_helpers.py'),('board_worker.py',ROOT/'board_worker.py')]:
    shutil.copy2(source,payload/name)
for path in payload.rglob('*.py'):compile(path.read_text(),str(path),'exec')
cfg['phase_hashes']={p.name:sha(p) for p in sorted(actions.iterdir())}
(payload/'config.json').write_text(json.dumps(cfg,indent=2)+'\n')
assert len(cfg['phase_hashes'])==6
members={str(p.relative_to(payload)):sha(p) for p in sorted(payload.rglob('*')) if p.is_file()}
(payload/'SHA256SUMS').write_text(''.join(f'{value}  {name}\n' for name,value in members.items()))
archive_path=ROOT/'reviewed_package.tar.gz'
with tarfile.open(archive_path,'w:gz') as archive:
    for path in sorted(payload.rglob('*')):
        if path.is_file():archive.add(path,arcname=str(path.relative_to(payload)),recursive=False)
record={'work':cfg['work'],'archive':str(archive_path),'sha256':sha(archive_path),
        'bytes':archive_path.stat().st_size,'members':{str(p.relative_to(payload)):sha(p) for p in payload.rglob('*') if p.is_file()},'config_sha256':sha(payload/'config.json'),
        'worker_sha256':sha(payload/'board_worker.py'),'original_bundle_sha256':sha(original)}
(ROOT/'package_manifest.json').write_text(json.dumps(record,indent=2)+'\n')
template=Path('/home/ghmd/kv260-dfx-manager-repair-20261002/evidence/20261003T042453Z-board-validation/transfer_candidate.py').read_text()
template=template.replace('/home/ghmd/kv260-dfx-manager-repair-20261002/bundle-v2/kv260-dfx-watch-candidate.tar.gz',str(archive_path))
template=template.replace('1718a46975f046ea018cf0b25b8373051dde9e0f5347185956775e77f87b39f2',record['sha256'])
template=template.replace('/home/root/kv260-dfx-manager-repair-20261003T042453Z/candidate.tar.gz',cfg['work']+'/reviewed-package.tar.gz')
template=template.replace('03-transfer','transfer').replace('reviewed DFX candidate bundle','reviewed temporary joint-test bundle')
(ROOT/'evidence/transfer_reviewed.py').write_text(template)
code="""import os,tarfile,hashlib,json,subprocess
from pathlib import Path
WORK=Path(%r)
assert os.geteuid()==0 and os.uname().release=='5.15.36-xilinx-v2022.2'
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==%r
p=WORK/'reviewed-package.tar.gz'
assert hashlib.sha256(p.read_bytes()).hexdigest()==%r
with tarfile.open(str(p),'r:gz') as archive:
 for member in archive.getmembers():
  assert member.isfile() and not member.name.startswith('/') and '..' not in Path(member.name).parts
  target=WORK/member.name;target.parent.mkdir(parents=True,exist_ok=True)
  with target.open('xb') as stream:stream.write(archive.extractfile(member).read())
subprocess.run(['sha256sum','-c','SHA256SUMS'],cwd=str(WORK),check=True)
(WORK/'candidate-stage/dfx-mgrd').chmod(0o755)
common=WORK/'live_common.py';assert hashlib.sha256(common.read_bytes()).hexdigest()==%r
exec(compile(common.read_bytes(),str(common),'exec'))
guard(CFG['stock_srcversion'],'kv260-benchmark-b4096');manager_guard(False)
assert not Path(CFG['override']).exists() and not Path(CFG['override']).parent.exists()
print('REVIEWED_STAGE_READY '+str(WORK),flush=True)
"""%(cfg['work'],cfg['boot_id'],record['sha256'],cfg['common_sha256'])
manifest('unpack',[('stage',code,180)])
launch="""import os,json,hashlib,subprocess
from pathlib import Path
WORK=Path(%r)
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==%r
cfg=WORK/'config.json';assert hashlib.sha256(cfg.read_bytes()).hexdigest()==%r
worker=WORK/'board_worker.py';assert hashlib.sha256(worker.read_bytes()).hexdigest()==%r
common=WORK/'live_common.py';assert hashlib.sha256(common.read_bytes()).hexdigest()==%r
exec(compile(common.read_bytes(),str(common),'exec'))
guard(CFG['stock_srcversion'],'kv260-benchmark-b4096');manager_guard(False)
assert not (WORK/'controller-status.json').exists()
subprocess.run(['systemd-run','--unit=kv260-runtime-live-review-20261003T085031Z','--property=StandardOutput=file:'+str(WORK/'controller.log'),'--property=StandardError=inherit','--property=WorkingDirectory='+str(WORK),'/usr/bin/python3','-B',str(worker)],check=True)
print('FINITE_REVIEW_LAUNCHED '+str(WORK),flush=True)
"""%(cfg['work'],cfg['boot_id'],record['config_sha256'],record['worker_sha256'],cfg['common_sha256'])
manifest('launch',[('worker',launch,180)])
print(json.dumps(record,indent=2))
