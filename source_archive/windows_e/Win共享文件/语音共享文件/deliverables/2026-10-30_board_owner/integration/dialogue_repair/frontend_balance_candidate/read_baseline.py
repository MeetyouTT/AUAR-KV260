"""Root-owned read-only capture of pinned public source; no business data."""
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[4]
sys.path.insert(0, str(PROJECT / 'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh

REMOTE = r'''
import hashlib,json,pathlib
root=pathlib.Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
raw=(root/'startup/config.json').read_bytes()
pin=hashlib.sha256(raw).hexdigest()
assert pin=='1129a2a7af2b401537710d1a67651c79961c1b10198f5625ae6802e7ac99fd77','baseline_changed'
cfg=json.loads(raw)
names=['tools/production_frontend_selection.py','tools/production_board_business_gui.py',
 'board/runtime/audio/board_frontend_process.py','board/runtime/audio/board_frontend_auto.py',
 'board/runtime/audio/board_gtcrn_reuse.py','board/runtime/audio/board_gtcrn_fft.py',
 'board/runtime/audio/board_asr_frontend.py','board/runtime/audio/board_capture.py',
 'board/runtime/audio/automatic_capture.py']
sources={}
for rel in names:
 if rel not in cfg['component_sha256']:continue
 data=(root/'runtime/aura'/rel).read_bytes()
 assert hashlib.sha256(data).hexdigest()==cfg['component_sha256'][rel]
 sources[rel]=data.decode('utf-8')
gui_raw=(root/'runtime/aura/config/board_avatar_gtk.json').read_bytes()
assert hashlib.sha256(gui_raw).hexdigest()==cfg['component_sha256']['config/board_avatar_gtk.json']
gui=json.loads(gui_raw)
options={key:gui['board_business'].get(key) for key in
 ['frontend_process','frontend_capture_process','frontend_optimization','frontend_threads','capture_priority_nice','asr_threads']}
print(json.dumps(dict(startup_sha256=pin,component_sha256=cfg['component_sha256'],
 source_manifest_sha256=hashlib.sha256((root/'production_source_manifest.json').read_bytes()).hexdigest(),
 business_options=options,resource_directories={key:gui['board_business'].get(key) for key in
 ['frontend_directory','asr_directory']},
 boot_id=pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip(),sources=sources)))
'''

if __name__ == '__main__':
    value = json.loads(ssh('python3 -B -', REMOTE, timeout=30))
    sources = value.pop('sources')
    value['public_source_copies'] = {}
    for rel, body in sources.items():
        raw = body.encode('utf-8')
        assert hashlib.sha256(raw).hexdigest() == value['component_sha256'][rel]
        dest = HERE / 'before' / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(raw)
        value['public_source_copies'][rel] = dict(bytes=len(raw), sha256=value['component_sha256'][rel])
    (HERE / 'baseline_manifest.json').write_text(json.dumps(value, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(startup_sha256=value['startup_sha256'], boot_id=value['boot_id'],
                         options=value['business_options'], public_sources=len(sources))))
