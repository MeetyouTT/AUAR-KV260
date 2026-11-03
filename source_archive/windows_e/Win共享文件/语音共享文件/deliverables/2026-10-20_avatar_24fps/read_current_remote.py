import json,base64
from pathlib import Path
r=Path('/home/root/aura-voice-barge-in-20261020/candidate-667b70d586ca/runtime')
names=['aura/tools/board_avatar_pan.py','aura/tools/native_pixels.cpp','aura/tools/native_pixels.py','aura/tools/native_video.py','aura/tools/board_avatar_worker.py','aura/config/board_avatar_gtk.json']
print(json.dumps({n:base64.b64encode((r/n).read_bytes()).decode() for n in names}))
