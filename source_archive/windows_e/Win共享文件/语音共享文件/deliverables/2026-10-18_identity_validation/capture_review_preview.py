"""Legacy full-view diagnosis. Disabled by the user's face-only preference."""
raise SystemExit('Full-frame photo export disabled: use prepare_photo_review.py for a face-only photo.')
import base64, json, sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
remote=r'''
import base64,hashlib,json,urllib.request
get=lambda path:json.load(urllib.request.urlopen('http://127.0.0.1:8790'+path,timeout=4))
state=get('/v1/ui/status');preview=state.get('preview');assert preview,'No live camera preview'
url='http://127.0.0.1:8790/v1/ui/preview.jpg?camera_epoch='+preview['camera_epoch']+'&frame_id='+str(preview['frame_id'])
raw=urllib.request.urlopen(url,timeout=4).read(262145);assert len(raw)<=262144
identity=state['modules'].get('identity',{})
print(json.dumps({'status':'PREVIEW_ONLY_NOT_REGISTERED','preview':preview,
 'people_count':state['modules']['vision'].get('people_count'),
 'target':state['modules']['target'].get('selected'),'identity_state':identity.get('state'),
 'identity_detail':identity.get('detail') if identity.get('state')!='KNOWN' else 'KNOWN_NAME_REDACTED',
 'image_sha256':hashlib.sha256(raw).hexdigest(),'image_base64':base64.b64encode(raw).decode(),
 'database_modified':False,'templates_exported':False}))
'''
result=json.loads(ssh('python3 -B -',remote,timeout=15))
out=HERE/'enrollment_review';out.mkdir(exist_ok=True)
(out/'current_preview.jpg').write_bytes(base64.b64decode(result.pop('image_base64'),validate=True))
(out/'current_preview.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=True))
