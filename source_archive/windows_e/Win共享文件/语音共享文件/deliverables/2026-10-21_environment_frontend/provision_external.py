"""Provision only small official audio assets into an external evaluation folder."""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import urllib.request

HERE = Path(__file__).resolve().parent
EXTERNAL = Path('D:/AIModels/audio-frontend-eval-20261021')
assert not EXTERNAL.resolve().is_relative_to(HERE.parents[2].resolve())
meta = json.loads((HERE / 'upstream_metadata.json').read_text(encoding='utf-8'))
assets = [a for tag in ('asr-models', 'speech-enhancement-models') for a in meta[tag]['assets']
          if a['name'] in ('silero_vad.int8.onnx', 'silero_vad.onnx', 'silero_vad_v5.onnx', 'gtcrn_simple.onnx',
                           'speech_with_noise.wav', 'inp_16k.wav')]
for repo, name in [('snakers4/silero-vad', 'SILERO_LICENSE'),
                   ('k2-fsa/sherpa-onnx', 'SHERPA_LICENSE'), ('Xiaobin-Rong/gtcrn', 'GTCRN_LICENSE')]:
    assets.append({'name': name, 'browser_download_url':
                   f'https://raw.githubusercontent.com/{repo}/{meta[repo]["commit"]}/LICENSE',
                   'size': None, 'digest': None, 'revision': meta[repo]['commit']})


def provision(asset):
    target = EXTERNAL / asset['name']
    if target.exists():
        data = target.read_bytes()
    else:
        req = urllib.request.Request(asset['browser_download_url'], headers={'User-Agent': 'aura-audio-evaluation'})
        with urllib.request.urlopen(req, timeout=35) as response:
            data = response.read(4*1024*1024 + 1)
        if len(data) > 4*1024*1024:
            raise ValueError('Asset exceeds small-audio-artifact budget')
    if asset['size'] is not None and len(data) != asset['size']:
        raise ValueError('Asset length mismatch: ' + asset['name'])
    digest = hashlib.sha256(data).hexdigest()
    if asset['digest'] and asset['digest'] != 'sha256:' + digest:
        raise ValueError('Official release digest mismatch: ' + asset['name'])
    EXTERNAL.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        target.write_bytes(data)
    return {**asset, 'path': str(target), 'bytes': len(data), 'sha256': digest,
            'official_digest_verified': bool(asset['digest']),
            'provenance': 'Official release asset ID/URL; local SHA256 only when upstream publishes no digest.'}


with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    records = list(pool.map(provision, assets))
manifest = {'date': '2026-10-21', 'external_root': str(EXTERNAL), 'assets': records,
            'new_dependencies_installed': False, 'production_changed': False,
            'llm_weights_included': False}
for path in (HERE / 'asset_manifest.json', EXTERNAL / 'asset_manifest.json'):
    path.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'external_root': str(EXTERNAL), 'assets': len(records),
                  'total_bytes': sum(r['bytes'] for r in records),
                  'official_digest_verified': [r['name'] for r in records if r['official_digest_verified']]}))
