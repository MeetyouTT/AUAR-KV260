"""Reproduce the complete-module equivalence and source-set checks offline."""
import ast,hashlib
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
name='tools/production_board_business_gui.py'
old,new=ROOT/'baseline_runtime'/name,ROOT/'candidate_runtime'/name
assert sha(old)=='b01f6edb9efe88cf95da60900e5ccc32eec93a24ef3f515ab08f51ae2ee6ada8'
assert sha(new)=='279ef8deb388e963e846453de71ddfe865fc05ab49e78c496321537234407168'
before,after=ast.parse(old.read_text(encoding='utf-8')),ast.parse(new.read_text(encoding='utf-8'))
found=[]
for call in ast.walk(after):
    if isinstance(call,ast.Call):
        for kw in tuple(call.keywords):
            if kw.arg=='calibration':
                found.append(ast.literal_eval(kw.value))
                call.keywords.remove(kw)
assert found==[dict(threshold=.35,margin=.1,consistency=.6,field_calibrated=False)]
assert ast.dump(before,include_attributes=False)==ast.dump(after,include_attributes=False)
line="            calibration={'threshold':.35,'margin':.1,'consistency':.6,'field_calibrated':False},\n"
assert new.read_text(encoding='utf-8').replace(line,'')==old.read_text(encoding='utf-8')
def files(root):
    return {p.relative_to(root).as_posix():sha(p) for p in root.rglob('*')
            if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
reference=ROOT.parent/'voice_threshold_035_20261102/candidate_runtime'
source,candidate=files(reference),files(ROOT/'candidate_runtime')
assert source.keys()==candidate.keys()
assert [n for n in source if source[n]!=candidate[n]]==[name]
assert len(candidate)==352
print('PASS: one added calibration keyword; whole AST/text reversible; only production GUI source differs across 352 files.')
