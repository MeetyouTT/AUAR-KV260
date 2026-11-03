import ast
from pathlib import Path
HERE=Path(__file__).resolve().parent
s=(HERE/'prepare_py39_board_tests.py').read_text(encoding='utf-8')
changes={
    "FIX=HERE/'py39_fix'":"FIX=HERE/'recovery_stability_20261102_v3'",
    "files[(prefix/'test_left_episode.py').as_posix()]=(FIX/'test_left_episode.py').read_bytes()":
    "files[(prefix/'test_left_episode.py').as_posix()]=(FIX/'test_left_episode.py').read_bytes()\nfiles[(prefix/'test_rearm_stability.py').as_posix()]=(FIX/'test_rearm_stability.py').read_bytes()",
    'import test_left_episode,test_hardware_slew;buf=':'import test_left_episode,test_hardware_slew,test_rearm_stability;buf=',
    'loadTestsFromModule(test_hardware_slew)]);r=':'loadTestsFromModule(test_hardware_slew),unittest.defaultTestLoader.loadTestsFromModule(test_rearm_stability)]);r=',
}
for old,new in changes.items():
    assert s.count(old)==1,(old,s.count(old));s=s.replace(old,new,1)
ast.parse(s)
p=HERE/'prepare_rearm_board_tests.expanded.py';assert not p.exists();p.write_text(s,encoding='utf-8')
exec(compile(s,str(p),'exec'),{'__file__':str(p),'__name__':'__main__'})
