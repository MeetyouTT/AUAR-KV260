import ast
import hashlib
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent;FIX=HERE/'py39_fix'
release=json.loads((FIX/'APPLIED.json').read_text(encoding='utf-8'))
assert release['status']=='ORIGINAL_FOLLOW_LEFT40_RIGHT45_PY39_SELECTED_STOPPED'
source=(HERE/'start_original_ui_once.py').read_text(encoding='utf-8')
for old,new in {
    'control-10282601-left40-right45-aaaa15bf':'control-10282601-left40-right45-py39-14e598cf',
    'original-follow-left40-right45-v1':'original-follow-left40-right45-v2-py39',
    '9856e25396a55ab4bf17cdcf80b3264aa756919121e19fcb17d89d985ac5097f':release['controller_manifest_sha256'],
    '73e532adad9f4769149f6c8b57844fcdc23a3d6df274902015d51323f5390453':release['startup_after_sha256'],
    "page=state.get('page')":"page=state.get('ui_page')",
    "assert side in (-1,0,1) and target==(.4 if side==-1 else .45)":
    "if side is not None:assert side in (-1,0,1) and target==(.4 if side==-1 else .45)",
}.items():
    assert source.count(old)==1,(old,source.count(old));source=source.replace(old,new,1)
ast.parse(source);p=FIX/'start_original_ui_once.py';assert not p.exists();p.write_text(source,encoding='utf-8')
print(json.dumps(dict(script_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),command='pan_face_follow',once=True)))
