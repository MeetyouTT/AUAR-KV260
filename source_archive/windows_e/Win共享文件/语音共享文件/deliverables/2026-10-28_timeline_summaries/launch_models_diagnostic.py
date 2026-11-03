"""Use the unchanged project launcher, adding a startup-only diagnostic wrapper."""
import importlib.util,subprocess,sys
from pathlib import Path
H=Path(__file__).resolve().parent;A=H.parents[1]/'aura'
path=H.parent/'2026-10-18_board_dialogue/launch_models.py'
sys.path.insert(0,str(path.parent))
spec=importlib.util.spec_from_file_location('summary_legacy_launcher',path)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
original=subprocess.Popen
def wrapped(command,*args,**kwargs):
    if isinstance(command,list) and str(A/'tools/board_model_host.py') in command:
        index=command.index(str(A/'tools/board_model_host.py'))
        command=command[:index]+[str(H/'diagnostic_voice_entry.py'),'--script']+command[index:]
    return original(command,*args,**kwargs)
subprocess.Popen=wrapped
raise SystemExit(module.main())
