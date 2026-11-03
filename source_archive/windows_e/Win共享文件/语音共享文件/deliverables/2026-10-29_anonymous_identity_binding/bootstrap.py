import importlib,sys
sys.dont_write_bytecode=True
from pathlib import Path
H=Path(__file__).resolve().parent;A=H.parents[1]/'aura';B=H.parent/'2026-10-29_speaker_visual_cooperation/candidate'
sys.path[:0]=[str(A),r'C:\Users\35870\.codex\visualizations\2026\10\26\01a1772c-f263-75f1-bfa1-9bd865e5caa9\animation-fps-deps']
for name in ('common','tools','board','board.runtime','board.runtime.audio'):
    package=importlib.import_module(name);relative=name.replace('.','/')
    package.__path__=[str(H/'candidate'/relative),str(B/relative),str(A/relative)]
