"""Overlay candidate modules without copying runtime resources or credentials."""
import importlib,sys,types
from pathlib import Path
HERE=Path(__file__).resolve().parent;AURA=HERE.parents[1]/'aura'
sys.path[:0]=[str(AURA),r'C:\Users\35870\.codex\visualizations\2026\10\26\01a1772c-f263-75f1-bfa1-9bd865e5caa9\animation-fps-deps']
for name in ('tools','common','board','board.runtime','board.runtime.audio'):
    package=importlib.import_module(name)
    relative=name.replace('.','/')
    package.__path__=[str(HERE/'candidate_source'/relative),str(AURA/relative)]
# This service uses __file__ to find existing small configuration; load its
# candidate code with the real config root, not a copied configuration tree.
def service_module():
    name='tools.board_model_host';p=HERE/'candidate_source/tools/board_model_host.py'
    module=types.ModuleType(name);module.__file__=str(AURA/'tools/board_model_host.py');module.__package__='tools'
    sys.modules[name]=module
    exec(compile(p.read_text(encoding='utf-8'),str(p),'exec'),module.__dict__)
    return module

