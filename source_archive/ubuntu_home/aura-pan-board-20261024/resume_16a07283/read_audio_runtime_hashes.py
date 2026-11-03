import hashlib,json
from pathlib import Path
A=Path('/home/root/aura-pan-current-20261024/16a07283/gui-manual-bound-v1/runtime/aura')
names=('tools/gstreamer_audio_worker.py','tools/gstreamer_persistent_engine.py','tools/gstreamer_audio.py')
print(json.dumps({'hashes':{n:hashlib.sha256((A/n).read_bytes()).hexdigest() for n in names},'board_mutated':False}))
