"""Independently reconstruct transferred firmware on the host; no device IO."""
from pathlib import Path
import hashlib,json
from install_staged_bundle import unpack
R=Path(__file__).resolve().parent
t=json.loads((R/'TRANSFER_STATUS.json').read_text());blob=Path(t['archive']).read_bytes()
sha=lambda b:hashlib.sha256(b).hexdigest()
assert sha(blob)==t['sha256'];meta,files=unpack(blob);rows=[]
for item in meta['firmware']:
    data=files[item['archive_file']]
    if item['encoding']=='xor':
        base=Path('/home/ghmd/aura-pan-joint-20261023/bundle/lib/firmware/xilinx/aura-visual-servo-b4096-v2/aura-visual-servo-b4096-v2.bit.bin').read_bytes()
        assert sha(base)==item['base_sha256'] and len(base)==len(data)
        data=bytes(x^y for x,y in zip(base,data))
    assert len(data)==item['target_bytes'] and sha(data)==item['target_sha256']
    original=R/'bundle/lib/firmware/xilinx'/meta['app']/Path(item['path']).name
    assert data==original.read_bytes()
    rows.append({'file':Path(item['path']).name,'bytes':len(data),'sha256':sha(data),'encoding':item['encoding'],'byte_equal_to_packaged_file':True})
result={'status':'TRANSFER_RECONSTRUCTION_VERIFIED_HOST_ONLY','firmware':rows,'archive_entries':len(files),'board_accessed':False,'installed':False}
(R/'TRANSFER_VALIDATION.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
