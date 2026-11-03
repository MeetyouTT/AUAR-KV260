import importlib,sys,types
from pathlib import Path
HERE=Path(__file__).resolve().parent;AURA=HERE.parents[1]/'aura'
sys.path[:0]=[str(AURA),r'C:\Users\35870\.codex\visualizations\2026\10\26\01a1772c-f263-75f1-bfa1-9bd865e5caa9\animation-fps-deps']
for name in ('common','tools'):
    package=importlib.import_module(name);package.__path__=[str(HERE/'candidate_r9_source'/name),str(AURA/name)]
# Load candidate TTS with its actual runtime __file__, without GPU/model loading.
tts_name='board.runtime.audio.omnivoice_voice'
importlib.import_module('board.runtime.audio')
tts=types.ModuleType(tts_name);tts.__file__=str(AURA/'board/runtime/audio/omnivoice_voice.py');tts.__package__='board.runtime.audio'
sys.modules[tts_name]=tts
exec(compile((HERE/'candidate_r9_source/board/runtime/audio/omnivoice_voice.py').read_text(encoding='utf-8'),tts.__file__,'exec'),tts.__dict__)

def service_module():
    name='tools.board_model_host';path=HERE/'candidate_r9_source/tools/board_model_host.py'
    if not path.exists():path=AURA/'tools/board_model_host.py'
    module=types.ModuleType(name);module.__file__=str(AURA/'tools/board_model_host.py');module.__package__='tools'
    sys.modules[name]=module;exec(compile(path.read_text(encoding='utf-8'),str(path),'exec'),module.__dict__);return module

