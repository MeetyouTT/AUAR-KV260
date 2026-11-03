import datetime
import hashlib
import http.client
import json
from pathlib import Path

BUSINESS=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
AURA=BUSINESS/'runtime/aura'
STARTUP=BUSINESS/'startup/config.json'
FACE=AURA/'config/pan_face.local.json'
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def identity(pid):
    p=Path('/proc')/str(pid)
    if not p.exists(): return {'pid':pid,'alive':False}
    return dict(pid=pid,alive=True,birth=p.joinpath('stat').read_text().rsplit(')',1)[1].split()[19],
                cmd_sha256=sha(p/'cmdline'))
def get(port,path):
    c=http.client.HTTPConnection('127.0.0.1',port,timeout=4)
    try:
        c.request('GET',path);r=c.getresponse();data=r.read(2097153)
        assert r.status==200 and len(data)<=2097152
        return json.loads(data)
    finally:c.close()
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
startup=json.loads(STARTUP.read_bytes());pins=startup['component_sha256']
face=json.loads(FACE.read_bytes());root=Path(face['release_root'])
manifest=json.loads((root/'deployment-manifest.json').read_bytes())
bad_components=[key for key,value in pins.items() if sha(AURA/key)!=value]
bad_sources=[]
for item in manifest['files']:
    p=Path(item['destination']);relative=p.relative_to(root)
    assert '..' not in relative.parts and not p.is_symlink()
    if sha(p)!=item['sha256'] or p.stat().st_size!=item['bytes']:bad_sources.append(str(relative))
state=get(8783,'/api/state');pan=state['manual_pan']
camera=get(8790,'/health')
zone=Path(face['arguments']['zone-settings'])
out=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),boot_id=boot,
         fdt_sha256=sha('/sys/firmware/fdt'),startup_sha256=sha(STARTUP),
         face_config_sha256=sha(FACE),face_config=face,zone_sha256=sha(zone),zone=json.loads(zone.read_bytes()),
         controller_manifest_sha256=sha(root/'deployment-manifest.json'),
         manifest_pin_matches=sha(root/'deployment-manifest.json')==face['manifest_sha256'],
         component_count=len(pins),bad_components=bad_components,source_count=len(manifest['files']),bad_sources=bad_sources,
         processes=[identity(pid) for pid in (97308,97312,79866)],
         camera_pid=camera.get('pid'),camera_health_status=camera.get('status'),camera_health_keys=sorted(camera),
         manual_pan=pan)
print(json.dumps(out))
