import base64, hashlib, json, subprocess
from pathlib import Path
root=Path('/home/root/aura-dpu-vision-20261021/postpower-retry-live/release-reliability-f7624754038f-450136/gui-runtime')
out={'files':{}}
for relative in ('aura/tools/native_pixels.cpp','aura/tools/libaura_pixels.so','aura/tools/demo_script.py','deliverables/2026-10-06_avatar_reuse/preview_script.py'):
    p=root/relative
    if p.is_file():
        raw=p.read_bytes();row={'sha256':hashlib.sha256(raw).hexdigest(),'size':len(raw)}
        if relative.endswith('.cpp') or relative.endswith('preview_script.py'):row['source_b64']=base64.b64encode(raw).decode()
        out['files'][relative]=row
out['build_tools']=subprocess.run(['sh','-c','command -v g++; pkg-config --modversion opencv4 gstreamer-1.0 gstreamer-app-1.0 gstreamer-video-1.0'],capture_output=True,text=True).stdout
out['boot']=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
print(json.dumps(out))
