"""Merged candidates, real read-only assets; no model construction on import."""
import importlib,sys,types
from pathlib import Path
H=Path(__file__).resolve().parent;A=H.parents[1]/'aura'
G=H.parent/'2026-10-29_gpu_coordination';S=H.parent/'2026-10-29_speaker_visual_cooperation'
sys.path[:0]=[str(A),r'C:\Users\35870\.codex\visualizations\2026\10\26\01a1772c-f263-75f1-bfa1-9bd865e5caa9\animation-fps-deps']
for name in ('common','tools','board.runtime.audio'):
    package=importlib.import_module(name);relative=name.replace('.','/')
    package.__path__=[str(H/'candidate/windows'/relative),str(G/'candidate'/relative),str(S/'candidate'/relative),str(A/relative)]
def service_module():
    name='tools.board_model_host';path=H/'candidate/windows/tools/board_model_host.py'
    module=types.ModuleType(name);module.__package__='tools';module.__file__=str(A/'tools/board_model_host.py')
    sys.modules[name]=module
    exec(compile(path.read_text(encoding='utf-8'),str(path),'exec'),module.__dict__)
    setattr(sys.modules['tools'],'board_model_host',module)
    return module
