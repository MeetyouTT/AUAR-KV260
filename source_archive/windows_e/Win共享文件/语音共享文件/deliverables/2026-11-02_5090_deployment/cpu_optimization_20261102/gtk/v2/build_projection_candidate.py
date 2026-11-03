"""Add a preview-only state projection; preserve the exact original Gst graph."""
import ast
import difflib
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
names={'board/interaction/ui_services.py':'b55ee295e2cb5494f387fbaa4aa081fd1d6bffd57588c018c5f31daae56bd711',
       'tools/board_camera_preview.py':'6e697c16f7ae264dff56b6b35f38da4b531ea13026b69a7c8bdbfb1960a6afcd',
       'board/interaction/ui_contract.py':'7f67e4bdfe4a95396fbe6445759c80f8ea79cf51d2d991269213409a83daec86'}
original={}
for name,sha in names.items():
    data=(BASE/'original'/name).read_bytes();assert hashlib.sha256(data).hexdigest()==sha
    target=HERE/'original'/name;target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as stream:stream.write(data)
    original[name]=data

method='''    def read_preview(self):
        """Copy only display-source fields, under the same snapshot/connection lock.

        Ingest already validates this source. Match SnapshotGate.read's source
        expiry exactly; its cancellation mask only changes interaction fields.
        The original full read() remains the UI/action/identity API.
        """
        with self.condition:
            value = self.gate.value if self.link == 'READY' else None
            if value is None or self.clock() >= value['observed_mono_ms']+value['ttl_ms']:
                return {'snapshot': None, 'preview': None, 'raw_preview': False}
            camera = value['modules'].get('camera', {})
            snapshot = copy.deepcopy({
                'board_boot_id': value['board_boot_id'],
                'service_epoch': value['service_epoch'],
                'source_kind': value['source_kind'],
                'preview': value.get('preview'),
                'modules': {'camera': {key: camera[key] for key in ('state', 'preview_transport') if key in camera}}})
            preview = self.preview if snapshot.get('preview') == self.preview_key else None
            if preview and self.clock()-self.preview_key['captured_mono_ms'] > 1500:
                preview = None
            return {'snapshot': snapshot, 'preview': copy.deepcopy(preview),
                    'raw_preview': self.use_raw(snapshot, self.connection)}

'''
services=original['board/interaction/ui_services.py']
newline=b'\r\n' if b'\r\n' in services else b'\n'
anchor=b'    def identity_snapshot(self):'
assert services.count(anchor)==1 and b'def read_preview(' not in services
new_services=services.replace(anchor,method.replace('\n',newline.decode()).encode()+anchor)
preview=original['tools/board_camera_preview.py']
old=b"                view=self.services.read();snapshot=view['snapshot']"
new=b"                read_preview=getattr(self.services,'read_preview',None)\n                view=read_preview() if callable(read_preview) else self.services.read();snapshot=view['snapshot']"
assert preview.count(old)==1
new_preview=preview.replace(old,new)
assert b'videoconvert ! videoscale ! video/x-raw,width=' in new_preview
assert b'videoscale ! videoconvert' not in new_preview
candidate={'board/interaction/ui_services.py':new_services,'tools/board_camera_preview.py':new_preview}
manifest={'status':'CANDIDATE_READY_PURE_EQUIVALENCE_AND_PUBLIC_CPU_TEST_PENDING','change':'Preview-only projection, original Gst pipeline preserved',
    'original_sha256':{},'candidate_sha256':{},'pipeline_changed':False,'deployed':False}
for name,data in candidate.items():
    ast.parse(data.decode('utf-8'))
    path=HERE/'candidate'/name;path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as stream:stream.write(data)
    manifest['original_sha256'][name]=hashlib.sha256(original[name]).hexdigest()
    manifest['candidate_sha256'][name]=hashlib.sha256(data).hexdigest()
    diff=''.join(difflib.unified_diff(original[name].decode().splitlines(True),data.decode().splitlines(True),fromfile='original/'+name,tofile='candidate/'+name))
    (HERE/(Path(name).stem+'.diff')).write_text(diff,encoding='utf-8')
with (HERE/'CANDIDATE_MANIFEST.json').open('x',encoding='utf-8') as stream:json.dump(manifest,stream,indent=2)
print(json.dumps(manifest))
