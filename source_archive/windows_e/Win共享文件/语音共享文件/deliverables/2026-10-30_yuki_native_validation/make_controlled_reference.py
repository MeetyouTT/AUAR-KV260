"""Explicit diagnostic PSB copy with physics/blink disabled for static geometry.

This does not change the actual animation asset or any native runtime mode.
"""
from pathlib import Path
import hashlib,json,sys
BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE/'source/tools/reference_capture'))
from psb_fixture import make_fixture
source=Path('D:/share、/项目开发/美冬本地女友项目/assets/fuyukiss/webgl/yuk_0.ems.psb')
out=BASE/'reference_controlled';out.mkdir(exist_ok=True)
data=source.read_bytes();fixture,edits=make_fixture(data,disable_physics=True,disable_auto_blink=True)
(out/'model.psb').write_bytes(fixture)
rig=json.loads(Path('D:/share、/项目开发/美冬本地女友项目/web/tachie/yuki-rig.json').read_text(encoding='utf8'))
rig['model']='/fixtures/yuki_controlled/model.psb'
(out/'controlled-rig.json').write_text(json.dumps(rig,ensure_ascii=True),encoding='utf8')
(out/'manifest.json').write_text(json.dumps(dict(source=str(source),source_sha256=hashlib.sha256(data).hexdigest(),
 fixture_sha256=hashlib.sha256(fixture).hexdigest(),edits=edits,purpose='static source geometry comparison ONLY',
 native_host_physics_disabled=False,production_asset_modified=False),indent=2),encoding='utf8')
print(json.dumps({'diagnostic_copy_bytes':len(fixture),'changed_fields':len(edits)}))
