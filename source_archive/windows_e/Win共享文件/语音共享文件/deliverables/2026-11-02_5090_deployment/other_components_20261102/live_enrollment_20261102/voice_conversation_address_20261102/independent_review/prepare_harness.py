"""Derive a test-only harness; product source bytes remain untouched."""
import hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
RUNTIME=ROOT/'candidate_runtime'
OLD=ROOT.parent/'voice_threshold_035_production_entry_20261102'/'independent_review'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
expected={
 'board/runtime/board_speaker_business.py':'9a82616aebbc79f0235d7ee1bef0a77effaeb891546587f0f1e7982e8ea7ceb1',
 'board/runtime/board_business.py':'9c6da51f569d19d71dd2b25f8e2c4549bfa5c5059f1e7bc45d1124807400b5b2',
 'board/runtime/board_dialogue.py':'f5998983494b028850688eb06528d4088c86b41b29742bbea9aed390b4e9ee7c',
 'board/runtime/board_memory_policy.py':'87964292e231c0b1c5989542b2dcc6e3bf34f97d76c8455b517a80c3a4f4dcfe',
}
assert all(sha(RUNTIME/n)==pin for n,pin in expected.items()),'Candidate changed; obtain its new explicit pins before rerunning.'
source=(OLD/'base_composition.py').read_text(encoding='utf-8')
start=source.index('RELEASE=');end=source.index('\nsys.path.insert',start)
source=source[:start]+'RELEASE=Path('+repr(str(RUNTIME))+')'+source[end:]
pins=json.loads((OLD/'LOADED_SOURCE_PINS.json').read_text(encoding='utf-8'))
pins.update(expected)
start=source.index('PINS=');end=source.index('class Mono:')
source=source[:start]+'PINS='+repr(pins)+"\nassert all(hashlib.sha256((RELEASE/name).read_bytes()).hexdigest()==pin for name,pin in PINS.items())\n\n"+source[end:]
source=source.replace('def __init__(self):self.calls=[]','def __init__(self):self.calls=[];self.requests=[]')
source=source.replace('        self.calls.append(kind)','        self.calls.append(kind);self.requests.append((kind,copy.deepcopy(payload)))')
source=source.replace('def say(self,text,*,seed=None):','def say(self,text,*,seed=None,pcm=None):')
source=source.replace("raw=struct.pack('<h',1000+(self.counter if seed is None else seed))*48000","raw=pcm if pcm is not None else struct.pack('<h',1000+(self.counter if seed is None else seed))*48000")
source=source.replace("audio=SimpleNamespace(sample_count=48000))","audio=SimpleNamespace(sample_count=len(raw)//2))")
(HERE/'base_composition.py').write_text(source,encoding='utf-8')
(HERE/'LOADED_SOURCE_PINS.json').write_text(json.dumps(pins,indent=2)+'\n',encoding='utf-8')
(HERE/'yuki_pair.formal.public.json').write_bytes((OLD/'yuki_pair.formal.public.json').read_bytes())
original=ROOT.parent/'voice_self_match_lifecycle_review_20261102'
(HERE/'recording_helpers.py').write_bytes((original/'test_recording_integration.py').read_bytes())
print('Pinned real Production attach + Runtime/formal pair/Yuki/worker harness generated.')
