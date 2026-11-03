"""Finish offline auditing/packaging after the builder; never accesses a board."""
import hashlib,json,subprocess,time
from pathlib import Path
R=Path(__file__).resolve().parent;start=time.monotonic()
while True:
    s=json.loads((R/'BUILD_STATUS.json').read_text())
    if s['status']=='IMPLEMENTED_PENDING_PAIRING_AND_BOARD':break
    if s['status'].endswith('_FAILED'):raise RuntimeError('Builder failed; no package or deployment')
    if time.monotonic()-start>3600:raise TimeoutError('Offline build still incomplete; no package claimed')
    time.sleep(5)
source=R/'implementation/source_routed.dcp';before=hashlib.sha256(source.read_bytes()).hexdigest()
with (R/'final-audit/console.log').open('w') as f:
    p=subprocess.run(['/home/ghmd/Xilinx_2022.2/Vivado/2022.2/bin/vivado','-mode','batch','-source',str(R/'audit-final.tcl'),'-log',str(R/'final-audit/vivado.log'),'-journal',str(R/'final-audit/vivado.jou')],cwd=R,stdout=f,stderr=subprocess.STDOUT,timeout=1800)
assert p.returncode==0 and hashlib.sha256(source.read_bytes()).hexdigest()==before
for name in ['package_wide.py','create_transfer_bundle.py','verify_transfer.py']:
    with (R/'final-audit'/(name+'.log')).open('w') as f:
        p=subprocess.run(['python3','-B',str(R/name)],cwd=R,stdout=f,stderr=subprocess.STDOUT,timeout=180)
    if p.returncode:raise RuntimeError(name+' failed; no board action')
t=json.loads((R/'TRANSFER_STATUS.json').read_text())
with (R/'final-audit/transfer-dry-run.log').open('w') as f:
    p=subprocess.run(['python3','-B',str(R/'install_staged_bundle.py'),t['archive'],'--sha256',t['sha256'],'--boot','00000000-0000-0000-0000-000000000000'],stdout=f,stderr=subprocess.STDOUT,timeout=60)
assert p.returncode==0
result={'status':'OFFLINE_AUDITED_PACKAGED_PENDING_POWER_RETURN','board_accessed':False,'deployed':False,'range_physically_verified':False,'routed_checkpoint_sha256':before,'package':json.loads((R/'PACKAGE_STATUS.json').read_text()),'transfer':t}
(R/'OFFLINE_COMPLETION.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'status':result['status'],'transfer_bytes':t['bytes'],'board_accessed':False}))
