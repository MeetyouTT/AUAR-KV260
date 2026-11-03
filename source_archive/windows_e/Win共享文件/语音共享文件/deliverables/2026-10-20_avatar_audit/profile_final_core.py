import sys,json,cProfile,pstats,io
from pathlib import Path
root=Path('/home/root/aura-avatar-performance-20261020/candidate-29e4697868be/runtime');sys.path.insert(0,str(root/'aura'))
from tools.board_avatar_gtk import create_runtime_core
from tools.demo_script import create_demo_core
from tools.realtime_facials import RealtimeFacials
from tools.board_avatar_affine import configure_board_rendering
core=create_runtime_core(create_demo_core);facials=RealtimeFacials(core);configure_board_rendering(core)
for i in range(5):facials.apply(core.frame_at('IDLE',100+i/30),100+i/30,0,0)
profile=cProfile.Profile();profile.enable()
for i in range(24):facials.apply(core.frame_at('IDLE',101+i/30),101+i/30,0,0)
profile.disable();out=io.StringIO();pstats.Stats(profile,stream=out).sort_stats('cumulative').print_stats(28)
print(json.dumps({'profile':out.getvalue()}))
