import importlib,sys
from pathlib import Path
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;P=H.parent;A=P.parents[1]/'aura';B=P.parent/'2026-10-29_speaker_visual_cooperation'
sys.path[:0]=[str(P),str(B),str(A),r'C:\Users\35870\.codex\visualizations\2026\10\26\01a1772c-f263-75f1-bfa1-9bd865e5caa9\animation-fps-deps']
for name in ('common','tools','board','board.runtime','board.runtime.audio'):
    package=importlib.import_module(name);relative=name.replace('.','/')
    package.__path__=[str(H/'candidate'/relative),str(P/'candidate'/relative),str(B/'board_bridge/candidate'/relative),str(B/'candidate'/relative),str(A/relative)]
