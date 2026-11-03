"""Fresh public synthetic copies only; never changes an existing release."""
import hashlib
import json
from pathlib import Path
import shutil

HERE=Path(__file__).resolve().parent
LIVE=HERE.parent
SOURCE=LIVE/'voice_entry_trace_20261102/production_composition_review/runtime'
PINS={
 'board/runtime/board_business.py':'d034227118063dc4dbfb69f4bc735000980bd166e91262b4953f0db4b1baf5cc',
 'board/runtime/audio/board_dialogue_jobs.py':'580b2cf796275104cf15f2295afa2de29f82f32eabdd783a4b3aff858840a464',
 'common/binding_intent.py':'8048cd5bd4f3f80cd872f373e1eed149820f37d2ec40042390c17cfb4cd94df1',
 'common/feature_intents.py':'1bb807ed88a84515942cca7e0dadab92dac99e2fd39b163b2e5d20a0194d8945',
 'tools/yuki_jobs_candidate.py':'18d4bcbc6d3a32b3a2edd64103d634493e2fbd00f88ab0809fa600144d26508d',
 'board/runtime/board_speaker_business.py':'6904267bd016a10a1508b26f372f0db54a71d78eed2eb15b043026218b1b7816',
 'tools/binding_hub_runtime.py':'80b20963160242eb06fca69dd0fd5774251d1da626f5de718cefa276bd58b375',
 'tools/speaker_device.py':'da9c199527abdf9e247661d8798f4345cf0b79524f5c2a06394b5dc9c44107de',
}
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
assert all(sha(SOURCE/name)==digest for name,digest in PINS.items())
for variant in ('baseline','candidate'):
 dest=HERE/(variant+'_runtime')
 assert not dest.exists(),'Fresh review directory required'
 shutil.copytree(SOURCE,dest,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
pair=LIVE.parent.parent/'identity_dialogue_collaboration/baseline/config/yuki_pair.formal.json'
# LIVE is OUT/other_components/live_enrollment; the independent old public pair
# is OUT/identity_dialogue_collaboration/baseline, with exactly the current pin.
if not pair.exists():pair=LIVE.parents[1]/'identity_dialogue_collaboration/baseline/config/yuki_pair.formal.json'
assert sha(pair)=='998710fc12bf442d6baea501bab0234665b666caa29f4be8f685741d50d82099'
shutil.copyfile(pair,HERE/'yuki_pair.formal.public.json')
(HERE/'BASE_PINS.json').write_text(json.dumps(PINS,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(copied=True,public_pair_sha256=sha(pair))))
