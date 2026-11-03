"""Local-only helper. Never modifies either candidate or baseline products."""
import hashlib,json,os
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
RUNTIME=Path(os.environ.get('AURA_ENTRY_RUNTIME',str(ROOT/'candidate_runtime')))
EXPECTED_PRODUCTION=os.environ['AURA_PRODUCTION_GUI_SHA']
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
pins={
 'board/runtime/board_speaker_business.py':'e229b6c3c64e75373e74d5fa136b633174ddf9897f6e95bc368899de9dc2c3d7',
 'tools/provisional_voice.py':'1ac360902f2b5790cb0b047110ef0d267940031caaaf20b91ec75c7fef1ab47c',
 'tools/yuki_business_gui.py':'6f04e9f8d7a87a8741f41f321f1c51478236be0b1cec7db7983c7b23f63764fd',
 'tools/production_board_business_gui.py':EXPECTED_PRODUCTION,
}
old=ROOT.parent/'voice_threshold_035_20261102'/'independent_review'
source=(old/'base_composition.py').read_text(encoding='utf-8')
source=source.replace("RELEASE=HERE.parent/'candidate_runtime'",'RELEASE=Path('+repr(str(RUNTIME))+')')
start=source.index('PINS=');end=source.index('class Mono:')
for name in ('tools/board_avatar_gtk.py','tools/formal_yuki.py','tools/board_business_gui.py',
 'common/feature_intents.py','board/runtime/board_business.py','tools/yuki_jobs_candidate.py',
 'tools/board_recording.py','tools/production_memory_presentation.py','board/runtime/history_delete.py',
 'common/anonymous_voice.py','tools/speaker_device.py','board/identity/store.py'):
    pins[name]=sha(RUNTIME/name)
assert all(sha(RUNTIME/name)==pin for name,pin in pins.items())
source=source[:start]+'PINS='+repr(pins)+"\nassert all(hashlib.sha256((RELEASE/name).read_bytes()).hexdigest()==pin for name,pin in PINS.items())\n\n"+source[end:]
source=source.replace('from tools import yuki_business_gui','from tools import production_board_business_gui')
source=source.replace("yuki_business_gui,'load_private_face_readback'","production_board_business_gui,'load_private_face_readback'")
source=source.replace('yuki_business_gui.CandidateGuiBoardBusiness','production_board_business_gui.ProductionGuiBoardBusiness')
source=source.replace("=='CandidateGuiBoardBusiness'","=='ProductionGuiBoardBusiness'")
source=source.replace('The SELECTED production subclass _attach_speaker and real worker run.','The actual production override _attach_speaker and real worker run.')
(HERE/'base_composition.py').write_text(source,encoding='utf-8')
(HERE/'yuki_pair.formal.public.json').write_bytes((old/'yuki_pair.formal.public.json').read_bytes())
(HERE/'LOADED_SOURCE_PINS.json').write_text(json.dumps(pins,indent=2)+'\n',encoding='utf-8')
print('Exact ProductionGuiBoardBusiness override harness prepared; IO remains synthetic.')
