"""Record authoritative release assets without downloading or executing models."""
import json
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent


def get(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'aura-audio-evaluation', 'Accept': 'application/vnd.github+json'})
    with urllib.request.urlopen(req, timeout=25) as response:
        return json.load(response)


releases = {}
for tag in ('asr-models', 'speech-enhancement-models'):
    url = 'https://api.github.com/repos/k2-fsa/sherpa-onnx/releases/tags/' + tag
    value = get(url)
    selected = []
    for a in value['assets']:
        if a['name'] in ('silero_vad.onnx', 'silero_vad.int8.onnx', 'silero_vad_v5.onnx',
                         'gtcrn_simple.onnx', 'speech_with_noise.wav', 'inp_16k.wav'):
            selected.append({k:a.get(k) for k in ('id', 'name', 'size', 'digest', 'updated_at', 'browser_download_url')})
    releases[tag] = {'source': url, 'release_id': value['id'], 'assets': selected}
for repo in ('snakers4/silero-vad', 'k2-fsa/sherpa-onnx', 'Xiaobin-Rong/gtcrn'):
    url = 'https://api.github.com/repos/' + repo + '/commits/HEAD'
    value = get(url)
    releases[repo] = {'commit': value['sha'], 'source': url}
(HERE / 'upstream_metadata.json').write_text(json.dumps(releases, indent=2) + '\n', encoding='utf-8')
print(json.dumps(releases, indent=2))
