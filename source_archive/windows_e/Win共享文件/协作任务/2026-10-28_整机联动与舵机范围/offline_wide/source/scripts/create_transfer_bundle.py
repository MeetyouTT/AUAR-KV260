"""Create a hash-bound transfer archive; never connect to the board."""
from pathlib import Path
import gzip,hashlib,io,json,tarfile
R=Path(__file__).resolve().parent
APP='aura-visual-servo-b4096-wide-v1'
def sha(b):return hashlib.sha256(b).hexdigest()
status=json.loads((R/'PACKAGE_STATUS.json').read_text());assert status['status']=='PAIRED_OFFLINE_BUNDLE_READY_PENDING_BOARD'
manifest_raw=(R/'bundle/candidate-manifest.json').read_bytes();assert sha(manifest_raw)==status['manifest_sha256']
manifest=json.loads(manifest_raw);entries={};instructions=[]
for path,digest in manifest['runtime_files'].items():
    name=Path(path).name;raw=(R/'bundle/lib/firmware/xilinx'/APP/name).read_bytes();assert sha(raw)==digest
    item={'path':path,'target_bytes':len(raw),'target_sha256':digest,'encoding':'raw'}
    if name.endswith('.bit.bin'):
        oldpath=Path('/home/ghmd/aura-pan-joint-20261023/bundle/lib/firmware/xilinx/aura-visual-servo-b4096-v2/aura-visual-servo-b4096-v2.bit.bin')
        old=oldpath.read_bytes();assert sha(old)=='dc708cb21c3c99c3e2de9f6969d9c1ec7c5c97d347d675b15014d6686931902d'
        if len(old)==len(raw):
            delta=bytes(a^b for a,b in zip(old,raw))
            if len(gzip.compress(delta,mtime=0))<len(gzip.compress(raw,mtime=0)):
                raw=delta;item.update(encoding='xor',base_path='/lib/firmware/xilinx/aura-visual-servo-b4096-v2/'+oldpath.name,base_sha256=sha(old))
    key='firmware/'+name+('.xor' if item['encoding']=='xor' else '')
    entries[key]=raw;item.update(archive_file=key,archive_bytes=len(raw),archive_sha256=sha(raw));instructions.append(item)
for p in (R/'bundle').rglob('*'):
    if p.is_file() and 'lib/firmware' not in str(p.relative_to(R/'bundle')):
        entries['release/'+str(p.relative_to(R/'bundle'))]=p.read_bytes()
controller=json.loads((R/'controller/deployment-manifest.json').read_text())
for item in controller['files']:
    raw=Path(item['source']).read_bytes();assert sha(raw)==item['sha256'];entries['controller/'+item['source_rel']]=raw
entries['controller/deployment-manifest.json']=(R/'controller/deployment-manifest.json').read_bytes()
for p in (R/'gui_motion').rglob('*.py'):entries['gui_patch/'+str(p.relative_to(R/'gui_motion'))]=p.read_bytes()
entries['rated_range_trial.py']=(R/'rated_range_trial.py').read_bytes()
transfer={'schema':'aura-wide-transfer-1','app':APP,'build_id':0x10282601,'manifest_sha256':sha(manifest_raw),
          'release_root':'/home/root/aura-pan-wide-20261028/release-'+sha(manifest_raw)[:16],
          'controller_root':'/home/root/aura-pan-wide-20261028/control-10282601','firmware':instructions,
          'files':{n:{'bytes':len(b),'sha256':sha(b)} for n,b in entries.items()},'programs_hardware':False}
entries['transfer.json']=(json.dumps(transfer,indent=2)+'\n').encode()
buffer=io.BytesIO()
with tarfile.open(fileobj=buffer,mode='w') as archive:
    for name,raw in sorted(entries.items()):
        info=tarfile.TarInfo(name);info.size=len(raw);info.mtime=0;info.mode=0o600;archive.addfile(info,io.BytesIO(raw))
blob=gzip.compress(buffer.getvalue(),mtime=0);out=R/'wide-transfer.tar.gz'
with out.open('xb') as f:f.write(blob)
result={'status':'TRANSFER_PREPARED_NO_BOARD_ACCESS','archive':str(out),'bytes':len(blob),'sha256':sha(blob),'firmware_encoding':{Path(i['path']).name:i['encoding'] for i in instructions},'files':len(entries),'release_root':transfer['release_root'],'controller_manifest_sha256':sha(entries['controller/deployment-manifest.json'])}
(R/'TRANSFER_STATUS.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
