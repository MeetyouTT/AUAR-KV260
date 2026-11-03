import sys,json,time,cProfile,pstats,io
from pathlib import Path
root=Path('/home/root/aura-speech-motion-20261021/0e98f7830e27/runtime');sys.path.insert(0,str(root/'aura'))
from tools.demo_script import create_demo_core
from tools.realtime_facials import RealtimeFacials
from tools.native_pixels import NativePixels
core=create_demo_core('reuse');pixels=NativePixels(root/'aura/tools/libaura_pixels.so',threads=3);pixels.configure(core)
f=RealtimeFacials(core);p=cProfile.Profile();p.enable()
for i in range(24):
 t=i*.125+.01;meta=core.frame_at('SPEAKING_NEUTRAL',t);f.apply(meta,t,.8,.7)
p.disable();stream=io.StringIO();pstats.Stats(p,stream=stream).sort_stats('cumtime').print_stats(23)
print(json.dumps({'profile':stream.getvalue()}));pixels.close()
