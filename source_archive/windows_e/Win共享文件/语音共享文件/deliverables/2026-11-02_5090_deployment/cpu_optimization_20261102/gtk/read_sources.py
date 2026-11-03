"""Read pinned UI source only. No frame, conversation, or database content."""
import base64
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[1]
helper = OUT.parent/'2026-10-18_board_dialogue/board_ssh.py'
assert hashlib.sha256(helper.read_bytes()).hexdigest() == '6aefec94f620c6c86fa6b17c83613b22c8599e899cb2c2fcaf36c9cdd17c7373'
spec = importlib.util.spec_from_file_location('gtk_read_transport',helper)
transport = importlib.util.module_from_spec(spec);spec.loader.exec_module(transport)
code = '''import base64,hashlib,json,time
from pathlib import Path
business=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
startup_raw=(business/'startup/config.json').read_bytes()
startup=json.loads(startup_raw);aura=Path(startup['runtime'])/'aura'
pins=startup['component_sha256'];assert len(pins)==380
names=('tools/board_camera_preview.py','tools/board_avatar_gtk.py','tools/board_avatar_pan.py','tools/board_ui_services.py','tools/production_memory_presentation.py','config/board_ui_services.json','config/board_avatar_gtk.json')
files={}
for name in names:
    if name not in pins:continue
    path=aura/name;assert path.is_file() and not path.is_symlink() and path.stat().st_size<2000000
    raw=path.read_bytes();digest=hashlib.sha256(raw).hexdigest();assert digest==pins[name]
    files[name]={'sha256':digest,'data':base64.b64encode(raw).decode()}
assert (business/'startup/config.json').read_bytes()==startup_raw
print(json.dumps({'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'startup_sha256':hashlib.sha256(startup_raw).hexdigest(),'runtime_aura':str(aura),'component_count':len(pins),'preview_source_keys':[k for k in pins if any(w in k for w in ('preview','camera','video','ui_services','projection'))],'files':files,'board_written':False,'project_imported':False}))
'''
data=json.loads(transport.ssh('/usr/bin/python3 -B -I -S -',code,timeout=20))
meta={k:v for k,v in data.items() if k!='files'};meta['read_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();meta['source_sha256']={}
for name,value in data['files'].items():
    target=HERE/'original'/name;target.parent.mkdir(parents=True,exist_ok=True)
    raw=base64.b64decode(value['data']);assert hashlib.sha256(raw).hexdigest()==value['sha256']
    with target.open('xb') as stream:stream.write(raw)
    meta['source_sha256'][name]=value['sha256']
with (HERE/'SOURCE_SNAPSHOT.json').open('x',encoding='utf-8') as stream:json.dump(meta,stream,indent=2)
print(json.dumps(meta))
