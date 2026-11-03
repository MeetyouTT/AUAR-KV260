"""Identity inventory aggregates only: no names, IDs, embeddings, keys or images."""
import ast
import copy
import datetime
import hashlib
import json
from pathlib import Path
import sqlite3
import time

ROOT = Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
startup_raw = (ROOT / 'startup/config.json').read_bytes()
startup = json.loads(startup_raw)
aura = Path(startup['runtime']) / 'aura'
ui_path = aura / 'config/board_avatar_gtk.json'
ui_raw = ui_path.read_bytes()
assert hashlib.sha256(ui_raw).hexdigest() == startup['component_sha256']['config/board_avatar_gtk.json']
business = json.loads(ui_raw)['board_business']
assert Path(business['private_root']) == Path('/home/root/.local/share/aura-board-business')
spec = business['face_readback']
selected_raw = Path(spec['path']).read_bytes()
assert hashlib.sha256(selected_raw).hexdigest() == spec['sha256']
selected = json.loads(selected_raw)
verifier = aura / 'board/runtime/audio/face_gallery_readback.py'
source = verifier.read_bytes()
assert hashlib.sha256(source).hexdigest() == 'b77c32b3863b9464006ac1bb7f16c8f767113925d9142d77e4755f1ce365527e'
tree = ast.parse(source)
klass = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'FaceGalleryReadback')
method = copy.deepcopy(next(node for node in klass.body if isinstance(node, ast.FunctionDef) and node.name == '_verify'))
method.decorator_list = []
space = {'Path': Path, 'hashlib': hashlib, 'json': json}
exec(compile(ast.Module(body=[method], type_ignores=[]), str(verifier) + '::<readonly-source-verifier>', 'exec'), space)
space['_verify'](selected)

speaker_root = Path(business['private_root']) / 'speaker'
namespace_path = speaker_root / 'speaker-gallery-namespace.json'
assert namespace_path.is_file() and not namespace_path.is_symlink()
namespace = json.loads(namespace_path.read_bytes())
voice_model = namespace['model_id']
assert type(voice_model) is str and voice_model.startswith('ecapa-voxceleb-')

observed = {}

def aggregate(label, path, queries, expected_application_id=None):
    path = Path(path)
    assert path.is_file() and not path.is_symlink() and path.resolve() == path
    before = path.stat()
    assert before.st_size <= 128 * 1024 * 1024
    db = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=1, isolation_level=None)
    deadline = time.monotonic() + 2
    db.set_progress_handler(lambda: int(time.monotonic() > deadline), 1000)
    try:
        db.execute('PRAGMA query_only=ON')
        assert db.execute('PRAGMA query_only').fetchone() == (1,)
        if expected_application_id is not None:
            assert db.execute('PRAGMA application_id').fetchone() == (expected_application_id,)
        db.execute('BEGIN')
        values = {}
        for key, (query, parameters) in queries.items():
            assert query.startswith('SELECT COUNT(')
            result = db.execute(query, parameters).fetchone()
            assert len(result) == 1 and type(result[0]) is int and result[0] >= 0
            values[key] = result[0]
        db.execute('ROLLBACK')
    finally:
        db.close()
    after = path.stat()
    values['file_changed_during_read'] = (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns)
    observed[label] = values

aggregate('face', selected['database'], {
    'registered_identities_all_models': ('SELECT COUNT(*) FROM identities', ()),
    'identities_with_current_model_template': ('SELECT COUNT(DISTINCT i.id) FROM identities i JOIN templates t ON i.id=t.identity_id WHERE t.model_id=? AND t.dimension=?', (selected['model_id'], selected['dimension'])),
    'templates_for_current_model': ('SELECT COUNT(*) FROM templates WHERE model_id=? AND dimension=?', (selected['model_id'], selected['dimension'])),
})
aggregate('voice', speaker_root / 'speakers.sqlite3', {
    'registered_identities_all_models': ('SELECT COUNT(*) FROM identities', ()),
    'identities_with_current_model_template': ('SELECT COUNT(DISTINCT i.id) FROM identities i JOIN templates t ON i.id=t.identity_id WHERE t.model_id=?', (voice_model,)),
    'templates_for_current_model': ('SELECT COUNT(*) FROM templates WHERE model_id=?', (voice_model,)),
}, 0x41555350)
aggregate('stored_links', speaker_root / 'identity-links.sqlite3', {
    'linked_people_total': ('SELECT COUNT(*) FROM linked_people', ()),
    'active_linked_people': ("SELECT COUNT(*) FROM linked_people WHERE state='ACTIVE'", ()),
    'active_face_links': ("SELECT COUNT(*) FROM modality_links WHERE state='ACTIVE' AND modality='face'", ()),
    'active_voice_links': ("SELECT COUNT(*) FROM modality_links WHERE state='ACTIVE' AND modality='voice'", ()),
    'people_with_both_stored_active_links': ("SELECT COUNT(*) FROM linked_people p WHERE p.state='ACTIVE' AND EXISTS (SELECT 1 FROM modality_links f WHERE f.person_id=p.person_id AND f.modality='face' AND f.state='ACTIVE') AND EXISTS (SELECT 1 FROM modality_links v WHERE v.person_id=p.person_id AND v.modality='voice' AND v.state='ACTIVE')", ()),
    'binding_attempts_recorded_active': ("SELECT COUNT(*) FROM binding_attempts WHERE state='ACTIVE'", ()),
}, 0x41554C4B)

assert Path(spec['path']).read_bytes() == selected_raw
space['_verify'](selected)
print(json.dumps({'schema': 'aura-identity-inventory-counts-readonly-1',
                  'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                  'startup_sha256': hashlib.sha256(startup_raw).hexdigest(),
                  'startup_changed_during_observation': (ROOT / 'startup/config.json').read_bytes() != startup_raw,
                  'counts': observed, 'face_current_model_source_verified': True,
                  'read_only': True, 'names_ids_templates_embeddings_keys_audio_images_exported': False,
                  'project_store_or_model_or_service_constructed': False,
                  'axis_or_main_page_read_or_changed': False,
                  'scope': 'Stored inventory counts, not identity accuracy or authorization acceptance'}, sort_keys=True))
