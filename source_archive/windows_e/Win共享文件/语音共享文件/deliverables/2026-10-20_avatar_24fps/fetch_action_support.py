import base64,json
from pathlib import Path
root=Path('/home/root/aura-echo-verify-20261021/candidate-a3c8e50c2797/runtime')
names=['aura/tools/native_pixels.py','aura/tools/realtime_facials.py','aura/tools/facial_layers.py',
       'deliverables/2026-10-06_avatar_reuse/preview_script.py']
print(json.dumps({n:base64.b64encode((root/n).read_bytes()).decode() for n in names}))
