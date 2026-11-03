"""Repeat the same cost gate using the exact recovery candidate service."""
import ast,hashlib,json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parent
old=Path('/home/ghmd/aura-gap3-validation-20261023')
target=Path('/home/ghmd/aura-recovery-validation-20261023')
candidate=Path('/home/ghmd/aura-yunet-recovery-20261023')
assert not target.exists()
shutil.copytree(old,target,ignore=shutil.ignore_patterns('evidence','__pycache__'))
relative='candidate/aura/board/identity/face_targets.py'
(target/relative).write_bytes((candidate/relative).read_bytes())
prepare=target/'prepare_sources.py';text=prepare.read_text()
tree=ast.parse(text)
pins=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign)
          and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='PINS')
pins={name:hashlib.sha256((target/name).read_bytes()).hexdigest() for name in pins}
start=text.index('PINS = ');end=text.index('\nEXPECTED_TESTS',start)
text=text[:start]+'PINS = '+repr(pins)+text[end:]
text=text.replace('aura-yunet-retry-gap-audit-20261023','aura-yunet-recovery-20261023')
prepare.write_text(text)
builder=(ROOT/'build_gap3_preflight.py').read_text()
builder=builder.replace('aura-gap3-validation-20261023','aura-recovery-validation-20261023')
builder=builder.replace('gap3-preflight','recovery-preflight')
builder=builder.replace('board_gap3_preflight_20261023.py','board_recovery_preflight_20261023.py')
exec(compile(builder,str(__file__),'exec'),{'__file__':str(__file__),'__name__':'__main__'})
