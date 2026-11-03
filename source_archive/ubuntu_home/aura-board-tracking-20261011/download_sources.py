"""Download only pinned ByteTrack tracker sources and MIT license."""
import hashlib
import json
from pathlib import Path
import urllib.request

root = Path(__file__).resolve().parent
headers = {'User-Agent': 'AURA-ByteTrack-source-review', 'Accept': 'application/vnd.github+json'}
request = urllib.request.Request('https://api.github.com/repos/FoundationVision/ByteTrack/commits/main', headers=headers)
with urllib.request.urlopen(request, timeout=30) as response:
    commit = json.load(response)['sha']
files = ['yolox/tracker/byte_tracker.py', 'yolox/tracker/kalman_filter.py',
         'yolox/tracker/basetrack.py', 'yolox/tracker/matching.py', 'LICENSE']
manifest = {'repository': 'https://github.com/FoundationVision/ByteTrack', 'commit': commit, 'files': {}}
for name in files:
    url = 'https://raw.githubusercontent.com/FoundationVision/ByteTrack/' + commit + '/' + name
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as response:
        blob = response.read()
    path = root / 'upstream' / name
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        assert path.read_bytes() == blob
    else:
        path.write_bytes(blob)
    manifest['files'][name] = {'bytes': len(blob), 'sha256': hashlib.sha256(blob).hexdigest(), 'url': url}
(root / 'upstream_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
print(json.dumps(manifest, indent=2))
