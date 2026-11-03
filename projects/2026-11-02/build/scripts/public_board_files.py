"""Verify the public KV260 inputs in the archive or in an offline rootfs."""
import hashlib
import importlib.util
import io
import wave
import json
from pathlib import Path


def verify_public_files(root, staged=None):
    def load(path):
        return json.loads(path.read_text(encoding='utf-8-sig'))

    def need(value, message):
        if not value:
            raise ValueError(message)

    def resolve(source, destination):
        if staged is None:
            return root / source
        return staged / destination.lstrip('/')

    meta = load(root / 'board/config/public_board_resources.json')
    plan = {row['destination']: row['source'] for row in load(root / 'board/config/deployment_files.json')}
    files = meta['files']
    for destination, row in files.items():
        need(destination.startswith('/') and '..' not in Path(destination).parts, 'Invalid board path')
        need(plan.get(destination) == row['source'], 'Deployment source differs: ' + destination)
        actual = resolve(row['source'], destination)
        need(actual.is_file() and actual.stat().st_size == row['bytes'], 'Missing public file: ' + destination)
        need(hashlib.sha256(actual.read_bytes()).hexdigest() == row['sha256'], 'Public file differs: ' + destination)
    for destination, digest in load(root / 'board/config/image_inputs.json')['files'].items():
        need(files[destination]['sha256'] == digest, 'Historical board pin differs: ' + destination)
    checked = {path for rule in meta['camera_prestart'] for path in rule['paths']}
    need(checked <= files.keys() and len(checked) == meta['camera_prestart_unique_paths'], 'Camera prestart inputs incomplete')
    for service, sequence in meta['systemd_order'].items():
        prefix = '/etc/systemd/system/' + service
        need(prefix in files and all(p.startswith(prefix + '.d/') and p in files for p in sequence), 'Unit override missing: ' + service)

    gui = meta['gui_file']
    gui_file = resolve(gui['source'], gui['destination'])
    need(hashlib.sha256(gui_file.read_bytes()).hexdigest() == gui['sha256'], 'GUI configuration differs')
    config = load(gui_file)
    fixed = load(root / 'data/reference/public_feedback.json')
    binding = {'path': fixed['manifest'], 'sha256': fixed['manifest_sha256']}
    need(config['formal_static_cues'] == binding, 'GUI cue binding differs')
    business = config['board_business']
    need((business['feedback_manifest'], business['feedback_manifest_sha256']) == (binding['path'], binding['sha256']), 'Business cue binding differs')
    manifest = files[binding['path']]
    need(manifest['sha256'] == binding['sha256'], 'Cue manifest pin differs')
    assets = load(resolve(manifest['source'], binding['path']))['assets']
    expected = {a['name']: a for a in fixed['assets']}
    need(set(assets) == set(expected) == {'arrival', 'invitation', 'thinking'}, 'Missing fixed prompt')
    # Run the same PCM and metadata validation used by the released audio provider.
    spec = importlib.util.spec_from_file_location('auar_public_voice_wire', root / 'src/software/common/voice_wire.py')
    wire = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(wire)
    for name, item in assets.items():
        ref = expected[name]
        target = item['path']
        need(target == ref['path'] and files[target]['sha256'] == ref['sha256'], 'Wrong cue identity: ' + name)
        blob = resolve(files[target]['source'], target).read_bytes()
        result = wire.wav_payload(item['metadata'], blob)
        with wave.open(io.BytesIO(blob), 'rb') as wav:
            need(result['reply_text'] == ref['text'] and wav.getnframes() == ref['samples'], 'Wrong cue text or sample count: ' + name)
    print('Public KV260 files verified: {} destinations, {} camera prestart checks, 3 original fixed WAVs'.format(len(files), len(meta['camera_prestart'])))
