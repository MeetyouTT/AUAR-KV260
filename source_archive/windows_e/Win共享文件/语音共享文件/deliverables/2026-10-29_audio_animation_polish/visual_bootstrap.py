"""Execute exact CPU-renderer snapshot modules with actual read-only asset paths."""
import bootstrap
import importlib,sys,types
from pathlib import Path
H=Path(__file__).resolve().parent;A=H.parents[1]/'aura'
def load(name,path,relative):
 importlib.import_module(name.rsplit('.',1)[0])
 module=types.ModuleType(name);module.__package__=name.rsplit('.',1)[0];module.__file__=str(A/relative)
 sys.modules[name]=module;exec(compile(path.read_text(encoding='utf-8'),str(path),'exec'),module.__dict__)
 parent_name,child=name.rsplit('.',1);setattr(sys.modules[parent_name],child,module)
 return module
snapshot=H/'candidate/renderer_snapshot'
for relative in ('board/runtime/fsm.py','board/interaction/avatar_player.py','tools/facial_layers.py','tools/demo_script.py'):
 load(relative[:-3].replace('/','.'),snapshot/relative,relative)
for relative in ('tools/idle_body_compositor.py','tools/realtime_facials.py'):
 load(relative[:-3].replace('/','.'),H/'candidate/shared'/relative,relative)
