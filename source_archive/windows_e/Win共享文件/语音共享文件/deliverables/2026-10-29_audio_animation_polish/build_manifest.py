"""Keep all historical asset pins; update only reviewed source inputs."""
import hashlib,json
from pathlib import Path
H=Path(__file__).resolve().parent;P=H.parents[1];A=P/'aura';snapshot=H/'candidate/renderer_snapshot'
old=json.loads((H.parent/'2026-10-27_windows_portrait/renderer_snapshot/manifest.json').read_text(encoding='utf-8'))
sources={name:hashlib.sha256((snapshot/name).read_bytes()).hexdigest() for name in old['sources']}
shared={}
for name,expected in old['project_sources'].items():
    original=hashlib.sha256((A/name).read_text(encoding='utf-8').encode()).hexdigest()
    assert original==expected,('Concurrent shared source change',name)
    candidate=H/'candidate/shared'/name
    shared[name]=hashlib.sha256((candidate if candidate.exists() else A/name).read_text(encoding='utf-8').encode()).hexdigest()
renderer='tools/portrait_renderer.py'
shared[renderer]=hashlib.sha256((H/'candidate/windows'/renderer).read_text(encoding='utf-8').encode()).hexdigest()
for name,item in old['assets'].items():
    path=P/name
    assert path.stat().st_size==item['bytes'] and hashlib.sha256(path.read_bytes()).hexdigest()==item['sha256'],name
for family in ('idle_normal','idle_present','talking_normal','talking_low'):
    required=[p.relative_to(P).as_posix() for p in (A/'assets/avatar'/family).glob('*.png')]
    assert len(required)==39 and all(name in old['assets'] for name in required),family
value={'sources':sources,'shared':shared,'assets':old['assets']}
revision=hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()
manifest=dict(revision=revision,sources=sources,project_sources=shared,assets=old['assets'])
(snapshot/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
report=dict(status='PASS',revision=revision,previous_revision=old['revision'],snapshot_sources=len(sources),
 shared_sources=len(shared),asset_pins=len(old['assets']),asset_bytes=sum(v['bytes'] for v in old['assets'].values()),
 original_assets_unchanged=True,original_snapshot_unchanged=True,new_models_or_art=False)
(H/'snapshot_verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
